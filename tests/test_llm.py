import io
import json
import unittest
from unittest.mock import Mock, patch
from agent import Agent, LLMRunner


class TestLLMProtocol(unittest.TestCase):
    def runner(self):
        client = Mock()
        client.count.return_value = 18
        runner = LLMRunner(Agent(client))
        runner.base, runner.key, runner.model = 'https://example.invalid/v1', 'test-key', 'test-model'
        return runner

    def test_tool_result_roundtrip_preserves_assistant_message(self):
        runner = self.runner()
        tool_msg = {'role': 'assistant', 'content': None, 'reasoning_content': 'provider context',
                    'tool_calls': [{'id': 'call_1', 'type': 'function',
                                    'function': {'name': 'count_documents', 'arguments': '{"doctype":"Item"}'}}]}
        responses = [tool_msg, {'role': 'assistant', 'content': '18 Items'}]
        requests = []
        def respond(request, timeout):
            requests.append(json.loads(request.data))
            return io.BytesIO(json.dumps({'choices': [{'message': responses.pop(0), 'finish_reason': 'stop'}]}).encode())
        with patch('agent.urlopen', side_effect=respond):
            answer, _ = runner.ask('How many items?')
        self.assertEqual(answer, '18 Items')
        runner.agent.c.count.assert_called_once_with('Item', None)
        self.assertEqual(requests[1]['messages'][2], tool_msg)
        result = requests[1]['messages'][3]
        self.assertEqual(result['tool_call_id'], 'call_1')
        self.assertEqual(json.loads(result['content']), {'ok': True, 'data': 18})
        self.assertEqual(runner.receipts()[0]['summary'], 18)

    def test_receipts_exclude_prior_turns_and_clear_on_clarification(self):
        runner = self.runner()
        old = [{'role': 'system', 'content': 'test'},
               {'role': 'assistant', 'tool_calls': [{'id': 'old', 'function':
                    {'name': 'count_documents', 'arguments': '{"doctype":"Item"}'}}]},
               {'role': 'tool', 'tool_call_id': 'old', 'content': '{"ok":true,"data":18}'},
               {'role': 'assistant', 'content': '18 Items'}]
        response = {'choices': [{'message': {'role': 'assistant', 'content': 'Which item?'}, 'finish_reason': 'stop'}]}
        with patch('agent.urlopen', return_value=io.BytesIO(json.dumps(response).encode())):
            runner.ask('Buy some material', old)
        self.assertEqual(runner.receipts(), [])

    def test_list_always_returns_source_identifier_with_requested_fields(self):
        runner = self.runner()
        runner.agent.c.list.return_value = [{'name': 'I1', 'stock_uom': 'Nos'}]
        result = runner._tool('list_documents', {'doctype': 'Item', 'fields': ['stock_uom', 'name']})
        self.assertEqual(runner.agent.c.list.call_args.args[1], ['name', 'stock_uom'])
        self.assertEqual(result['records'][0]['name'], 'I1')

    def test_truncated_or_empty_response_is_not_reported_as_success(self):
        for reason, message in [('length', {'content': 'partial'}), ('stop', {'content': ''})]:
            with self.subTest(reason=reason), patch('agent.urlopen', return_value=io.BytesIO(
                    json.dumps({'choices': [{'message': message, 'finish_reason': reason}]}).encode())):
                with self.assertRaises(RuntimeError):
                    self.runner().ask('test')
