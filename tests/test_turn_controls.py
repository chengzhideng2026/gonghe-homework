import io
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from agent import Agent, ERPError, ERPNextClient, LLMRunner
from execution_trace import ExecutionTraceWriter
from read_policy import RequestLimitError
from test_agent import FakeERP
from tool_registry import ToolRegistry


def definition(name='probe'):
    return {'type': 'function', 'function': {'name': name,
            'description': 'A read-only test probe.',
            'parameters': {'type': 'object', 'properties': {'value': {'type': 'integer'}},
                           'required': ['value'], 'additionalProperties': False}}}


def reply(message, usage=None):
    body = {'choices': [{'message': message, 'finish_reason': 'stop'}]}
    if usage is not None:
        body['usage'] = usage
    return io.BytesIO(json.dumps(body, ensure_ascii=False).encode())


class TestAskTurnControls(unittest.TestCase):
    def runner(self, registry):
        runner = LLMRunner(Agent(FakeERP()), registry)
        runner.base, runner.key, runner.model = 'https://example.invalid/v1', 'test-key', 'test-model'
        return runner

    def test_expired_response_does_not_execute_first_tool_on_real_ask_path(self):
        registry = ToolRegistry()
        seen = []
        registry.register(definition(), lambda context, args: seen.append(args['value']) or args['value'])
        runner = self.runner(registry)
        runner.trace_writer = ExecutionTraceWriter(tempfile.mkdtemp())
        response = {'role': 'assistant', 'content': None, 'tool_calls': [
            {'id': 'expired-1', 'type': 'function',
             'function': {'name': 'probe', 'arguments': '{"value":1}'}}]}
        def expired_response(request, timeout):
            runner._turn_deadline = 0
            return reply(response)
        with patch('agent.urlopen', side_effect=expired_response):
            with self.assertRaisesRegex(RuntimeError, 'deadline'):
                runner.ask('probe once', [])
        self.assertEqual(seen, [])
        self.assertTrue(any(m.get('role') == 'tool' and 'deadline' in m.get('content', '')
                            for m in runner.last_trace))

    def test_each_call_in_one_response_checks_deadline_and_preserves_pairing(self):
        registry = ToolRegistry()
        seen = []
        def first(context, args):
            seen.append(args['value'])
            runner._turn_deadline = 0
            return args['value']
        registry.register(definition('first'), first)
        registry.register(definition('second'), lambda context, args: seen.append(args['value']) or args['value'])
        runner = self.runner(registry)
        message = {'role': 'assistant', 'content': None, 'tool_calls': [
            {'id': 'one', 'type': 'function', 'function': {'name': 'first', 'arguments': '{"value":1}'}},
            {'id': 'two', 'type': 'function', 'function': {'name': 'second', 'arguments': '{"value":2}'}}]}
        with patch('agent.urlopen', return_value=reply(message)):
            with self.assertRaisesRegex(RuntimeError, 'deadline'):
                runner.ask('run both', [])
        self.assertEqual(seen, [1])
        tool_messages = [m for m in runner.last_trace if m.get('role') == 'tool']
        self.assertEqual({m['tool_call_id'] for m in tool_messages}, {'one', 'two'})
        self.assertIn('deadline', next(m['content'] for m in tool_messages if m['tool_call_id'] == 'two'))

    def test_expired_get_many_and_aggregate_do_not_start_more_http(self):
        client = ERPNextClient(base='http://127.0.0.1:8080')
        client.deadline = time.monotonic() - 1
        with patch('agent.urlopen') as wire:
            result = client.get_many('Item', ['A', 'B'])
            self.assertFalse(result['complete'])
            self.assertEqual(wire.call_count, 0)
            with self.assertRaisesRegex(RequestLimitError, 'deadline'):
                client.aggregate('Item')
            self.assertEqual(wire.call_count, 0)

    def test_deadline_stops_after_first_batch_read_and_before_aggregate_page(self):
        client = ERPNextClient(base='http://127.0.0.1:8080')
        calls = []
        def wire(request, timeout):
            calls.append(request.full_url)
            client.deadline = 0
            return io.BytesIO(b'{"data":{"name":"A"}}')
        client.deadline = time.monotonic() + 3
        with patch('agent.urlopen', side_effect=wire):
            batch = client.get_many('Item', ['A', 'B'])
        self.assertEqual(len(calls), 1)
        self.assertEqual(batch['success_count'], 1)
        self.assertEqual(batch['error_count'], 1)

        client = ERPNextClient(base='http://127.0.0.1:8080')
        calls = []
        def count_then_expire(request, timeout):
            calls.append(request.full_url)
            client.deadline = 0
            return io.BytesIO(b'{"message":2}')
        client.deadline = time.monotonic() + 3
        with patch('agent.urlopen', side_effect=count_then_expire):
            with self.assertRaisesRegex(ERPError, 'deadline'):
                client.aggregate('Item')
        self.assertEqual(len(calls), 1)

    def test_native_erp_http_timeout_is_capped_by_remaining_turn_time(self):
        client = ERPNextClient(base='http://127.0.0.1:8080', timeout=20)
        client.deadline = time.monotonic() + 3
        observed = []
        def wire(request, timeout):
            observed.append(timeout)
            return io.BytesIO(b'{"message": 18}')
        with patch('agent.urlopen', side_effect=wire):
            self.assertEqual(client.count('Item'), 18)
        self.assertEqual(len(observed), 1)
        self.assertLessEqual(observed[0], 3)

    def test_long_history_is_trimmed_by_complete_turns_and_receipts_survive(self):
        runner = self.runner(ToolRegistry())
        # Register the real built-in count after making a small isolated runner.
        from erp_tools import BUILTIN_TOOLS
        runner.registry = BUILTIN_TOOLS.clone()
        # Leave room for the current system evidence rules while forcing old
        # turns out of context. This is a byte budget, not a token estimate.
        runner.context_max_bytes = 5000
        history = [{'role': 'system', 'content': 'rules'}]
        for index in range(8):
            call_id = f'old-{index}'
            history.extend([
                {'role': 'user', 'content': f'old question {index}'},
                {'role': 'assistant', 'content': None, 'tool_calls': [{'id': call_id, 'type': 'function',
                    'function': {'name': 'count_documents', 'arguments': '{"doctype":"Item"}'}}]},
                {'role': 'tool', 'tool_call_id': call_id, 'content': json.dumps({'ok': True, 'data': index})},
                {'role': 'assistant', 'content': f'old answer {index}'}])
        responses = [
            {'role': 'assistant', 'content': None, 'tool_calls': [{'id': 'current', 'type': 'function',
                'function': {'name': 'count_documents', 'arguments': '{"doctype":"Item"}'}}]},
            {'role': 'assistant', 'content': '18'}]
        requests = []
        def model(request, timeout):
            payload = json.loads(request.data)
            requests.append(payload['messages'])
            return reply(responses.pop(0))
        runner.agent.c.count = lambda doctype, filters=None: 18
        with patch('agent.urlopen', side_effect=model):
            answer, updated = runner.ask('How many items now?', history)
        self.assertEqual(answer, '18')
        self.assertTrue(any('[HISTORICAL TOOL EVIDENCE SUMMARY' in str(m.get('content'))
                            for m in requests[0] if m.get('role') == 'system'))
        for messages in requests:
            self.assertTrue(all(isinstance(message, dict) and 'role' in message for message in messages))
            calls = {call['id'] for message in messages if message.get('role') == 'assistant'
                     for call in message.get('tool_calls') or []}
            results = {message.get('tool_call_id') for message in messages if message.get('role') == 'tool'}
            self.assertTrue(results <= calls)
        self.assertTrue(runner.receipts())
        self.assertTrue(any(m.get('role') == 'tool' and m.get('tool_call_id') == 'current' for m in updated))

    def test_trace_records_usage_tool_io_and_does_not_replace_result_on_write_failure(self):
        registry = ToolRegistry()
        registry.register(definition(), lambda context, args: args['value'])
        runner = self.runner(registry)
        with tempfile.TemporaryDirectory() as directory:
            runner.trace_writer = ExecutionTraceWriter(directory)
            responses = [
                {'role': 'assistant', 'content': None, 'tool_calls': [{'id': 'c', 'type': 'function',
                    'function': {'name': 'probe', 'arguments': '{"value":7}'}}]},
                {'role': 'assistant', 'content': 'done'}]
            with patch('agent.urlopen', side_effect=lambda request, timeout: reply(responses.pop(0), {'prompt_tokens': 4} if responses else None)):
                answer, _ = runner.ask('trace this', [])
            self.assertEqual(answer, 'done')
            traces = list(Path(directory).glob('*.json'))
            self.assertEqual(len(traces), 1)
            record = json.loads(traces[0].read_text(encoding='utf-8'))
            self.assertEqual(record['usage_events'][0]['prompt_tokens'], 4)
            self.assertEqual(record['tool_calls'][0]['call_id'], 'c')
            self.assertIn('evidence_identity', record['tool_calls'][0])
            self.assertIn('elapsed_ms', record['tool_calls'][0])
            runner.trace_writer.write = lambda *args: (_ for _ in ()).throw(OSError('trace disk full'))
            with patch('agent.urlopen', return_value=reply({'role': 'assistant', 'content': 'still works'})):
                answer, _ = runner.ask('again', [])
            self.assertEqual(answer, 'still works')
            self.assertIn('trace disk full', runner.last_trace_write_error)


if __name__ == '__main__':
    unittest.main()
