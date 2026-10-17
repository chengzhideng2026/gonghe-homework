import io
import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from agent import Agent, ERPNextClient, LLMRunner
from aggregation_checks import aggregate_rollups, subtotal_checks, subtotal_issues
from execution_trace import ExecutionTraceWriter
from read_policy import ReadPolicy


def response(message):
    return io.BytesIO(json.dumps({'choices': [{'message': message, 'finish_reason': 'stop'}]}).encode())


def calls(specs):
    return {'role': 'assistant', 'tool_calls': [
        {'id': str(index), 'type': 'function', 'function': {'name': name, 'arguments': json.dumps(args)}}
        for index, (name, args) in enumerate(specs)]}


def trace(groups, complete=True):
    return [calls([('aggregate_documents', {})]), {'role': 'tool', 'tool_call_id': '0',
            'content': json.dumps({'ok': True, 'data': {'complete': complete, 'groups': groups}})}]


def fixture(amounts, delta):
    groups, tables = [], []
    for index, values in enumerate(amounts):
        lines = ['| Entity | Count | Amount |', '|---|---:|---:|']
        for n, value in enumerate(values):
            entity = f'Entity-{index}-{n}'
            groups.append({'group': {'entity': entity, 'segment': f'Segment-{index}', 'currency': 'USD'},
                           'count': 1, 'sums': {'amount': str(value)}})
            lines.append(f'| {entity} | 1 | {value} |')
        correct = sum((Decimal(str(v)) for v in values), Decimal(0))
        wrong = correct + delta * (1 if index == 0 else -1)
        lines.append(f'| **Subtotal** | {len(values)} | {wrong} |')
        tables.append('\n'.join(lines))
    return groups, '\n\n'.join(tables)


