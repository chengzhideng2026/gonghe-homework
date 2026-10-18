"""Narrow provenance/table regressions; scripted replies do not prove model behavior."""
import io
import json
import tempfile
import unittest
from unittest.mock import patch

from agent import Agent, ERPError, ERPNextClient, LLMRunner, calculate
from answer_checks import evidence_issues
from execution_trace import ExecutionTraceWriter
from test_answer_checks import bin_trace
from test_replenishment_boundaries import calls, final


# Frozen previous protocol text, not obtained from the implementation under test.
LEGACY_BOUNDARIES = (
    ' [ANSWER EVIDENCE BOUNDARIES v1] Keep answers brief: report only the requested facts and '
    'their necessary scope. Omit unrequested fields even when returned by a tool. '
    'Current balances, amounts outstanding and totals, including equal values, establish '
    'current field values only; they do not establish that payments, allocations or write-offs '
    'never occurred. Do not reconstruct historical events or hypothetical causes from a snapshot. '
    'Reservation conclusions are limited to the reservation fields actually returned for '
    'the queried item and warehouse. Zero in some fields does not establish zero in other '
    'reservation types; unqueried fields remain unknown. '
    'Distinguish local proposal state, prospective payload docstatus and actual ERP document '
    'state. A local pending preview with intended docstatus=0 is not evidence of an existing '
    'ERP Draft. Report actual ERP names/status only from ERP results, and use the confirmation '
    'journal for execution state, never an old chat summary. '
    'When evidence is insufficient, narrow the claim. Do not expand queries to justify '
    'unrequested history, other reservation types or additional state explanations.')


def calculation_trace(expression, identity='calc'):
    return [calls((identity, 'calculate', {'expression': expression})),
            {'role': 'tool', 'tool_call_id': identity,
             'content': json.dumps({'ok': True, 'data': calculate(expression)})}]


class TestCurrencySources(unittest.TestCase):
    def test_compact_code_and_chinese_user_quotes_are_accepted_with_attribution(self):
        for question, answer in [
                ('Use USD10 as input.', 'User-provided price: USD10.'),
                ('按10美元预算。', '用户提供单价：10 USD。'),
                ('报价每米27欧元。', '单价 EUR27/Meter（用户提供）。'),
                ('报价每米27欧元。', '用户提供EUR27/Meter（非ERP报价）。'),
                ('报价每米27欧元。', '27欧元来自您的口述报价。'),
                ('报价每米27欧元。', 'EUR27, quoted by you.'),
                ('输入10.00USD。', '来源：用户，USD 10。')]:
            with self.subTest(question=question):
                self.assertFalse(evidence_issues(answer, [{'role': 'user', 'content': question}]))

    def test_user_quote_does_not_become_erp_fact_or_global_currency_permission(self):
        trace = [{'role': 'user', 'content': '预算是USD10。'},
                 *bin_trace(records=[{'name': 'B', 'stock_value': 10}])]
        for answer in ['ERP库存金额USD10。', '库存金额 USD 10。',
                       '用户提供USD10；ERP库存金额USD10。',
                       '用户提供USD10，ERP库存金额USD10。']:
            with self.subTest(answer=answer):
                self.assertTrue(evidence_issues(answer, trace))
        self.assertFalse(evidence_issues('用户提供USD10；库存金额10，币种未核实。', trace))

    def test_wrong_user_amount_or_currency_is_not_saved_by_erp_default_currency(self):
        trace = [{'role': 'user', 'content': '报价27 EUR/Meter。'},
                 *bin_trace('Company', [{'name': 'ORG', 'default_currency': 'USD'}]),
                 *calculation_trace('27 * 4')]
        for answer in ['用户报价 EUR28。', '按用户报价计算总额USD108。', '用户报价 USD27。']:
            with self.subTest(answer=answer):
                self.assertTrue(evidence_issues(answer, trace))

    def test_user_derived_amount_needs_matching_calculation_and_input(self):
        user = [{'role': 'user', 'content': '报价27欧元每米，买4米。'}]
        answer = '按用户报价计算总额 EUR108。'
        self.assertTrue(evidence_issues(answer, user))
        self.assertTrue(evidence_issues(answer, user + calculation_trace('36 * 3')))
        self.assertTrue(evidence_issues(answer, user + calculation_trace('27 * 3')))
        self.assertFalse(evidence_issues(answer, user + calculation_trace('27 * 4')))
        failed = calculation_trace('27 * 4')
        failed[-1]['content'] = '{"ok":false,"error":"failed"}'
        self.assertTrue(evidence_issues(answer, user + failed))

    def test_mixed_user_currencies_do_not_authorize_implicit_conversion(self):
        trace = [{'role': 'user', 'content': '一项EUR27，另一项USD4。'},
                 *calculation_trace('27 + 4')]
        self.assertTrue(evidence_issues('按用户条件计算合计EUR31。', trace))

    def test_old_user_and_calculate_evidence_do_not_leak_into_current_turn(self):
        old = [{'role': 'user', 'content': '报价EUR27。'},
               *calculation_trace('27 * 4'), final('用户报价EUR27。')]
        current = [{'role': 'user', 'content': '现在查询另一笔金额。'}]
        self.assertTrue(evidence_issues('用户报价EUR27。', old + current))
        self.assertTrue(evidence_issues('按用户报价计算总额EUR108。', old + current))
        repeat = [{'role': 'user', 'content': '本轮条件还是EUR27，数量4。'},
                  *calculation_trace('27 * 4', 'new')]
        self.assertFalse(evidence_issues('按用户条件计算总额EUR108。', old + repeat))

    def test_repair_feedback_is_not_a_new_user_quote(self):
        trace = [{'role': 'user', 'content': '查询库存金额。'},
                 {'role': 'user', 'content': '[PROGRAM EVIDENCE CHECK] User quote USD10.'}]
        self.assertTrue(evidence_issues('用户报价USD10。', trace))

    def test_explicit_earlier_user_source_is_reusable_without_becoming_current_erp_fact(self):
        trace = [{'role': 'user', 'content': '用户条件EUR27。'}, final('已记录。'),
                 {'role': 'user', 'content': '沿用上一轮用户条件，计算4份总额。'},
                 *calculation_trace('27 * 4')]
        self.assertFalse(evidence_issues('上一轮用户提供EUR27。', trace))
        self.assertFalse(evidence_issues('按上一轮用户报价计算总额EUR108。', trace))
        self.assertTrue(evidence_issues('ERP金额EUR108。', trace))
        without_current_calc = trace[:-2]
        self.assertTrue(evidence_issues('按上一轮用户报价计算总额EUR108。', without_current_calc))

    def test_current_erp_currency_remains_usable_and_wrong_currency_rejected(self):
        trace = [{'role': 'user', 'content': '查询库存金额。'},
                 *bin_trace(records=[{'name': 'B', 'stock_value': 10, 'currency': 'USD'}])]
        self.assertFalse(evidence_issues('ERP库存金额USD10。', trace))
        self.assertTrue(evidence_issues('ERP库存金额EUR10。', trace))


