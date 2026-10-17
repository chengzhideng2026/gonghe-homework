import json
import io
import sqlite3
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from agent import Agent
from proposal_store import ProposalStore
from test_review_target import BoundERP
import agent as app


SCOPE_A = {'endpoint': 'https://a.example.invalid', 'identity_fingerprint': 'identity-a'}
SCOPE_B = {'endpoint': 'https://b.example.invalid', 'identity_fingerprint': 'identity-b'}


def proposal(scope=None, state='pending', **extra):
    body = {'state': state, 'created_at': time.time(), 'doc': {'supplier': 'Test supplier'}}
    if scope is not None:
        body['target_binding'] = dict(scope)
    body.update(extra)
    return body


class TestProposalConnectionScope(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'journal.sqlite3'
        self.store = ProposalStore(self.path)

    def test_scoped_active_and_get_hide_foreign_and_unbound_records(self):
        for key, body in [
            ('own', proposal(SCOPE_A)), ('foreign', proposal(SCOPE_B)), ('legacy', proposal()),
            ('own-completed', proposal(SCOPE_A, 'completed')),
            ('own-discarded', proposal(SCOPE_A, 'discarded')),
        ]:
            self.store.put(key, body)
        self.assertEqual(set(self.store.active(SCOPE_A)), {'own', 'own-discarded'})
        for key in ('foreign', 'legacy', 'missing'):
            with self.subTest(key=key):
                self.assertIsNone(self.store.get(key, SCOPE_A))
        self.assertEqual(self.store.get('own-completed', SCOPE_A)['state'], 'completed')

    def test_credentials_change_at_same_endpoint_also_changes_visibility(self):
        rotated = {**SCOPE_A, 'identity_fingerprint': 'rotated-identity'}
        self.store.put('own', proposal(SCOPE_A))
        self.assertEqual(self.store.active(rotated), {})
        self.assertIsNone(self.store.get('own', rotated))

    def test_foreign_legacy_and_missing_ids_have_identical_mutation_errors(self):
        foreign = proposal(SCOPE_B, 'creating', created_name='OTHER-PO-1')
        legacy = proposal()
        self.store.put('foreign', foreign)
        self.store.put('legacy', legacy)
        operations = [
            lambda key: self.store.claim(key, 900, target_binding=SCOPE_A),
            lambda key: self.store.discard(key, target_binding=SCOPE_A),
            lambda key: self.store.finish(key, 'completed', target_binding=SCOPE_A),
        ]
        for operation in operations:
            for key in ('foreign', 'legacy', 'missing'):
                with self.subTest(operation=operation, key=key), \
                        self.assertRaisesRegex(ValueError, '^Unknown proposal id$'):
                    operation(key)
        self.assertEqual(self.store.get('foreign'), foreign)
        self.assertEqual(self.store.get('legacy'), legacy)

    def test_each_mutation_checks_current_persisted_scope_after_stale_read(self):
        operations = [
            lambda key: self.store.claim(key, 900, target_binding=SCOPE_A),
            lambda key: self.store.discard(key, target_binding=SCOPE_A),
            lambda key: self.store.finish(key, 'completed', target_binding=SCOPE_A),
        ]
        for index, operation in enumerate(operations):
            key = f'proposal-{index}'
            self.store.put(key, proposal(SCOPE_A))
            self.assertIsNotNone(self.store.get(key, SCOPE_A))
            current = proposal(SCOPE_B)
            with closing(sqlite3.connect(self.path)) as db:
                with db:
                    db.execute('UPDATE proposals SET body=? WHERE id=?', (json.dumps(current), key))
            with self.subTest(operation=index), self.assertRaisesRegex(ValueError, '^Unknown proposal id$'):
                operation(key)
            self.assertEqual(self.store.get(key), current)

    def test_authorized_claim_and_discard_keep_their_original_semantics(self):
        self.store.put('claim', proposal(SCOPE_A))
        self.store.put('discard', proposal(SCOPE_A))
        self.assertEqual(self.store.claim('claim', 900, SCOPE_A)['state'], 'creating')
        self.store.discard('discard', SCOPE_A)
        self.assertEqual(self.store.get('discard', SCOPE_A)['state'], 'discarded')
        with self.assertRaises(ValueError):
            self.store.claim('discard', 900, SCOPE_A)

    def test_finish_compares_expected_state_and_created_name_without_partial_update(self):
        self.store.put('own', proposal(SCOPE_A, 'creating', created_name='PO-1'))
        for states, expected_name in ((('failed',), 'PO-1'), (('creating',), 'PO-other')):
            with self.subTest(states=states, expected_name=expected_name), \
                    self.assertRaisesRegex(ValueError, 'changed while'):
                self.store.finish('own', 'completed', target_binding=SCOPE_A,
                                  expected_states=states, expected_created_name=expected_name,
                                  result={'should_not_be_saved': True})
            self.assertNotIn('result', self.store.get('own', SCOPE_A))
        self.store.finish('own', 'completed', target_binding=SCOPE_A,
                          expected_states=('creating', 'failed'), expected_created_name='PO-1',
                          result={'verified': True})
        self.assertEqual(self.store.get('own', SCOPE_A)['result'], {'verified': True})

    def test_two_compare_and_set_completions_have_one_winner(self):
        self.store.put('own', proposal(SCOPE_A, 'failed', created_name='PO-1'))
        def complete(index):
            try:
                ProposalStore(self.path).finish(
                    'own', 'completed', target_binding=SCOPE_A,
                    expected_states=('creating', 'failed'), expected_created_name='PO-1',
                    result={'winner': index})
                return True
            except ValueError:
                return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(complete, range(2)))
        self.assertCountEqual(outcomes, [True, False])
        self.assertEqual(self.store.get('own', SCOPE_A)['state'], 'completed')

    def test_expected_missing_name_is_distinct_from_omitting_name_check(self):
        self.store.put('own', proposal(SCOPE_A, 'creating'))
        self.store.finish('own', 'creating', target_binding=SCOPE_A,
                          expected_states='creating', expected_created_name=None, created_name='PO-1')
        with self.assertRaisesRegex(ValueError, 'changed while'):
            self.store.finish('own', 'completed', target_binding=SCOPE_A, expected_created_name=None)
        self.store.finish('own', 'completed', target_binding=SCOPE_A)

    def test_unscoped_trusted_maintenance_calls_remain_compatible(self):
        self.store.put('legacy', proposal())
        self.store.put('foreign', proposal(SCOPE_B))
        self.assertEqual(set(self.store.active()), {'legacy', 'foreign'})
        self.assertEqual(self.store.claim('legacy', 900)['state'], 'creating')
        self.store.finish('legacy', 'failed', created_name='PO-legacy')
        self.assertEqual(self.store.get('legacy')['created_name'], 'PO-legacy')
        self.store.discard('foreign')
        self.assertEqual(self.store.get('foreign')['state'], 'discarded')


