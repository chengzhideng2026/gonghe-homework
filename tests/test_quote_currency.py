import io
import json
import unittest
from unittest.mock import patch
from agent import Agent, ERPError, LLMRunner, TOOL_DEFS
from tool_receipts import tool_receipts
from test_agent import FakeERP


ARGS = {'supplier': 'Tongling Magnet Wire Co.', 'item': 'RM-COIL-CU-2.0',
        'qty': 10, 'uom': 'Meter', 'rate': 29}


class TestQuoteCurrency(unittest.TestCase):
    def test_foreign_quote_rejected_without_preview_or_write(self):
        erp = FakeERP()
        agent = Agent(erp)
        with self.assertRaisesRegex(ERPError, 'differs from company base currency'):
            agent.proposal_po(**ARGS, currency='EUR')
        self.assertEqual(agent.proposals, {})
        self.assertEqual(erp.created, [])
        preview = agent.proposal_po(**ARGS, currency='USD')
        self.assertEqual(preview['doc']['currency'], 'USD')
        self.assertEqual(preview['estimated_total'], '290')

    def test_model_tool_must_supply_quote_currency(self):
        runner = LLMRunner(Agent(FakeERP()))
        with self.assertRaisesRegex(ValueError, 'explicit quote currency'):
            runner._tool('prepare_purchase_order', ARGS)
        schema = next(t['function']['parameters'] for t in TOOL_DEFS
                      if t['function']['name'] == 'prepare_purchase_order')
        self.assertIn('currency', schema['required'])

    def test_model_json_decimal_is_not_rounded_before_validation(self):
        runner = LLMRunner(Agent(FakeERP()))
        runner.base, runner.key, runner.model = 'https://example.invalid/v1', 'test-key', 'test-model'
        raw = '{"supplier":"Tongling Magnet Wire Co.","item":"RM-COIL-CU-2.0","qty":1.00000000000000001,"uom":"Meter","rate":29,"currency":"USD"}'
        messages = [
            {'role': 'assistant', 'tool_calls': [{'id': 'precise', 'type': 'function',
                 'function': {'name': 'prepare_purchase_order', 'arguments': raw}}]},
            {'role': 'assistant', 'content': 'Quantity cannot be represented without rounding; please clarify.'},
        ]
        def respond(request, timeout):
            return io.BytesIO(json.dumps({'choices': [{'message': messages.pop(0), 'finish_reason': 'stop'}]}).encode())
        with patch('agent.urlopen', side_effect=respond):
            runner.ask('Prepare exact quantity', [])
        self.assertEqual(runner.agent.proposals, {})
        payload = next(json.loads(m['content']) for m in runner.last_trace if m.get('role') == 'tool')
        self.assertFalse(payload['ok'])
        self.assertIn('precision', payload['error'])
        self.assertEqual(tool_receipts(runner.last_trace)[0]['arguments']['qty'], '1.00000000000000001')
