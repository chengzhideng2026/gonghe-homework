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
        runner.base, runner.key, runner.model = 'https://example.invalid/v1', 'test-key', 'test-model'
        messages = [bin_trace()[0], {'role': 'assistant', 'content': '20件已发到生产线。'},
                    {'role': 'assistant', 'content': 'WIP仓当前有20件；未核实转料历史。'}]
        def respond(request, timeout):
            return io.BytesIO(json.dumps({'choices': [{'message': messages.pop(0), 'finish_reason': 'stop'}]}).encode())
        with patch('agent.urlopen', side_effect=respond), patch.object(runner, '_tool', return_value={'records': []}):
            answer, _ = runner.ask('库存多少？')
        self.assertEqual(answer, 'WIP仓当前有20件；未核实转料历史。')
        self.assertTrue(any('PROGRAM EVIDENCE CHECK' in (m.get('content') or '') for m in runner.last_trace))

    def test_runner_fails_closed_if_repair_still_asserts_history(self):
        runner = LLMRunner(Agent(Mock()))
        runner.base, runner.key, runner.model = 'https://example.invalid/v1', 'test-key', 'test-model'
        history = []
        messages = [bin_trace()[0], {'role': 'assistant', 'content': '20件已发到生产线。'},
                    {'role': 'assistant', 'content': '材料已经转入车间。'}]
        def respond(request, timeout):
            return io.BytesIO(json.dumps({'choices': [{'message': messages.pop(0), 'finish_reason': 'stop'}]}).encode())
        with patch('agent.urlopen', side_effect=respond), patch.object(runner, '_tool', return_value={'records': []}), \
                self.assertRaisesRegex(RuntimeError, 'after one repair'):
            runner.ask('库存多少？', history)
        self.assertEqual(history, [])

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