class TestAgentConnectionScope(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.store = ProposalStore(Path(self.directory.name) / 'journal.sqlite3')

    def make_agent(self, base='https://a.example.invalid', authorization='token example-a:secret-a'):
        return Agent(BoundERP(base, authorization), self.store)

    def preview(self, agent):
        return agent.proposal_po('Tongling Magnet Wire Co.', 'RM-COIL-CU-2.0', 100, 'Meter', 29)['proposal_id']

    def assert_hidden_operations_match_unknown(self, agent, proposal_id):
        for operation in (agent.confirm, agent.discard, agent.reconcile):
            with self.subTest(operation=operation.__name__):
                with self.assertRaises(ValueError) as foreign:
                    operation(proposal_id)
                with self.assertRaises(ValueError) as unknown:
                    operation('unknown-proposal')
                self.assertEqual(str(foreign.exception), str(unknown.exception))

    def test_restarted_endpoint_or_credentials_hide_foreign_proposals_and_operations(self):
        original = self.make_agent()
        proposal_id = self.preview(original)
        for base, authorization in (
            ('https://b.example.invalid', 'token example-a:secret-a'),
            ('https://a.example.invalid', 'token example-b:secret-b'),
        ):
            with self.subTest(base=base):
                switched = self.make_agent(base, authorization)
                self.assertNotIn(proposal_id, switched.proposals)
                own_id = self.preview(switched)
                self.assertEqual(set(switched.active_proposals()), {own_id})
                self.assert_hidden_operations_match_unknown(switched, proposal_id)
                self.assertEqual(switched.c.created, [])
                self.assertEqual(switched.c.reads, [])
        self.assertEqual(self.store.get(proposal_id)['state'], 'pending')

    def test_in_process_endpoint_or_credentials_change_refreshes_active_scope(self):
        for field in ('endpoint', 'credentials'):
            with self.subTest(field=field):
                original = self.make_agent()
                proposal_id = self.preview(original)
                if field == 'endpoint':
                    original.c.base = 'https://b.example.invalid'
                else:
                    original.c.headers['Authorization'] = 'token rotated:secret'
                self.assertNotIn(proposal_id, original.active_proposals())
                self.assert_hidden_operations_match_unknown(original, proposal_id)
                original.c.base = 'https://a.example.invalid'
                original.c.headers['Authorization'] = 'token example-a:secret-a'
                self.assertIn(proposal_id, original.active_proposals())
                self.assertEqual(self.store.get(proposal_id)['state'], 'pending')

    def test_legacy_unbound_record_has_no_current_application_scope(self):
        self.store.put('legacy', proposal())
        agent = self.make_agent()
        self.assertNotIn('legacy', agent.proposals)
        self.assertNotIn('legacy', agent.active_proposals())
        self.assert_hidden_operations_match_unknown(agent, 'legacy')
        self.assertEqual(self.store.get('legacy')['state'], 'pending')

    def test_pending_cli_prints_only_current_connection_previews(self):
        original = self.make_agent()
        foreign_id = self.preview(original)
        current = self.make_agent('https://b.example.invalid')
        own_id = self.preview(current)
        output = io.StringIO()
        with patch.object(app, 'configure_console'), \
                patch.object(app, 'ERPNextClient', return_value=current.c), \
                patch.object(app, 'ProposalStore', return_value=self.store), \
                patch.object(app.LLMRunner, 'available', return_value=True), \
                patch.object(app.LLMRunner, 'ask', side_effect=AssertionError('No model should be called')), \
                patch('sys.argv', ['agent.py']), \
                patch('builtins.input', side_effect=['/pending', '/quit']), redirect_stdout(output):
            app.main()
        self.assertIn(own_id, output.getvalue())
        self.assertNotIn(foreign_id, output.getvalue())

    def test_foreign_unresolved_name_is_not_disclosed_or_reconciled(self):
        original = self.make_agent()
        for state in ('creating', 'failed'):
            with self.subTest(state=state):
                proposal_id = self.preview(original)
                self.store.finish(proposal_id, state, created_name='FOREIGN-PO-1')
                switched = self.make_agent('https://b.example.invalid')
                self.assertNotIn(proposal_id, switched.active_proposals())
                self.assert_hidden_operations_match_unknown(switched, proposal_id)
                self.assertEqual(switched.c.reads, [])
                self.assertEqual(self.store.get(proposal_id)['created_name'], 'FOREIGN-PO-1')


if __name__ == '__main__':
    unittest.main()
