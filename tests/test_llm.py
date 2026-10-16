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

    def test_truncated_or_empty_response_is_not_reported_as_success(self):
        for reason, message in [('length', {'content': 'partial'}), ('stop', {'content': ''})]:
            with self.subTest(reason=reason), patch('agent.urlopen', return_value=io.BytesIO(
                    json.dumps({'choices': [{'message': message, 'finish_reason': reason}]}).encode())):
                with self.assertRaises(RuntimeError):
                    self.runner().ask('test')
