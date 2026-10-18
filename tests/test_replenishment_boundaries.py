"""Offline ask/protocol contracts, NOT evidence of live model instruction following.

Scripted model calls exercise real Decimal tools, validators and proposal state.
Policy assertions separately check what the model actually receives.
"""
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent import Agent, LLMRunner
from execution_trace import ExecutionTraceWriter
from proposal_store import ProposalStore
from test_agent import FakeERP


def calls(*items):
    return {'role': 'assistant', 'content': None, 'tool_calls': [
        {'id': identity, 'type': 'function', 'function': {
            'name': name, 'arguments': json.dumps(args)}}
        for identity, name, args in items]}


def final(text):
    return {'role': 'assistant', 'content': text}


class StockERP(FakeERP):
    def __init__(self):
        super().__init__(items=[{'name': 'PART-A', 'stock_uom': 'Each', 'disabled': 0}],
                         suppliers=[{'name': 'SUPPLIER-A'}])
        self.stock = {'name': 'BIN-A', 'item_code': 'PART-A', 'warehouse': 'STORE-A',
                      'actual_qty': 42, 'ordered_qty': 13, 'reserved_qty': 9,
                      'stock_uom': 'Each'}

    def get(self, doctype, name):
        self.reads.append((doctype, name))
        if (doctype, name) == ('Item', 'PART-A'):
            return {'name': name, 'stock_uom': 'Each', 'last_purchase_rate': 7.25}
        if (doctype, name) != ('Bin', 'BIN-A'):
            raise AssertionError('Unexpected ERP read')
        return dict(self.stock)

    def create(self, *args, **kwargs):
        raise AssertionError('Preview must never create an ERP document')


