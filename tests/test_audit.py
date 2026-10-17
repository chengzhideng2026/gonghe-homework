import io
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from agent import Agent, ERPError, ERPNextClient, LLMRunner, calculate
from proposal_store import ProposalStore
from test_agent import FakeERP


class TestDurableConfirmation(unittest.TestCase):
    def preview(self, agent):
        return agent.proposal_po('Tongling Magnet Wire Co.', 'RM-COIL-CU-2.0', 100, 'Meter', 29)

    def test_restart_keeps_snapshot_and_repeated_confirmation_cannot_create_twice(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'journal.sqlite3'
            erp = FakeERP()
            first = Agent(erp, ProposalStore(path))
            preview = self.preview(first)
            second = Agent(erp, ProposalStore(path))
            second.confirm(preview['proposal_id'])
            third = Agent(erp, ProposalStore(path))
            with self.assertRaises(ERPError):
                third.confirm(preview['proposal_id'])
            self.assertEqual(len(erp.created), 1)
            self.assertEqual(third.store.get(preview['proposal_id'])['created_name'], 'PUR-TEST-0001')

    def test_crash_after_claim_is_blocked_after_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'journal.sqlite3'
            erp = FakeERP()
            first = Agent(erp, ProposalStore(path))
            preview = self.preview(first)
            first.store.claim(preview['proposal_id'], 900)
            restarted = Agent(erp, ProposalStore(path))
            with self.assertRaisesRegex(ERPError, 'already in flight'):
                restarted.confirm(preview['proposal_id'])
            self.assertEqual(erp.created, [])

    def test_lost_ack_after_remote_creation_never_blindly_retries(self):
        class LostACK(FakeERP):
            def create(self, doctype, doc):
                super().create(doctype, doc)
                raise TimeoutError('Remote committed but response was lost')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'journal.sqlite3'
            erp = LostACK()
            agent = Agent(erp, ProposalStore(path))
            proposal_id = self.preview(agent)['proposal_id']
            with self.assertRaises(ERPError):
                agent.confirm(proposal_id)
            with self.assertRaises(ERPError):
                Agent(erp, ProposalStore(path)).confirm(proposal_id)
            self.assertEqual(len(erp.created), 1)

    def test_concurrent_claims_have_one_winner(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'journal.sqlite3'
            erp = FakeERP()
            first = Agent(erp, ProposalStore(path))
            proposal_id = self.preview(first)['proposal_id']
            def attempt(_):
                try:
                    return ProposalStore(path).claim(proposal_id, 900)['state']
                except ValueError:
                    return 'blocked'
            with ThreadPoolExecutor(max_workers=2) as pool:
                self.assertCountEqual(list(pool.map(attempt, range(2))), ['creating', 'blocked'])

    def test_expired_or_discarded_previews_never_write(self):
        erp = FakeERP()
        agent = Agent(erp)
        expired = self.preview(agent)['proposal_id']
        agent.proposals[expired]['created_at'] -= 901
        with self.assertRaisesRegex(ERPError, 'expired'):
            agent.confirm(expired)
        discarded = self.preview(agent)['proposal_id']
        agent.discard(discarded)
        with self.assertRaises(ERPError):
            agent.confirm(discarded)
        self.assertEqual(erp.created, [])

    def test_disabled_supplier_is_rechecked_before_create(self):
        erp = FakeERP()
        agent = Agent(erp)
        proposal_id = self.preview(agent)['proposal_id']
        erp.suppliers[0]['disabled'] = 1
        with self.assertRaisesRegex(ERPError, 'Supplier is disabled'):
            agent.confirm(proposal_id)
        self.assertEqual(erp.created, [])

    def test_company_ambiguity_and_numeric_overflow_are_rejected(self):
        class AmbiguousERP(FakeERP):
            def list(self, doctype, *args, **kwargs):
                if doctype == 'Company':
                    return [{'name': 'A', 'default_currency': 'USD'}, {'name': 'B', 'default_currency': 'EUR'}]
                return super().list(doctype, *args, **kwargs)
        with self.assertRaisesRegex(ERPError, 'ambiguous'):
            self.preview(Agent(AmbiguousERP()))
        for qty, rate in [('1e999', 29), ('1e-999', 29), (100, '1e999'), ('1.00000000000000001', 29)]:
            with self.subTest(qty=qty, rate=rate), self.assertRaises(ValueError):
                Agent(FakeERP()).proposal_po('Tongling Magnet Wire Co.', 'RM-COIL-CU-2.0', qty, 'Meter', rate)

    def test_readback_difference_is_reported_without_recreating(self):
        erp = FakeERP()
        agent = Agent(erp)
        result = agent.confirm(self.preview(agent)['proposal_id'])
        self.assertTrue(result['review_required'])
        self.assertIn('items', result['differences_from_preview'])
        self.assertEqual(len(erp.created), 1)


class TestCompleteAggregation(unittest.TestCase):
    def test_more_than_one_page_and_decimal_sums(self):
        client = ERPNextClient()
        rows = [{'name': f'{i:03}', 'currency': 'USD', 'outstanding_amount': 0.1} for i in range(205)]
        with patch.object(client, 'count', return_value=205), patch.object(client, 'list', side_effect=lambda d, f, filters, limit, offset, order: rows[offset:offset+limit]) as listing:
            result = client.aggregate('Any New DocType', group_by=['currency'], sum_fields=['outstanding_amount'])
        self.assertTrue(result['complete'])
        self.assertEqual(result['groups'][0]['sums']['outstanding_amount'], '20.5')
        self.assertEqual(listing.call_count, 3)

    def test_duplicate_partial_missing_field_and_changed_count_fail_loudly(self):
        scenarios = [([{'name': 'a', 'amount': 1}, {'name': 'a', 'amount': 2}], [2, 2]),
                     ([{'name': 'a'}], [1, 1]), ([], [1, 1]),
                     ([{'name': 'a', 'amount': 1}], [1, 2])]
        for rows, counts in scenarios:
            with self.subTest(rows=rows, counts=counts), patch.object(ERPNextClient, 'count', side_effect=counts), \
                 patch.object(ERPNextClient, 'list', return_value=rows), self.assertRaises(ERPError):
                ERPNextClient().aggregate('Invoice', sum_fields=['amount'])

    def test_page_metadata_makes_truncation_explicit(self):
        client = ERPNextClient()
        with patch.object(client, 'list', return_value=[{'name': str(i)} for i in range(20)]), \
             patch.object(client, 'count', return_value=25):
            result = LLMRunner(Agent(client))._tool('list_documents', {'doctype': 'Sales Order'})
        self.assertTrue(result['pagination']['has_more'])
        self.assertEqual(result['pagination']['next_offset'], 20)


class TestConversationRecovery(unittest.TestCase):
    def test_model_cannot_dispatch_a_write_or_confirmation_tool(self):
        erp = FakeERP()
        runner = LLMRunner(Agent(erp))
        for name in ('create_document', 'confirm', 'cancel_document', 'execute_sql'):
            with self.subTest(tool=name), self.assertRaises(ValueError):
                runner._tool(name, {'doctype': 'Purchase Order', 'docstatus': 1})
        self.assertEqual(erp.created, [])

    def test_failed_tool_turn_is_not_committed_to_next_conversation(self):
        runner = LLMRunner(Agent(FakeERP()))
        runner.key = 'test-key'
        runner.model = 'test-model'
        history = []
        tool = {'role': 'assistant', 'tool_calls': [{'id': 'call_x', 'type': 'function',
                'function': {'name': 'get_document', 'arguments': '{"doctype":"Item","name":"x"}'}}]}
        first = io.BytesIO(json.dumps({'choices': [{'message': tool}]}).encode())
        with patch('agent.urlopen', side_effect=[first, TimeoutError('lost response')]), self.assertRaisesRegex(RuntimeError, 'lost response'):
            runner.ask('First question', history)
        self.assertEqual(history, [])
        self.assertEqual(runner.last_trace[-1]['role'], 'tool')
        with patch('agent.urlopen', return_value=io.BytesIO(json.dumps({'choices': [{'message': {'role': 'assistant', 'content': 'Recovered'}}]}).encode())):
            answer, _ = runner.ask('Retry', history)
        self.assertEqual(answer, 'Recovered')
        self.assertNotIn('call_x', json.dumps(history))


class TestDecimalCalculation(unittest.TestCase):
    def test_net_cash_and_decimal_rounding(self):
        self.assertEqual(calculate('58990 - 57561')['result'], '1429')
        self.assertEqual(calculate('0.1 + 0.2')['result'], '0.3')
        self.assertEqual(calculate('(600 - 575.2) / 600 * 100')['result'][:4], '4.13')

    def test_calculator_rejects_code_and_unbounded_arithmetic(self):
        for expression in ["__import__('os').getcwd()", '1/0', '2**999999', '1e9999', '[1][0]']:
            with self.subTest(expression=expression), self.assertRaises((ValueError, SyntaxError)):
                calculate(expression)
