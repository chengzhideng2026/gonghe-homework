import io
import json
import unittest
from unittest.mock import Mock, patch
from answer_checks import evidence_issues
from agent import Agent, LLMRunner


def bin_trace(doctype='Bin', records=None, call_id='c'):
    return [
        {'role': 'assistant', 'tool_calls': [{'id': call_id, 'function':
             {'name': 'list_documents', 'arguments': json.dumps({'doctype': doctype})}}]},
        {'role': 'tool', 'tool_call_id': call_id,
         'content': json.dumps({'ok': True, 'data': {'records': records or []}})},
    ]


class TestEvidenceChecks(unittest.TestCase):
    def test_currency_amount_requires_matching_returned_currency(self):
        no_currency = bin_trace(records=[{'name': 'BIN-1', 'stock_value': '11400'}])
        self.assertTrue(evidence_issues('库存金额为 USD 11,400。', no_currency))
        self.assertTrue(evidence_issues('库存金额为 $11,400。', no_currency))
        self.assertFalse(evidence_issues('库存金额为 11,400；Bin 未返回币种。', no_currency))

        usd = bin_trace(records=[{'name': 'BIN-1', 'stock_value': '11400', 'currency': 'USD'}])
        self.assertFalse(evidence_issues('库存金额为 USD 11,400。', usd))
        self.assertTrue(evidence_issues('库存金额为 EUR 11,400。', usd))

    def test_currency_boundary_does_not_treat_unrelated_words_as_amount_claims(self):
        no_currency = bin_trace(records=[{'name': 'BIN-1', 'stock_value': '11400'}])
        for answer in ('币种未知。', '按 ERP 原值列示，不能证明是 USD。',
                       'USD 是公司默认币种，但本次返回的 Bin 没有币种字段。'):
            with self.subTest(answer=answer):
                self.assertFalse(evidence_issues(answer, no_currency))

    def test_currency_does_not_leak_from_an_unrelated_prior_turn(self):
        prior = bin_trace(records=[{'name': 'BIN-OLD', 'stock_value': '10', 'currency': 'USD'}], call_id='old')
        current = [{'role': 'user', 'content': '本轮只查看当前库存快照。'},
                   {'role': 'assistant', 'content': '库存金额为 USD 10。'}]
        self.assertTrue(evidence_issues('本轮库存金额为 USD 10。', prior + current))

        current_with_read = [
            {'role': 'user', 'content': '本轮查询金额。'},
            {'role': 'assistant', 'tool_calls': [{'id': 'now', 'function':
                {'name': 'list_documents', 'arguments': '{"doctype":"Bin"}'}}]},
            {'role': 'tool', 'tool_call_id': 'now', 'content': json.dumps({'ok': True, 'data': {
                'records': [{'name': 'BIN-NOW', 'stock_value': '10', 'currency': 'USD'}]}})},
            {'role': 'assistant', 'content': '本轮库存金额为 USD 10。'},
        ]
        self.assertFalse(evidence_issues(current_with_read[-1]['content'], prior + current_with_read))

    def test_shortage_table_uses_zero_shortage_for_surplus_rows(self):
        trace = bin_trace(records=[{'name': 'BIN-1', 'actual_qty': 205}])
        contradictory = ('| 物料 | 需求 | 实际库存 | 缺口 |\n'
                         '|---|---:|---:|---:|\n| P1 | 30 | 205 | 不缺（余175） |')
        self.assertTrue(evidence_issues(contradictory, trace))
        consistent = ('| 物料 | 需求 | 实际库存 | 缺口 | 余量 |\n'
                       '|---|---:|---:|---:|---:|\n| P1 | 30 | 205 | 0 | 175 |')
        self.assertFalse(evidence_issues(consistent, trace))

    def test_shortage_table_checks_deficit_arithmetic_without_fixed_items(self):
        trace = bin_trace(records=[{'name': 'BIN-1', 'actual_qty': 20}])
        wrong = ('| Item | Required | actual_qty | shortage |\n'
                 '|---|---:|---:|---:|\n| X | 30 | 20 | 15 |')
        self.assertTrue(evidence_issues(wrong, trace))
        right = ('| Item | Required | actual_qty | shortage |\n'
                 '|---|---:|---:|---:|\n| X | 30 | 20 | 10 |')
        self.assertFalse(evidence_issues(right, trace))

    def test_shortage_table_rejects_explicit_mixed_requirement_and_available_units(self):
        trace = bin_trace(records=[{'name': 'BIN-1', 'actual_qty': 20}])
        mixed = ('| Item | Required | Required UOM | Available | Available UOM | Shortage |\n'
                 '|---|---:|---|---:|---|---:|\n| X | 30 | Nos | 20 | Meter | 10 |')
        issues = evidence_issues(mixed, trace)
        self.assertTrue(issues)
        self.assertIn('different units', ' '.join(issues))

    def test_snapshot_rejects_movement_assertion_but_allows_location_and_uncertainty(self):
        self.assertTrue(evidence_issues('WIP仓20件已发到生产线。', bin_trace()))
        self.assertTrue(evidence_issues('20 were transferred to production.', bin_trace()))
        self.assertFalse(evidence_issues('WIP仓当前有20件；仓名不能证明已发到生产线。', bin_trace()))
        self.assertFalse(evidence_issues('Stores现货130件，WIP仓20件。', bin_trace()))

    def test_event_evidence_leaves_semantic_review_to_model_and_reviewer(self):
        events = bin_trace('Stock Entry', records=[{'name': 'MAT-STE-1'}], call_id='event')
        self.assertFalse(evidence_issues('20件已发到生产线。', bin_trace()+events))

    def test_postposed_uncertainty_and_questions_are_not_movement_assertions(self):
        for answer in [
            '这20件是否已发到生产线，尚无证据。',
            '20件已发到生产线与否，尚未核实。',
            '这20件已发到生产线了吗？',
            'Whether 20 were transferred to production remains unverified.',
            '20 were transferred to production, but this has not been verified.',
            '20 were transferred to production?',
        ]:
            with self.subTest(answer=answer):
                self.assertFalse(evidence_issues(answer, bin_trace()))
        self.assertTrue(evidence_issues(
            '20 were transferred to production. Other movements are unverified.', bin_trace()))

    def test_empty_or_failed_event_reads_do_not_relax_snapshot_check(self):
        for doctype in ('Stock Entry', 'Stock Ledger Entry'):
            events = bin_trace(doctype, call_id='event')
            self.assertTrue(evidence_issues('20件已发到生产线。', bin_trace()+events))
            events[-1]['content'] = json.dumps({'ok': False, 'error': 'query failed'})
            self.assertTrue(evidence_issues('20件已发到生产线。', bin_trace()+events))

    def test_event_detail_and_aggregate_require_nonempty_records(self):
        for tool, empty, nonempty in [
            ('get_document', {}, {'name': 'MAT-STE-1'}),
            ('aggregate_documents', {'complete': True, 'count': 0}, {'complete': True, 'count': 1}),
        ]:
            for data, allowed in ((empty, False), (nonempty, True)):
                with self.subTest(tool=tool, data=data):
                    events = [
                        {'role': 'assistant', 'tool_calls': [{'id': 'event', 'function':
                            {'name': tool, 'arguments': '{"doctype":"Stock Entry"}'}}]},
                        {'role': 'tool', 'tool_call_id': 'event', 'content': json.dumps({'ok': True, 'data': data})},
                    ]
                    self.assertEqual(not evidence_issues('20件已发到生产线。', bin_trace()+events), allowed)

    def test_repair_feedback_distinguishes_snapshot_and_history_requests(self):
        feedback = ' '.join(evidence_issues('20件已发到生产线。', bin_trace()))
        self.assertIn('If the user asks only about current stock', feedback)
        self.assertIn('If the user explicitly asks about issue/transfer history', feedback)
        self.assertNotIn('The user requested stock', feedback)

    def test_runner_repairs_once_before_accepting_final_answer(self):
        runner = LLMRunner(Agent(Mock()))
        runner.agent.c.list.return_value = []
        runner.agent.c.count.return_value = 0
        runner.base, runner.key, runner.model = 'https://example.invalid/v1', 'test-key', 'test-model'
        messages = [bin_trace()[0], {'role': 'assistant', 'content': '20件已发到生产线。'},
                    {'role': 'assistant', 'content': 'WIP仓当前有20件；未核实转料历史。'}]
        def respond(request, timeout):
            return io.BytesIO(json.dumps({'choices': [{'message': messages.pop(0), 'finish_reason': 'stop'}]}).encode())
        with patch('agent.urlopen', side_effect=respond):
            answer, _ = runner.ask('库存多少？')
        self.assertEqual(answer, 'WIP仓当前有20件；未核实转料历史。')
        self.assertTrue(any('PROGRAM EVIDENCE CHECK' in (m.get('content') or '') for m in runner.last_trace))

    def test_runner_fails_closed_if_repair_still_asserts_history(self):
        runner = LLMRunner(Agent(Mock()))
        runner.agent.c.list.return_value = []
        runner.agent.c.count.return_value = 0
        runner.base, runner.key, runner.model = 'https://example.invalid/v1', 'test-key', 'test-model'
        history = []
        messages = [bin_trace()[0], {'role': 'assistant', 'content': '20件已发到生产线。'},
                    {'role': 'assistant', 'content': '材料已经转入车间。'}]
        def respond(request, timeout):
            return io.BytesIO(json.dumps({'choices': [{'message': messages.pop(0), 'finish_reason': 'stop'}]}).encode())
        with patch('agent.urlopen', side_effect=respond), \
                self.assertRaisesRegex(RuntimeError, 'after one repair'):
            runner.ask('库存多少？', history)
        self.assertEqual(history, [])

    def test_runner_repairs_currency_claim_when_snapshot_has_no_currency(self):
        runner = LLMRunner(Agent(Mock()))
        runner.base, runner.key, runner.model = 'https://example.invalid/v1', 'test-key', 'test-model'
        replies = [
            {'role': 'assistant', 'content': '库存金额为 USD 11,400。'},
            {'role': 'assistant', 'content': '库存金额为 11,400；Bin 未返回币种。'},
        ]
        def respond(request, timeout):
            return io.BytesIO(json.dumps({'choices': [{'message': replies.pop(0), 'finish_reason': 'stop'}]}).encode())
        with patch('agent.urlopen', side_effect=respond):
            answer, _ = runner.ask('哪个物料库存金额最大？')
        self.assertEqual(answer, '库存金额为 11,400；Bin 未返回币种。')
        feedback = [m.get('content', '') for m in runner.last_trace
                    if m.get('role') == 'user' and 'PROGRAM EVIDENCE CHECK' in m.get('content', '')]
        self.assertEqual(len(feedback), 1)
        self.assertIn('currency evidence', feedback[0])

    def test_runner_checks_prior_turn_snapshot_when_followup_reuses_it(self):
        runner = LLMRunner(Agent(Mock()))
        runner.base, runner.key, runner.model = 'https://example.invalid/v1', 'test-key', 'test-model'
        history = [{'role': 'system', 'content': 'test'}, *bin_trace(),
                   {'role': 'assistant', 'content': 'WIP仓当前有20件。'}]
        messages = [{'role': 'assistant', 'content': '20件已经发到生产线。'},
                    {'role': 'assistant', 'content': 'WIP仓当前有20件，转料历史尚未核实。'}]
        def respond(request, timeout):
            return io.BytesIO(json.dumps({'choices': [{'message': messages.pop(0), 'finish_reason': 'stop'}]}).encode())
        with patch('agent.urlopen', side_effect=respond), patch.object(runner, '_tool') as tool:
            answer, _ = runner.ask('这些已经转料了吗？', history)
        self.assertEqual(answer, 'WIP仓当前有20件，转料历史尚未核实。')
        tool.assert_not_called()
        self.assertTrue(any('PROGRAM EVIDENCE CHECK' in (m.get('content') or '') for m in history))
