"""Calendar comparisons and their delivery through the real ask protocol."""
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent import Agent, ERPError, ERPNextClient, LLMRunner, invoice_due_evidence, invoice_read_evidence, overdue
from context_budget import _tool_summary
from execution_trace import ExecutionTraceWriter
from read_policy import ReadPolicy


class TestInvoiceDates(unittest.TestCase):
    def test_before_on_after_reference_date_preserve_source_status(self):
        invoices = []
        for due, relation, days, expected in [('2025-10-14', 'before', -1, True),
                                              ('2025-10-15', 'on', 0, False),
                                              ('2025-10-18', 'after', 3, False)]:
            with self.subTest(due=due):
                invoice = {'name': due, 'due_date': due, 'outstanding_amount': '17.25',
                           'status': 'Overdue', 'docstatus': 1}
                original = copy.deepcopy(invoice)
                evidence = invoice_due_evidence(invoice, '2025-10-15')
                self.assertEqual(evidence['reference_date'], '2025-10-15')
                self.assertEqual(evidence['due_date_relation'], relation)
                self.assertEqual(evidence['due_date_minus_reference_days'], days)
                self.assertEqual(evidence['overdue_by_reference_date'], expected)
                self.assertEqual(evidence['erp_status'], 'Overdue')
                self.assertEqual(invoice, original)
                invoices.append(invoice)
        self.assertEqual(overdue(invoices, '2025-10-15'), invoices[:1])
        # The caller's reference is used, not today's clock or a fixed answer.
        self.assertTrue(invoice_due_evidence(invoices[-1], '2025-10-19')['overdue_by_reference_date'])

    def test_current_positive_balance_is_required_without_float_rounding(self):
        invoice = {'due_date': '2025-10-14', 'status': 'Unpaid'}
        for amount, expected in [('0', False), ('-1', False), ('1e-1000', True)]:
            with self.subTest(amount=amount):
                result = invoice_due_evidence({**invoice, 'outstanding_amount': amount}, '2025-10-15')
                self.assertIs(result['overdue_by_reference_date'], expected)
                self.assertEqual(result['erp_status'], 'Unpaid')

    def test_invalid_or_missing_inputs_are_unknown_not_zero_or_status_fallback(self):
        valid = {'due_date': '2025-10-14', 'outstanding_amount': 10, 'status': 'Overdue'}
        for changes in ({'due_date': None}, {'due_date': '2025-02-30'}, {'due_date': '20251014'},
                        {'outstanding_amount': None}, {'outstanding_amount': 'NaN'}):
            with self.subTest(changes=changes):
                result = invoice_due_evidence({**valid, **changes}, '2025-10-15')
                self.assertIsNone(result['overdue_by_reference_date'])
                self.assertIn('unknown_reason', result)
        self.assertIsNone(invoice_due_evidence({}, '2025-10-15')['overdue_by_reference_date'])
        self.assertIsNone(invoice_due_evidence(valid, 'bad-date')['overdue_by_reference_date'])

    def test_date_assessment_is_opt_in_without_hiding_or_mutating_source_fields(self):
        invoice = {'name': 'A', 'status': 'Overdue', 'due_date': '2025-10-18', 'outstanding_amount': 10}
        args = {'doctype': 'Sales Invoice', 'name': 'A'}
        for flag in (None, False):
            self.assertIsNone(invoice_read_evidence('get_document', {**args, 'assess_due_date': flag}, invoice))
        self.assertIsNone(invoice_read_evidence('get_document', args, invoice))
        self.assertEqual(invoice, {'name': 'A', 'status': 'Overdue', 'due_date': '2025-10-18', 'outstanding_amount': 10})

    def test_ask_reads_deliver_sidecar_evidence_without_rewriting_or_extra_http(self):
        client = ERPNextClient(base='http://127.0.0.1:8080')
        client.read_policy = ReadPolicy(interval=0)
        runner = LLMRunner(Agent(client))
        runner.key, runner.model = 'test-key', 'test-model'
        invoice = {'doctype': 'Sales Invoice', 'name': 'INV-A', 'due_date': '2025-10-18',
                   'outstanding_amount': 17.25, 'currency': 'USD', 'status': 'Overdue', 'docstatus': 1}
        untouched = copy.deepcopy(invoice)
        calls = [
            ('get_document', {'doctype': 'Sales Invoice', 'name': 'INV-A'}),
            ('get_document', {'doctype': 'Sales Invoice', 'name': 'INV-A', 'assess_due_date': True}),
            ('list_documents', {'doctype': 'Sales Invoice', 'fields': ['due_date', 'outstanding_amount',
                                                                      'status', 'docstatus'],
                                'include_total': False, 'assess_due_date': True}),
            ('get_documents', {'doctype': 'Sales Invoice', 'names': ['INV-A', 'MISSING'], 'assess_due_date': True})]
        replies = [
            {'role': 'assistant', 'tool_calls': [
                {'id': str(index), 'type': 'function',
                 'function': {'name': name, 'arguments': json.dumps(args)}}
                for index, (name, args) in enumerate(calls)]},
            {'role': 'assistant', 'content': 'A protocol fixture, not a business answer.'}]
        requests = []

        def model(request, timeout):
            requests.append(json.loads(request.data))
            return io.BytesIO(json.dumps({'choices': [{'message': replies.pop(0),
                                                       'finish_reason': 'stop'}]}).encode())

        def erp(method, path, **kwargs):
            self.assertEqual(method, 'GET')
            if path.endswith('/MISSING'):
                raise ERPError('ERPNext HTTP 404: missing')
            return [invoice] if path.endswith('/Sales%20Invoice') else invoice

        with tempfile.TemporaryDirectory() as directory:
            runner.trace_writer = ExecutionTraceWriter(directory)
            with patch('agent.urlopen', side_effect=model), patch.object(client, '_http_req', side_effect=erp) as wire:
                runner.ask('Read these invoice records.', [])
            # GET one + list one + missing batch member. INV-A is reused from cache.
            self.assertEqual(wire.call_count, 3)
            self.assertEqual(invoice, untouched)
            tool_messages = [message for message in requests[-1]['messages'] if message.get('role') == 'tool']
            for (name, args), message, receipt in zip(calls, tool_messages, runner.receipts()):
                payload = json.loads(message['content'])
                if not args.get('assess_due_date'):
                    self.assertNotIn('reference_date_evidence', payload)
                    self.assertNotIn('reference_date_evidence', receipt)
                    self.assertEqual(payload['data'], untouched)
                    continue
                evidence = payload['reference_date_evidence']
                self.assertEqual(evidence['reference_date'], '2025-10-15')
                self.assertEqual(len(evidence['records']), 1)
                assessment = evidence['records'][0]
                self.assertEqual(assessment['due_date_relation'], 'after')
                self.assertFalse(assessment['overdue_by_reference_date'])
                self.assertEqual(assessment['erp_status'], 'Overdue')
                self.assertEqual(receipt['reference_date_evidence'], evidence)
                historical = _tool_summary({'function': {'name': name}}, message)
                self.assertEqual(historical['reference_date_evidence']['records'], evidence['records'])
                if name == 'get_document':
                    self.assertEqual(payload['data'], untouched)
                if name == 'get_documents':
                    self.assertFalse(payload['data']['complete'])
            trace = json.loads((Path(directory) / (runner.turn_id + '.json')).read_text(encoding='utf-8'))
            self.assertNotIn('reference_date_evidence', trace['tool_calls'][0])
            self.assertEqual(trace['tool_calls'][1]['reference_date_evidence']['reference_date'], '2025-10-15')