class TestMarkdownTableBoundaries(unittest.TestCase):
    first = '| Item | Required | actual_qty | shortage |\n|---|---:|---:|---:|\n| PART-A | 14 | 9 | 5 |'

    def test_adjacent_unrelated_table_is_not_read_with_first_table_columns(self):
        other = '| Label | Price | Quantity | Value |\n|---|---:|---:|---:|\n| OTHER | 1 | 2 | 99 |'
        for separator in ['\n', '\n\n', '\n## Prices\n']:
            with self.subTest(separator=separator):
                self.assertFalse(evidence_issues(self.first + separator + other, []))

    def test_adjacent_shortage_tables_use_their_own_column_order(self):
        other = '| Shortage | Item | Required | actual_qty |\n|---:|---|---:|---:|\n| 2 | PART2 | 8 | 6 |'
        self.assertFalse(evidence_issues(self.first + '\n' + other, []))
        self.assertTrue(evidence_issues(self.first + '\n' + other.replace('| 2 |', '| 3 |'), []))

    def test_heading_prose_or_blank_ends_table_before_stray_pipe_row(self):
        for separator in ['\n# Next\n', '\nExplanation.\n', '\n\n']:
            with self.subTest(separator=separator):
                self.assertFalse(evidence_issues(self.first + separator + '| OTHER | 1 | 2 | 99 |', []))

    def test_missing_columns_separator_or_row_cells_are_not_complete_tables(self):
        for table in [
                '| Item | Required | Shortage |\n|---|---|---|\n| X | 5 | 99 |',
                '| Item | Required UOM | Available UOM | Shortage |\n|---|---|---|---|\n| X | 5 | 2 | 99 |',
                '| Item | Required | actual_qty | shortage |\n| X | 5 | 2 | 99 |',
                '| Item | Required | actual_qty | shortage |\n|---|---|---|---|\n| X | 5 | 99 |']:
            with self.subTest(table=table):
                self.assertFalse(evidence_issues(table, []))

    def test_fenced_example_is_not_a_rendered_shortage_table(self):
        wrong = self.first.replace('| 5 |', '| 99 |')
        for fence in ['```', '~~~']:
            with self.subTest(fence=fence):
                self.assertFalse(evidence_issues(fence + '\n' + wrong + '\n' + fence + '\n' + self.first, []))
                self.assertTrue(evidence_issues(fence + '\nexample\n' + fence + '\n' + wrong, []))

    def test_unit_columns_before_quantities_do_not_become_numeric_columns(self):
        table = ('| Item | Required UOM | Required | Available UOM | Available | Shortage |\n'
                 '|---|---|---:|---|---:|---:|\n| X | Each | 8 | Each | 6 | 2 |')
        self.assertFalse(evidence_issues(table, []))
        self.assertTrue(evidence_issues(table.replace('| Each | 6', '| Meter | 6'), []))
        self.assertTrue(evidence_issues(table.replace('| 2 |', '| 3 |'), []))