class TestSubtotalArithmetic(unittest.TestCase):
    def test_program_rollups_recompute_counts_and_amounts_and_keep_partitions(self):
        groups, _ = fixture([['12.10', '13.20'], ['21.30', '22.40']], Decimal(0))
        groups.append({'group': {'entity': 'Other', 'segment': 'Segment-0', 'currency': 'EUR'},
                       'count': 3, 'sums': {'amount': '9.99'}})
        rollups = aggregate_rollups({'complete': True, 'groups': groups})
        segment = next(r for r in rollups if r['group_by'] == ['segment', 'currency'])
        self.assertEqual(segment['groups'], [
            {'group': {'segment': 'Segment-0', 'currency': 'USD'}, 'count': 2, 'sums': {'amount': '25.30'}},
            {'group': {'segment': 'Segment-1', 'currency': 'USD'}, 'count': 2, 'sums': {'amount': '43.70'}},
            {'group': {'segment': 'Segment-0', 'currency': 'EUR'}, 'count': 3, 'sums': {'amount': '9.99'}}])
        self.assertEqual(aggregate_rollups({'complete': False, 'groups': groups}), [])
        self.assertEqual(aggregate_rollups({'complete': True, 'groups': groups * 101}), [])

    def test_each_subtotal_checked_when_opposite_errors_leave_grand_total_equal(self):
        for amounts, delta in [([['0.10', '0.20'], ['1.30', '2.40']], Decimal('.01')),
                               ([['100.01', '-19.05'], ['13.07', '0']], Decimal('3')),
                               ([['1234.56', '789.01'], ['99.99', '10.01']], Decimal('17.23'))]:
            with self.subTest(amounts=amounts):
                groups, answer = fixture(amounts, delta)
                checks = subtotal_checks(answer, trace(groups))
                self.assertEqual(len(checks), 2)
                self.assertTrue(all(row['status'] == 'mismatch' for row in checks))
                self.assertEqual(sum(Decimal(row['reported'][1]) for row in checks),
                                 sum(Decimal(row['expected'][1]) for row in checks))
                self.assertTrue(subtotal_issues(checks))

    def test_correct_and_partial_or_unmatched_tables_are_distinguished(self):
        groups, answer = fixture([['2.15', '3.05'], ['7.01', '9.09']], Decimal(0))
        self.assertTrue(all(c['status'] == 'ok' for c in subtotal_checks(answer, trace(groups))))
        self.assertEqual(subtotal_checks(answer, trace(groups, False)), [])
        self.assertEqual(subtotal_checks(answer.replace('2.15', '2.16'), trace(groups))[-1]['status'], 'ok')
        # The changed detail table is unsupported, not silently certified.
        self.assertEqual(len(subtotal_checks(answer.replace('2.15', '2.16'), trace(groups))), 1)

    def test_original_failure_detects_both_errors_from_complete_tool_groups(self):
        original = json.loads((Path(__file__).resolve().parents[1] / 'evidence/n05_n07_original.json').read_text(encoding='utf-8'))
        turn = next(c for c in original['cases'] if c['id'] == 'N05')['turns'][0]
        checks = subtotal_checks(turn['answer'], turn['history'])
        self.assertEqual(len(checks), 2)
        self.assertTrue(all(c['status'] == 'mismatch' for c in checks))
        self.assertEqual(sum(Decimal(c['reported'][1]) for c in checks),
                         sum(Decimal(c['expected'][1]) for c in checks))

    def test_real_ask_repairs_subtotals_using_existing_groups_without_extra_erp(self):
        groups, wrong = fixture([['12.10', '13.20'], ['21.30', '22.40']], Decimal('2'))
        _, correct = fixture([['12.10', '13.20'], ['21.30', '22.40']], Decimal(0))
        client = ERPNextClient(base='http://127.0.0.1:8080')
        client.read_policy = ReadPolicy(interval=0, max_requests=30)
        runner = LLMRunner(Agent(client)); runner.key, runner.model = 'test-key', 'test-model'
        rows = [{'name': str(i), **g['group'], 'amount': g['sums']['amount']} for i, g in enumerate(groups)]
        replies = [calls([('aggregate_documents', {'doctype': 'Ledger', 'group_by': ['entity', 'segment', 'currency'],
                                                   'sum_fields': ['amount']})]),
                   {'role': 'assistant', 'content': wrong}, {'role': 'assistant', 'content': correct}]
        requests = []
        def model(request, timeout):
            requests.append(json.loads(request.data)); return response(replies.pop(0))
        def erp(method, path, **kwargs):
            return len(rows) if path.endswith('get_count') else rows
        with tempfile.TemporaryDirectory() as directory:
            runner.trace_writer = ExecutionTraceWriter(directory)
            with patch('agent.urlopen', side_effect=model), patch.object(client, '_http_req', side_effect=erp) as wire:
                answer, _ = runner.ask('Report grouped totals.', [])
            self.assertEqual(answer, correct)
            self.assertEqual(wire.call_count, 3)
            self.assertEqual([c['status'] for c in runner.last_subtotal_checks], ['mismatch', 'mismatch', 'ok', 'ok'])
            self.assertTrue(any('PROGRAM EVIDENCE CHECK' in (m.get('content') or '') for m in requests[-1]['messages']))
            record = json.loads((Path(directory) / (runner.turn_id + '.json')).read_text(encoding='utf-8'))
            self.assertEqual(record['subtotal_checks'], runner.last_subtotal_checks)

    def test_real_ask_rejects_second_bad_answer_and_preserves_history(self):
        groups, wrong = fixture([['1', '2'], ['3', '4']], Decimal('1'))
        runner = LLMRunner(Agent(ERPNextClient())); runner.key, runner.model = 'test-key', 'test-model'
        replies = [calls([('aggregate_documents', {'doctype': 'Ledger'})]),
                   {'role': 'assistant', 'content': wrong}, {'role': 'assistant', 'content': wrong}]
        history = []
        with tempfile.TemporaryDirectory() as directory:
            runner.trace_writer = ExecutionTraceWriter(directory)
            with patch('agent.urlopen', side_effect=lambda request, timeout: response(replies.pop(0))), \
                    patch.object(runner.agent.c, 'aggregate', return_value={'complete': True, 'groups': groups}), \
                    self.assertRaisesRegex(RuntimeError, 'after one repair'):
                runner.ask('Grouped report.', history)
        self.assertEqual(history, [])
        self.assertEqual(len(runner.last_subtotal_checks), 4)


