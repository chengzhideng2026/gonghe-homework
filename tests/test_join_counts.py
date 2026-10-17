import unittest
from unittest.mock import patch

from agent import Agent, ERPError, ERPNextClient, LLMRunner, has_child_join


CHILD_FILTER = [['Sales Invoice Item', 'sales_order', '=', 'SO-1']]


class TestExplicitJoinDetection(unittest.TestCase):
    def test_only_explicit_other_doctype_or_dotted_fields_enable_join_handling(self):
        for filters in (
            CHILD_FILTER,
            ['Sales Invoice Item', 'sales_order', '=', 'SO-1'],
            [['items.sales_order', '=', 'SO-1']],
            {'items.sales_order': 'SO-1'},
        ):
            with self.subTest(filters=filters):
                self.assertTrue(has_child_join('Sales Invoice', filters))
        for filters in (None, [], {}, [['Sales Invoice', 'docstatus', '=', 1]],
                        [['customer', '=', 'Customer.with.dot']]):
            with self.subTest(filters=filters):
                self.assertFalse(has_child_join('Sales Invoice', filters))


class TestDistinctParentAggregation(unittest.TestCase):
    def test_parent_sums_are_not_multiplied_by_matching_child_rows(self):
        client = ERPNextClient()
        rows = [{'name': 'INV-1', 'currency': 'USD', 'grand_total': '10.10'},
                {'name': 'INV-1', 'currency': 'USD', 'grand_total': '10.10'},
                {'name': 'INV-2', 'currency': 'USD', 'grand_total': '0.20'}]
        with patch.object(client, 'count', return_value=3), patch.object(client, 'list', return_value=rows):
            result = client.aggregate('Sales Invoice', CHILD_FILTER, ['currency'], ['grand_total'])
        self.assertEqual(result['count'], 2)
        self.assertEqual(result['matched_rows'], 3)
        self.assertEqual(result['duplicates_collapsed'], 1)
        self.assertTrue(result['complete'])
        self.assertEqual(result['groups'], [
            {'group': {'currency': 'USD'}, 'count': 2, 'sums': {'grand_total': '10.30'}}])

    def test_duplicates_cross_short_page_boundaries_using_raw_offsets(self):
        client = ERPNextClient()
        rows = [{'name': f'INV-{i//2:03}', 'grand_total': '0.1'} for i in range(205)]
        with patch.object(client, 'count', return_value=205), \
                patch.object(client, 'list', side_effect=lambda d, f, filters, limit, offset, order:
                             rows[offset:offset+min(limit, 17)]) as listing:
            result = client.aggregate('Sales Invoice', CHILD_FILTER, sum_fields=['grand_total'])
        self.assertEqual(result['count'], 103)
        self.assertEqual(result['matched_rows'], 205)
        self.assertEqual(result['duplicates_collapsed'], 102)
        self.assertEqual(result['groups'][0]['sums']['grand_total'], '10.3')
        self.assertEqual([call.args[4] for call in listing.call_args_list], list(range(0, 205, 17)))

    def test_plain_short_pages_still_cover_all_205_documents(self):
        client = ERPNextClient()
        rows = [{'name': f'INV-{i:03}', 'grand_total': '0.1'} for i in range(205)]
        with patch.object(client, 'count', return_value=205), \
                patch.object(client, 'list', side_effect=lambda d, f, filters, limit, offset, order:
                             rows[offset:offset+min(limit, 17)]):
            result = client.aggregate('Sales Invoice', sum_fields=['grand_total'])
        self.assertEqual(result['count'], 205)
        self.assertEqual(result['matched_rows'], 205)
        self.assertEqual(result['duplicates_collapsed'], 0)
        self.assertEqual(result['groups'][0]['sums']['grand_total'], '20.5')

    def test_conflicting_parent_projection_across_pages_is_rejected(self):
        client = ERPNextClient()
        for changed in ({'grand_total': '20.00'}, {'grand_total': 10.0}, {'currency': 'EUR'}):
            original = {'name': 'INV-1', 'grand_total': '10.00', 'currency': 'USD'}
            rows = [original, {**original, **changed}]
            with self.subTest(changed=changed), patch.object(client, 'count', return_value=2), \
                    patch.object(client, 'list', side_effect=lambda d, f, filters, limit, offset, order: rows[offset:offset+1]), \
                    self.assertRaisesRegex(ERPError, 'Conflicting projection'):
                client.aggregate('Sales Invoice', CHILD_FILTER, group_by=['currency'], sum_fields=['grand_total'])

    def test_unjoined_duplicate_parent_rows_still_fail(self):
        client = ERPNextClient()
        rows = [{'name': 'INV-1', 'grand_total': 10}, {'name': 'INV-1', 'grand_total': 10}]
        with patch.object(client, 'count', return_value=2), patch.object(client, 'list', return_value=rows), \
                self.assertRaisesRegex(ERPError, 'duplicate'):
            client.aggregate('Sales Invoice', sum_fields=['grand_total'])

    def test_raw_join_row_limit_applies_before_distinct_collapse(self):
        client = ERPNextClient()
        with patch.object(client, 'count', return_value=10001), patch.object(client, 'list') as listing, \
                self.assertRaisesRegex(ERPError, 'exceeds complete-scan limit'):
            client.aggregate('Sales Invoice', CHILD_FILTER)
        listing.assert_not_called()

    def test_early_end_or_changed_raw_count_fails_even_with_duplicate_parents(self):
        client = ERPNextClient()
        rows = [{'name': 'INV-1'}, {'name': 'INV-1'}]
        with patch.object(client, 'count', return_value=3), \
                patch.object(client, 'list', side_effect=[rows, []]), \
                self.assertRaisesRegex(ERPError, 'ended early'):
            client.aggregate('Sales Invoice', CHILD_FILTER)
        with patch.object(client, 'count', side_effect=[2, 3]), \
                patch.object(client, 'list', return_value=rows), \
                self.assertRaisesRegex(ERPError, 'count changed'):
            client.aggregate('Sales Invoice', CHILD_FILTER)


