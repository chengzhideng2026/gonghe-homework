import io
import json
import unittest
from unittest.mock import Mock, patch

from agent import Agent, ERPNextClient, LLMRunner
from test_agent import FakeERP


class TestIdempotencyAndDeadline(unittest.TestCase):
    def test_preview_persists_a_stable_nonsecret_key_and_legacy_client_still_works(self):
        erp = FakeERP()
        agent = Agent(erp)
        preview = agent.proposal_po('Tongling Magnet Wire Co.', 'RM-COIL-CU-2.0', 1, 'Meter', 29)
        key = preview['idempotency_key']
        self.assertTrue(key.startswith('plantcore-po-'))
        self.assertEqual(agent.proposals[preview['proposal_id']]['idempotency_key'], key)
        result = agent.confirm(preview['proposal_id'])
        self.assertEqual(result['name'], 'PUR-TEST-0001')
        self.assertEqual(len(erp.created), 1)

    def test_native_client_transmits_same_key_without_putting_it_in_the_json_document(self):
        client = ERPNextClient(key='key', secret='secret')
        with patch.object(client, '_http_req', return_value={'name': 'PO-1'}) as wire:
            client.create('Purchase Order', {'supplier': 'S'}, idempotency_key='plantcore-po-12345678')
        self.assertEqual(wire.call_args.kwargs['headers'], {'X-Idempotency-Key': 'plantcore-po-12345678'})
        self.assertNotIn('idempotency_key', wire.call_args.kwargs['json'])

    def test_model_turn_deadline_is_checked_before_tool_execution(self):
        runner = LLMRunner(Agent(FakeERP()))
        runner._turn_deadline = 0
        with self.assertRaisesRegex(RuntimeError, 'deadline'):
            runner._tool('calculate', {'expression': '1+1'})

    def test_model_request_timeout_is_capped_by_remaining_turn_budget(self):
        runner = LLMRunner(Agent(FakeERP()))
        runner.base, runner.key, runner.model = 'https://example.invalid/v1', 'key', 'model'
        runner.turn_timeout = 1
        request_timeouts = []
        response = {'choices': [{'message': {'role': 'assistant', 'content': 'done'}, 'finish_reason': 'stop'}]}
        def respond(request, timeout):
            request_timeouts.append(timeout)
            return io.BytesIO(json.dumps(response).encode())
        with patch('agent.urlopen', side_effect=respond):
            runner.ask('say done', [])
        self.assertEqual(len(request_timeouts), 1)
        self.assertLessEqual(request_timeouts[0], 1)


if __name__ == '__main__':
    unittest.main()