class TestProjectionRecovery(unittest.TestCase):
    def test_real_ask_reuses_metadata_and_reads_only_unique_matching_parents(self):
        c = ERPNextClient(base='http://127.0.0.1:8080'); c.read_policy = ReadPolicy(max_requests=30, interval=0)
        runner = LLMRunner(Agent(c)); runner.key, runner.model = 'test-key', 'test-model'
        child_filters = [['sku', '=', 'Target']]
        parent_filters = [['docstatus', '=', 1], ['transaction_date', '<=', '2030-02-01'],
                          ['Detail Row', 'sku', '=', 'Target']]
        specs = [('get_doctype_meta', {'doctype': 'Parent Ledger'}), ('get_doctype_meta', {'doctype': 'Parent Ledger'}),
                 ('list_documents', {'doctype': 'Detail Row', 'fields': ['parent', 'qty'], 'filters': child_filters}),
                 ('aggregate_documents', {'doctype': 'Detail Row', 'group_by': ['parent'], 'sum_fields': ['qty'], 'filters': child_filters}),
                 ('list_documents', {'doctype': 'Parent Ledger', 'fields': ['name'], 'filters': parent_filters}),
                 ('get_documents', {'doctype': 'Parent Ledger', 'names': ['P1', 'P1', 'P2']})]
        replies = [calls(specs), {'role': 'assistant', 'content': 'Protocol fixture; not a business acceptance answer.'}]
        sent = []
        def erp(method, path, **kwargs):
            sent.append((method, path, kwargs))
            if path.endswith('getdoctype'):
                return {'docs': [{'doctype': 'DocType', 'name': 'Parent Ledger', 'fields': [
                    {'fieldname': 'lines', 'fieldtype': 'Table', 'options': 'Detail Row'}]}]}
            if path.endswith('get_count'):
                return 2 if kwargs['params']['doctype'] == 'Detail Row' else 3
            if path.endswith('/Detail%20Row'):
                return [{'name': 'L1'}, {'name': 'L2'}]
            if path.endswith('/Parent%20Ledger'):
                self.assertEqual(json.loads(kwargs['params']['filters']), parent_filters)
                return [{'name': 'P1'}, {'name': 'P1'}, {'name': 'P2'}]
            return {'name': path.rsplit('/', 1)[-1], 'doctype': 'Parent Ledger', 'docstatus': 1,
                    'transaction_date': '2030-01-01', 'currency': 'USD',
                    'lines': [{'sku': 'Target', 'qty': 1, 'uom': 'Each', 'amount': 5}]}
        with tempfile.TemporaryDirectory() as directory:
            runner.trace_writer = ExecutionTraceWriter(directory)
            with patch('agent.urlopen', side_effect=lambda request, timeout: response(replies.pop(0))), \
                    patch.object(c, '_http_req', side_effect=erp):
                runner.ask('Summarize selected child rows.', [])
        receipts = runner.receipts()
        self.assertEqual(len(sent), 7)
        self.assertEqual(runner.last_io['http_attempts'], 7)
        self.assertEqual(receipts[1]['io']['cache_hits'], 1)
        self.assertEqual(receipts[3]['status'], 'error')
        self.assertIn('No ERP request sent', receipts[3]['error'])
        self.assertEqual(receipts[3]['io']['http_attempts'], 0)
        self.assertEqual(receipts[4]['summary']['pagination']['unique_names_returned'], 2)
        self.assertEqual(receipts[5]['summary']['requested_names'], ['P1', 'P2'])
        self.assertTrue(receipts[5]['summary']['complete'])
        self.assertTrue(all(method == 'GET' for method, _, _ in sent))