class TestReplenishmentBoundaries(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.erp = StockERP()
        self.store = ProposalStore(Path(directory.name) / 'proposals.sqlite3')
        self.runner = LLMRunner(Agent(self.erp, store=self.store))
        self.runner.trace_writer = ExecutionTraceWriter(Path(directory.name) / 'traces')
        self.runner.base = 'https://example.invalid/v1'
        self.runner.key, self.runner.model = 'test-key', 'test-model'
        self.requests = []

    def ask(self, question, replies, history=None):
        replies = list(replies)

        def model(request, timeout):
            self.requests.append(json.loads(request.data))
            return io.BytesIO(json.dumps({'choices': [{'message': replies.pop(0),
                                                       'finish_reason': 'stop'}]}).encode())

        with patch('agent.urlopen', side_effect=model):
            result = self.runner.ask(question, history)
        self.assertEqual(replies, [], 'Unexpected missing/extra model rounds')
        return result

    def payload(self, identity):
        return next(json.loads(m['content']) for m in self.runner.last_trace
                    if m.get('tool_call_id') == identity)

    def test_policy_upgrades_old_history_once_in_actual_model_request(self):
        history = [{'role': 'system', 'content': 'Existing rules.'},
                   {'role': 'user', 'content': 'Earlier task.'}, final('Earlier answer.')]
        _, history = self.ask('Continue.', [final('Please specify the item.')], history)
        self.ask('Still deciding.', [final('Please specify the item.')], history)
        for request in self.requests:
            policy = request['messages'][0]['content']
            self.assertTrue(policy.startswith('Existing rules.'))
            self.assertEqual(policy.count('[REPLENISHMENT BASIS v1]'), 1)
            for rule in ('actual_qty', 'relevant reservations', 'conditional on arrival',
                         'Unknown incoming is not zero', 'preserve the chosen basis',
                         'unverified assumption', 'non-executable preliminary',
                         'Preview permission never authorizes ERP writes'):
                self.assertIn(rule, policy)

    def test_physical_and_explicit_future_supply_keep_distinct_calculation_results(self):
        self.ask('Target 80 Each: physical shortfall, then separately including incoming.', [
            calls(('stock', 'get_document', {'doctype': 'Bin', 'name': 'BIN-A'})),
            calls(('physical', 'calculate', {'expression': '80 - 42'}),
                  ('future', 'calculate', {'expression': '80 - 42 - 13'})),
            final('Physical shortfall 38 Each; future shortfall 25 Each if incoming arrives.')])
        self.assertEqual(self.payload('physical')['data']['result'], '38')
        self.assertEqual(self.payload('future')['data']['result'], '25')
        self.assertEqual(self.payload('stock')['data']['ordered_qty'], 13)
        self.assertEqual(self.erp.reads, [('Bin', 'BIN-A')])

    def test_reserved_free_stock_is_separate_from_gross_physical_target(self):
        self.ask('Target 80 Each unreserved for sales; compare gross physical stock.', [
            calls(('stock', 'get_document', {'doctype': 'Bin', 'name': 'BIN-A'})),
            calls(('free', 'calculate', {'expression': '42 - 9'}),
                  ('free_gap', 'calculate', {'expression': '80 - (42 - 9)'}),
                  ('physical_gap', 'calculate', {'expression': '80 - 42'})),
            final('Sales-unreserved stock 33 Each, gap 47 Each; physical gap 38 Each. '
                  'Other reservation types are unknown.')])
        for identity, expected in [('free', '33'), ('free_gap', '47'), ('physical_gap', '38')]:
            self.assertEqual(self.payload(identity)['data']['result'], expected)
        self.assertNotIn('reserved_qty_for_production', self.payload('stock')['data'])

    def test_unknown_incoming_allows_physical_result_without_fabricating_forecast(self):
        del self.erp.stock['ordered_qty']
        self.ask('Target 80 Each; report physical and future supply if known.', [
            calls(('stock', 'get_document', {'doctype': 'Bin', 'name': 'BIN-A'})),
            calls(('physical', 'calculate', {'expression': '80 - 42'})),
            final('Physical shortfall 38 Each. Incoming is unknown; future gap is unknown.')])
        self.assertNotIn('ordered_qty', self.payload('stock')['data'])
        self.assertEqual(self.payload('physical')['data']['result'], '38')
        self.assertEqual(len(self.runner.agent.proposals), 0)

    def test_followup_incomplete_plan_reuses_evidence_without_confirmable_proposal(self):
        _, history = self.ask('Target physical stock 80 Each; compare incoming and read historical price.', [
            calls(('stock', 'get_document', {'doctype': 'Bin', 'name': 'BIN-A'}),
                  ('price', 'get_document', {'doctype': 'Item', 'name': 'PART-A'})),
            calls(('physical', 'calculate', {'expression': '80 - 42'}),
                  ('future', 'calculate', {'expression': '80 - 42 - 13'})),
            final('Physical gap 38 Each; separate future gap 25 Each conditional on arrival. '
                  'Historical unit rate 7.25, currency unknown; not a current agreed quote.')])
        self.assertNotIn('currency', self.payload('price')['data'])
        self.assertNotIn('supplier', self.payload('price')['data'])
        answer, _ = self.ask(
            'Use that physical basis for a preliminary plan, supplier blank; '
            'use the historical rate with USD as an unverified budgeting assumption; no ERP write.', [
                calls(('budget', 'calculate', {'expression': '38 * 7.25'})),
                final('Non-executable preliminary plan: PART-A, STORE-A, 38 Each; '
                      'incoming excluded from the physical target. Unverified budget assumption: '
                      'USD 7.25 per Each. Unverified conditional budget: USD 275.50. '
                      'Missing supplier, agreed quote and company verification. No ERP document '
                      'was created by this plan.')], history)
        self.assertEqual(self.payload('budget')['data']['result'], '275.50')
        self.assertIn('38 Each', answer)
        self.assertNotIn('/confirm', answer)
        self.assertEqual(self.runner.agent.proposals, {})
        self.assertEqual(self.erp.reads, [('Bin', 'BIN-A'), ('Item', 'PART-A')])
        self.assertFalse(any('PROGRAM EVIDENCE CHECK' in (m.get('content') or '')
                             for m in self.runner.last_trace))

    def test_complete_inputs_prepare_only_local_pending_with_unchanged_validation(self):
        self.ask('Prepare only: agreed supplier, item, quantity, unit and USD quote.', [
            calls(('preview', 'prepare_purchase_order', {
                'supplier': 'SUPPLIER-A', 'item': 'PART-A', 'qty': 38,
                'uom': 'Each', 'rate': 7.25, 'currency': 'USD'})),
            final('Local pending preview only; this preview created no corresponding ERP document.')])
        preview = self.payload('preview')['data']
        stored = self.store.get(preview['proposal_id'], self.runner.agent._target_binding())
        self.assertEqual(stored['state'], 'pending')
        self.assertEqual(preview['local_state'], 'pending')
        self.assertIsNone(preview['erp_document'])
        self.assertEqual(preview['doc']['docstatus'], 0)
        self.assertEqual(preview['estimated_total'], '275.50')
        self.assertEqual(stored['doc'], preview['doc'])
        self.assertEqual(self.erp.created, [])

    def test_missing_fields_foreign_currency_and_wrong_unit_still_fail_closed(self):
        valid = {'supplier': 'SUPPLIER-A', 'item': 'PART-A', 'qty': 38,
                 'uom': 'Each', 'rate': 7.25, 'currency': 'USD'}
        for changes, omitted, error in [
                ({'supplier': ''}, None, 'required'),
                ({}, 'currency', 'Missing required'),
                ({'currency': ''}, None, 'explicit quote currency'),
                ({'currency': 'EUR'}, None, 'differs from company base currency'),
                ({'uom': 'Meter'}, None, 'UOM mismatch')]:
            with self.subTest(changes=changes, omitted=omitted):
                args = dict(valid, **changes)
                if omitted:
                    del args[omitted]
                self.ask('Preview only, do not write.', [
                    calls(('invalid', 'prepare_purchase_order', args)),
                    final('A confirmable preview is unavailable; required inputs must be resolved.')])
                payload = self.payload('invalid')
                self.assertFalse(payload['ok'])
                self.assertIn(error.lower(), payload['error'].lower())
                self.assertEqual(self.runner.agent.proposals, {})
        self.assertEqual(self.erp.created, [])

    def test_preview_permission_exposes_no_model_write_or_confirmation_tool(self):
        self.ask('You may preview only; I have not confirmed.', [
            calls(('forbidden', 'confirm', {'proposal_id': 'invented'})),
            final('No ERP document was created by this attempt.')])
        names = {t['function']['name'] for t in self.requests[0]['tools']}
        self.assertEqual(len(names), 9)
        self.assertNotIn('confirm', names)
        self.assertNotIn('create_document', names)
        self.assertFalse(self.payload('forbidden')['ok'])
        self.assertIn('not available', self.payload('forbidden')['error'])
        self.assertEqual(self.runner.agent.proposals, {})
        self.assertEqual(self.erp.created, [])