class TestJoinToolMetadata(unittest.TestCase):
    def test_count_documents_returns_distinct_parent_count_for_join_filters(self):
        client = ERPNextClient()
        runner = LLMRunner(Agent(client))
        rows = [{'name': 'INV-1'}, {'name': 'INV-1'}]
        with patch.object(client, 'count', return_value=2), patch.object(client, 'list', return_value=rows):
            self.assertEqual(runner._tool('count_documents', {'doctype': 'Sales Invoice', 'filters': CHILD_FILTER}), 1)
        with patch.object(client, 'count', return_value=25) as count, patch.object(client, 'aggregate') as aggregate:
            self.assertEqual(runner._tool('count_documents', {'doctype': 'Sales Invoice'}), 25)
        count.assert_called_once_with('Sales Invoice', None)
        aggregate.assert_not_called()

    def test_list_preserves_raw_rows_and_reports_join_count_basis(self):
        client = ERPNextClient()
        runner = LLMRunner(Agent(client))
        rows = [{'name': 'INV-1', 'qty': 1}, {'name': 'INV-1', 'qty': 2}]
        with patch.object(client, 'count', return_value=5), patch.object(client, 'list', return_value=rows):
            result = runner._tool('list_documents', {'doctype': 'Sales Invoice', 'filters': CHILD_FILTER,
                                                   'fields': ['qty'], 'offset': 1, 'limit': 2})
        self.assertIs(result['records'], rows)
        page = result['pagination']
        self.assertEqual((page['offset'], page['returned'], page['total'], page['next_offset']), (1, 2, 5, 3))
        self.assertEqual(page['total_basis'], 'raw_join_rows')
        self.assertEqual(page['unique_names_returned'], 1)
        self.assertEqual(page['duplicate_names'], ['INV-1'])
        self.assertTrue(any('not distinct documents' in warning for warning in result['warnings']))

    def test_plain_list_preserves_document_count_basis(self):
        client = ERPNextClient()
        with patch.object(client, 'count', return_value=2), \
                patch.object(client, 'list', return_value=[{'name': 'INV-1'}, {'name': 'INV-2'}]):
            result = LLMRunner(Agent(client))._tool('list_documents', {'doctype': 'Sales Invoice'})
        self.assertEqual(result['pagination']['total_basis'], 'documents')
        self.assertEqual(result['pagination']['unique_names_returned'], 2)
        self.assertEqual(result['pagination']['duplicate_names'], [])


if __name__ == '__main__':
    unittest.main()
