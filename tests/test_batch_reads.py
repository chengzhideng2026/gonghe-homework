"""Bounded parent reads: completeness, failure identity, and evidence integration."""
import json
import unittest
from unittest.mock import call, patch

from agent import Agent, ERPError, ERPNextClient, LLMRunner, TOOL_DEFS
from answer_checks import evidence_issues
from tool_receipts import tool_receipts


def messages(tool, arguments, data, call_id='batch'):
    return [
        {'role': 'assistant', 'tool_calls': [
            {'id': call_id, 'type': 'function', 'function': {
                'name': tool, 'arguments': json.dumps(arguments)}}]},
        {'role': 'tool', 'tool_call_id': call_id,
         'content': json.dumps({'ok': True, 'data': data})},
    ]


class TestBoundedParentReads(unittest.TestCase):
    def client(self):
        return ERPNextClient(base='https://example.invalid', key='test', secret='test')

    def test_reads_unseen_parent_type_with_children_and_never_creates(self):
        client = self.client()
        documents = [{'doctype': 'Unseen Parent', 'name': name,
                      'lines': [{'sku': 'part', 'qty': 2}]}
                     for name in ('B', 'A')]
        with patch.object(client, 'get', side_effect=documents) as get, \
                patch.object(client, 'create') as create:
            result = client.get_many('Unseen Parent', ['B', 'A'])
        self.assertEqual(get.call_args_list, [call('Unseen Parent', 'B'), call('Unseen Parent', 'A')])
        self.assertTrue(result['complete'])
        self.assertEqual((result['success_count'], result['error_count']), (2, 0))
        self.assertEqual([row['data'] for row in result['results']], documents)
        self.assertIn('not a transactional snapshot', result['consistency'])
        create.assert_not_called()

    def test_duplicate_names_preserve_first_occurrence_and_read_once(self):
        client = self.client()
        with patch.object(client, 'get', side_effect=lambda d, n: {'name': n}) as get:
            result = client.get_many('Parent', ['B', 'A', 'B', 'A'])
        self.assertEqual(result['requested_names'], ['B', 'A'])
        self.assertEqual((result['input_count'], result['requested_count']), (4, 2))
        self.assertEqual(get.call_args_list, [call('Parent', 'B'), call('Parent', 'A')])

    def test_invalid_names_rejected_before_any_read(self):
        client = self.client()
        invalid = [None, 'A', {}, ('A',), [], [''], [' '], [None], [False], [1],
                   ['valid', None], ['A'] * 21]
        for names in invalid:
            with self.subTest(names=names), patch.object(client, 'get') as get, \
                    self.assertRaises(ValueError):
                client.get_many('Parent', names)
            get.assert_not_called()

    def test_invalid_doctype_rejected_before_any_read(self):
        client = self.client()
        for doctype in (None, '', ' ', False, [], 1):
            with self.subTest(doctype=doctype), patch.object(client, 'get') as get, \
                    self.assertRaises(ValueError):
                client.get_many(doctype, ['A'])
            get.assert_not_called()

    def test_twenty_inputs_are_allowed(self):
        client = self.client()
        names = [f'P-{i}' for i in range(20)]
        with patch.object(client, 'get', side_effect=lambda d, n: {'name': n}) as get:
            result = client.get_many('Parent', names)
        self.assertEqual(get.call_count, 20)
        self.assertEqual(result['requested_names'], names)
        self.assertTrue(result['complete'])

    def test_partial_404_is_explicit_and_later_reads_continue_without_retry(self):
        client = self.client()
        with patch.object(client, 'get', side_effect=[{'name': 'A'}, ERPError('HTTP 404'), {'name': 'C'}]) as get:
            result = client.get_many('Parent', ['A', 'missing', 'C'])
        self.assertFalse(result['complete'])
        self.assertEqual((result['success_count'], result['error_count']), (2, 1))
        self.assertEqual(result['results'][1], {'name': 'missing', 'ok': False, 'error': 'HTTP 404'})
        self.assertEqual(result['results'][2]['data']['name'], 'C')
        self.assertEqual(get.call_count, 3)

    def test_malformed_or_mismatched_readback_is_not_returned_as_success(self):
        client = self.client()
        for data in (None, [], 'A', {}, {'name': 'other'}, {'name': 'A', 'doctype': 'Other'}):
            with self.subTest(data=data), patch.object(client, 'get', return_value=data) as get:
                result = client.get_many('Parent', ['A'])
            self.assertFalse(result['complete'])
            self.assertEqual(result['success_count'], 0)
            self.assertEqual(result['error_count'], 1)
            self.assertFalse(result['results'][0]['ok'])
            self.assertIn('Invalid document read-back', result['results'][0]['error'])
            self.assertNotIn('data', result['results'][0])
            get.assert_called_once()

    def test_dispatch_uses_read_client_and_schema_exposes_bound(self):
        client = self.client()
        runner = LLMRunner(Agent(client))
        with patch.object(client, 'get_many', return_value={'complete': True}) as get_many, \
                patch.object(client, 'create') as create:
            result = runner._tool('get_documents', {'doctype': 'Parent', 'names': ['A']})
        self.assertTrue(result['complete'])
        get_many.assert_called_once_with('Parent', ['A'])
        create.assert_not_called()
        tool = next(tool['function'] for tool in TOOL_DEFS if tool['function']['name'] == 'get_documents')
        self.assertEqual(tool['parameters']['properties']['names']['maxItems'], 20)
        self.assertIn('partial', tool['description'])


class TestBatchReadEvidence(unittest.TestCase):
    def batch(self, doctype, entries):
        client = ERPNextClient(base='https://example.invalid', key='test', secret='test')
        with patch.object(client, 'get', side_effect=entries):
            data = client.get_many(doctype, ['A', 'B'][:len(entries)])
        return messages('get_documents', {'doctype': doctype, 'names': data['requested_names']},
                        data, call_id=doctype)

    def test_receipt_keeps_partial_status_and_successful_identities_only(self):
        trace = self.batch('Parent', [{'name': 'A', 'lines': [{'secret_detail': 'not in summary'}]}, ERPError('404')])
        receipt = tool_receipts(trace)[0]
        self.assertEqual(receipt['status'], 'ok')
        self.assertFalse(receipt['summary']['complete'])
        self.assertEqual(receipt['summary']['record_names'], ['A'])
        self.assertEqual(receipt['summary']['failures'], [{'name': 'B', 'error': '404'}])
        self.assertNotIn('secret_detail', json.dumps(receipt))

    def test_nonempty_batch_event_read_allows_normal_review_not_relevance_proof(self):
        bins = self.batch('Bin', [{'name': 'A'}])
        events = self.batch('Stock Entry', [{'name': 'A'}, ERPError('404')])
        self.assertEqual(evidence_issues('材料已经转入 WIP。', bins + events), [])

    def test_failed_batch_events_do_not_remove_snapshot_check(self):
        bins = self.batch('Bin', [{'name': 'A'}])
        for doctype in ('Stock Entry', 'Stock Ledger Entry'):
            with self.subTest(doctype=doctype):
                events = self.batch(doctype, [ERPError('404')])
                self.assertTrue(evidence_issues('材料已经转入 WIP。', bins + events))

    def test_bin_batch_without_events_still_triggers_known_claim_check(self):
        bins = self.batch('Bin', [{'name': 'A'}])
        self.assertTrue(evidence_issues('材料已经转入 WIP。', bins))


if __name__ == '__main__':
    unittest.main()