class TestSourceProtocol(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.client = ERPNextClient(base='https://example.invalid', key='test', secret='test')
        self.runner = LLMRunner(Agent(self.client))
        self.runner.key, self.runner.model = 'test-key', 'test-model'
        self.runner.base = 'https://example.invalid/v1'
        self.runner.trace_writer = ExecutionTraceWriter(directory.name)
        self.requests = []
        self.create = patch.object(self.client, 'create', side_effect=AssertionError('No write allowed'))
        self.create.start()
        self.addCleanup(self.create.stop)

    def ask(self, question, replies, history=None):
        replies = list(replies)
        def model(request, timeout):
            self.requests.append(json.loads(request.data))
            return io.BytesIO(json.dumps({'choices': [{'message': replies.pop(0),
                                                       'finish_reason': 'stop'}]}).encode())
        with patch('agent.urlopen', side_effect=model):
            result = self.runner.ask(question, history)
        self.assertEqual(replies, [])
        return result

    def body(self, identity):
        return next(json.loads(m['content']) for m in self.runner.last_trace
                    if m.get('tool_call_id') == identity)

    def test_payment_shortlist_warning_then_generic_batch_exposes_actual_allocations(self):
        parent = {'doctype': 'Payment Entry', 'name': 'PAY-A', 'docstatus': 1,
                  'company': 'ORG-A', 'party': 'CLIENT-A', 'payment_type': 'Receive',
                  'paid_amount': 30, 'reference_no': 'INV-A', 'references': [
                      {'reference_doctype': 'Sales Invoice', 'reference_name': 'INV-A', 'allocated_amount': 22},
                      {'reference_doctype': 'Sales Invoice', 'reference_name': 'INV-B', 'allocated_amount': 8}]}
        with patch.object(self.client, 'list', return_value=[{k: v for k, v in parent.items() if k != 'references'}]), \
                patch.object(self.client, 'get', return_value=parent) as get:
            self.ask('核实CLIENT-A在ORG-A的收款核销关联。', [
                calls(('shortlist', 'list_documents', {'doctype': 'Payment Entry',
                       'filters': [['party', '=', 'CLIENT-A'], ['company', '=', 'ORG-A'],
                                   ['docstatus', '=', 1]], 'include_total': False})),
                calls(('parents', 'get_documents', {'doctype': 'Payment Entry', 'names': ['PAY-A', 'PAY-A']})),
                final('已提交PAY-A的references显示：INV-A核销22，INV-B核销8。')])
        get.assert_called_once_with('Payment Entry', 'PAY-A')
        self.assertIn('reference_no is reference text', ' '.join(self.body('shortlist')['data']['warnings']))
        batch = self.body('parents')['data']
        self.assertTrue(batch['complete'])
        self.assertEqual(batch['results'][0]['data'], parent)
        policy = self.requests[0]['messages'][0]['content']
        for field in ['reference_doctype', 'reference_name', 'allocated_amount', 'docstatus=1']:
            self.assertIn(field, policy)

    def test_payment_empty_missing_draft_and_failed_details_stay_distinct(self):
        documents = [{'name': 'EMPTY', 'docstatus': 1, 'references': []},
                     {'name': 'MISSING', 'docstatus': 1},
                     {'name': 'DRAFT', 'docstatus': 0, 'references': [
                         {'reference_doctype': 'Sales Invoice', 'reference_name': 'INV-A', 'allocated_amount': 3}]},
                     ERPError('HTTP 403 permission denied')]
        with patch.object(self.client, 'get', side_effect=documents):
            self.ask('核实核销，不得把缺明细当无收款。', [
                calls(('parents', 'get_documents', {'doctype': 'Payment Entry',
                       'names': ['EMPTY', 'MISSING', 'DRAFT', 'DENIED']})),
                final('只读到EMPTY空子表、MISSING缺字段及DRAFT草稿；DENIED权限不足，关联尚未核实。')])
        batch = self.body('parents')['data']
        self.assertFalse(batch['complete'])
        self.assertEqual(batch['results'][0]['data']['references'], [])
        self.assertNotIn('references', batch['results'][1]['data'])
        self.assertEqual(batch['results'][2]['data']['docstatus'], 0)
        self.assertFalse(batch['results'][3]['ok'])
        self.assertIn('403', batch['results'][3]['error'])

    def test_explicit_foreign_quote_is_user_input_not_erp_verified_or_executable(self):
        with patch.object(self.client, 'get', return_value={
                'doctype': 'Supplier', 'name': 'SUP-A', 'accounts': [], 'companies': []}):
            answer, _ = self.ask('只作初步方案，供应商SUP-A报价每米27欧元，采购4米；公司用美元，汇率未定。', [
                calls(('supplier', 'get_document', {'doctype': 'Supplier', 'name': 'SUP-A'})),
                calls(('total', 'calculate', {'expression': '4 * 27'})),
                final('用户提供报价27 EUR/Meter；按用户报价计算总额108 EUR。供应商主档accounts和companies为空，'
                      '仅说明本次主档字段无数据。初步方案不可执行，仍缺约定的本位币价格，不自行换汇。')])
        self.assertIn('108 EUR', answer)
        self.assertEqual(self.body('total')['data']['result'], '108')
        self.assertEqual(self.runner.agent.proposals, {})
        self.assertFalse(any('PROGRAM EVIDENCE CHECK' in (m.get('content') or '') for m in self.runner.last_trace))
        self.assertEqual(len(self.requests[0]['tools']), 9)

    def test_valid_base_currency_preview_total_needs_no_duplicate_calculate_call(self):
        def parties(doctype, *args, **kwargs):
            return {'Item': [{'name': 'PART-A', 'stock_uom': 'Meter'}],
                    'Supplier': [{'name': 'SUP-A'}],
                    'Company': [{'name': 'ORG-A', 'default_currency': 'USD'}]}[doctype]
        with patch.object(self.client, 'list', side_effect=parties):
            answer, _ = self.ask('只预览，供应商SUP-A，PART-A，6米，报价USD1.75/Meter。', [
                calls(('preview', 'prepare_purchase_order', {'supplier': 'SUP-A', 'item': 'PART-A',
                       'qty': 6, 'uom': 'Meter', 'rate': 1.75, 'currency': 'USD'})),
                final('按用户报价计算的本地预览总额USD10.50。仅本地pending，未创建对应ERP单据。')])
        self.assertIn('USD10.50', answer)
        preview = self.body('preview')['data']
        self.assertEqual(preview['estimated_total'], '10.50')
        self.assertEqual(preview['local_state'], 'pending')
        self.assertIsNone(preview['erp_document'])
        self.assertEqual(len(self.runner.agent.proposals), 1)

    def test_policy_upgrade_replaces_old_block_and_retains_unrelated_rules(self):
        history = [{'role': 'system', 'content': 'Keep this rule.' + LEGACY_BOUNDARIES + ' Keep another rule.'},
                   {'role': 'user', 'content': 'Previous task.'}, final('Previous answer.')]
        _, history = self.ask('继续。', [final('请提供业务问题。')], history)
        self.ask('稍后。', [final('好的。')], history)
        for request in self.requests:
            system = request['messages'][0]['content']
            self.assertNotIn('[ANSWER EVIDENCE BOUNDARIES v1]', system)
            self.assertEqual(system.count('[ANSWER EVIDENCE BOUNDARIES v2]'), 1)
            self.assertIn('Keep this rule.', system)
            self.assertIn('Keep another rule.', system)

    def test_user_usd_input_passes_without_erp_but_does_not_authorize_next_turn_erp_amount(self):
        answer, history = self.ask('用户条件是USD10，请复述。', [final('用户提供USD10。')])
        self.assertEqual(answer, '用户提供USD10。')
        with patch.object(self.client, 'get', return_value={'name': 'B', 'stock_value': 10}):
            answer, _ = self.ask('查另一笔库存价值。', [
                calls(('stock', 'get_document', {'doctype': 'Bin', 'name': 'B'})),
                final('ERP库存金额USD10。'),
                final('ERP库存金额10，币种未核实。')], history)
        self.assertEqual(answer, 'ERP库存金额10，币种未核实。')
        self.assertEqual(sum('PROGRAM EVIDENCE CHECK' in (m.get('content') or '')
                             for m in self.runner.last_trace), 1)

    def test_bin_warning_limits_reservations_to_warehouse_even_when_demand_equals_it(self):
        with patch.object(self.client, 'list', return_value=[{
                'name': 'B', 'item_code': 'PART-A', 'warehouse': 'STORE-A', 'reserved_qty_for_production': 12}]):
            self.ask('需求12，报告该仓生产预留。', [
                calls(('stock', 'list_documents', {'doctype': 'Bin', 'include_total': False})),
                final('仓级生产预留12；仅凭相等数量不能断言属于某工单。')])
        self.assertIn('order-level link', ' '.join(self.body('stock')['data']['warnings']))
