"""Regression tests for repeated-parent child-table snapshot consistency."""
import copy
import unittest
from detail_statistics import summarize_details


def row(name, qty='2', price='10', code='ITEM'):
    return {'name': name, 'qty': qty, 'rate': price,
            'amount': str(int(qty) * int(price)), 'uom': 'Nos', 'code': code}


def evidence(tag, rows, parent='P1'):
    return {'tool': 'get_document', 'version': '1', 'call_id': tag,
            'arguments': {'doctype': 'Doc', 'name': parent},
            'data': {'doctype': 'Doc', 'name': parent, 'currency': 'USD',
                     'company': 'CO', 'docstatus': 1,
                     'lines': copy.deepcopy(rows)}, 'io': {}}


class SnapshotFixTests(unittest.TestCase):
    def stats(self, a, b, **kwargs):
        return summarize_details({'a': a, 'b': b}, ['a', 'b'], 'lines', **kwargs)

    def test_same_parent_disjoint_rows_cannot_be_union_complete(self):
        with self.assertRaisesRegex(ValueError, 'Conflicting child-table snapshots'):
            self.stats(evidence('1', [row('A')]), evidence('2', [row('B')]))

    def test_same_parent_row_removed_or_added(self):
        with self.assertRaisesRegex(ValueError, 'Conflicting child-table snapshots'):
            self.stats(evidence('1', [row('A'), row('B')]), evidence('2', [row('A')]))

    def test_same_parent_rate_changed(self):
        with self.assertRaisesRegex(ValueError, 'Conflicting child-table snapshots'):
            self.stats(evidence('1', [row('A')]), evidence('2', [row('A', price='11')]))

    def test_same_parent_unmatched_child_changed(self):
        with self.assertRaisesRegex(ValueError, 'Conflicting child-table snapshots'):
            self.stats(evidence('1', [row('A'), row('B', code='EXTRA')]),
                       evidence('2', [row('A')]), row_equals={'code': 'ITEM'})

    def test_same_parent_reordered_rows_allowed(self):
        lines = [row('A'), row('B')]
        s = self.stats(evidence('1', lines), evidence('2', list(reversed(lines))))
        self.assertTrue(s['complete'])
        self.assertEqual(s['line_count'], 2)
        self.assertEqual(s['duplicates_collapsed'], 2)

    def test_same_parent_repeated_identical_reads_allowed(self):
        s = self.stats(evidence('1', [row('A')]), evidence('2', [row('A')]))
        self.assertTrue(s['complete'])
        self.assertEqual(s['line_count'], 1)
        self.assertEqual(s['duplicates_collapsed'], 1)

    def test_different_parent_same_child_name_kept(self):
        s = self.stats(evidence('1', [row('A')]), evidence('2', [row('A')], parent='P2'))
        self.assertEqual(s['line_count'], 2)
        self.assertEqual(s['distinct_parent_count'], 2)

    def test_duplicate_child_name_in_single_document_fails(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate child row identity'):
            summarize_details({'a': evidence('1', [row('A'), row('A')])}, ['a'], 'lines')

    def test_empty_group_has_zero_matching_parents_but_referenced_scope(self):
        s = summarize_details({'a': evidence('1', [])}, ['a'], 'lines')
        self.assertTrue(s['complete'])
        self.assertEqual(s['line_count'], 0)
        self.assertEqual(s['distinct_parent_count'], 0)
        self.assertEqual(len(s['query_scope']['parent_names']), 1)


if __name__ == '__main__':
    unittest.main()
