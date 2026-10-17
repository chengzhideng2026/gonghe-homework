"""Fault injection around the remote commit and local durable read-back boundary."""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent import Agent, ERPError
from proposal_store import ProposalStore
from test_agent import FakeERP


class RecoverableERP(FakeERP):
    def __init__(self):
        super().__init__()
        self.read_failure = TimeoutError('connection lost during read-back')
        self.remote_changes = {}

    def get(self, doctype, name):
        self.reads.append((doctype, name))
        if self.read_failure:
            raise self.read_failure
        doc = copy.deepcopy(self.created[0][1])
        doc.update(name=name, status='Draft', grand_total=2900)
        doc.update(self.remote_changes)
        return doc


class TestReadOnlyReconciliation(unittest.TestCase):
    def preview(self, agent):
        return agent.proposal_po('Tongling Magnet Wire Co.', 'RM-COIL-CU-2.0',
                                 100, 'Meter', 29)['proposal_id']

    def interrupted(self, erp, path):
        agent = Agent(erp, ProposalStore(path))
        proposal_id = self.preview(agent)
        with self.assertRaisesRegex(ERPError, 'read-back failed'):
            agent.confirm(proposal_id)
        row = agent.store.get(proposal_id)
        self.assertEqual(row['state'], 'failed')
        self.assertEqual(row['created_name'], 'PUR-TEST-0001')
        return proposal_id

    def test_restart_reads_only_recorded_name_and_completes_without_second_create(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'journal.sqlite3'
            erp = RecoverableERP()
            proposal_id = self.interrupted(erp, path)
            erp.read_failure = None
            restarted = Agent(erp, ProposalStore(path))
            with patch.object(erp, 'create', side_effect=AssertionError('must never POST')):
                result = restarted.reconcile(proposal_id)
            self.assertTrue(result['reconciled'])
            self.assertFalse(result['review_required'])
            self.assertEqual(len(erp.created), 1)
            self.assertEqual(erp.reads[-1], ('Purchase Order', 'PUR-TEST-0001'))
            self.assertEqual(restarted.store.get(proposal_id)['state'], 'completed')
            with self.assertRaises(ERPError):
                restarted.confirm(proposal_id)
            with self.assertRaises(ERPError):
                restarted.reconcile(proposal_id)
            self.assertEqual(len(erp.reads), 2)

    def test_repeated_404_permissions_timeout_and_malformed_readback_remain_unresolved(self):
        for error in [ERPError('HTTP 404'), ERPError('HTTP 403'), TimeoutError('offline'), None]:
            with self.subTest(error=error), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'journal.sqlite3'
                erp = RecoverableERP()
                proposal_id = self.interrupted(erp, path)
                erp.read_failure = error
                restarted = Agent(erp, ProposalStore(path))
                if error is None:
                    read = patch.object(erp, 'get', return_value=[])
                else:
                    read = patch.object(erp, 'get', side_effect=error)
                with read, self.assertRaises(ERPError):
                    restarted.reconcile(proposal_id)
                row = restarted.store.get(proposal_id)
                self.assertEqual(row['state'], 'failed')
                self.assertEqual(row['created_name'], 'PUR-TEST-0001')
                with self.assertRaises(ERPError):
                    restarted.confirm(proposal_id)
                self.assertEqual(len(erp.created), 1)

    def test_unknown_remote_name_never_searches_or_creates(self):
        class LostACK(RecoverableERP):
            def create(self, doctype, doc):
                super().create(doctype, doc)
                raise TimeoutError('remote commit succeeded but ACK lost')
        with tempfile.TemporaryDirectory() as directory:
            erp = LostACK()
            path = Path(directory) / 'journal.sqlite3'
            agent = Agent(erp, ProposalStore(path))
            proposal_id = self.preview(agent)
            with self.assertRaises(ERPError):
                agent.confirm(proposal_id)
            restarted = Agent(erp, ProposalStore(path))
            with patch.object(erp, 'list') as listing, patch.object(erp, 'get') as getting, \
                    self.assertRaisesRegex(ERPError, 'name is unknown'):
                restarted.reconcile(proposal_id)
            listing.assert_not_called()
            getting.assert_not_called()
            self.assertEqual(len(erp.created), 1)

    def test_crash_after_persisting_name_can_reconcile_even_if_preview_expired(self):
        with tempfile.TemporaryDirectory() as directory:
            erp = RecoverableERP()
            path = Path(directory) / 'journal.sqlite3'
            agent = Agent(erp, ProposalStore(path))
            proposal_id = self.preview(agent)
            agent.store.claim(proposal_id, 900)
            erp.create('Purchase Order', agent.proposals[proposal_id]['doc'])
            agent.store.finish(proposal_id, 'creating', created_name='PUR-TEST-0001',
                               created_at=0)
            erp.read_failure = None
            result = Agent(erp, ProposalStore(path)).reconcile(proposal_id)
            self.assertFalse(result['review_required'])
            self.assertEqual(len(erp.created), 1)

    def test_external_drift_is_returned_for_review_without_altering_remote_document(self):
        changes = [({'name': 'OTHER'}, 'name'), ({'doctype': 'Sales Invoice'}, 'doctype'),
                   ({'docstatus': 1}, 'docstatus (expected an unsubmitted draft)'),
                   ({'docstatus': 2}, 'docstatus (expected an unsubmitted draft)'),
                   ({'currency': 'EUR'}, 'currency'), ({'supplier': 'OTHER'}, 'supplier'),
                   ({'grand_total': 3000}, 'grand_total (taxes/defaults may affect the estimated total)'),
                   ({'items': []}, 'items')]
        for change, field in changes:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                erp = RecoverableERP()
                path = Path(directory) / 'journal.sqlite3'
                proposal_id = self.interrupted(erp, path)
                erp.read_failure = None
                erp.remote_changes = change
                result = Agent(erp, ProposalStore(path)).reconcile(proposal_id)
                self.assertTrue(result['review_required'])
                self.assertIn(field, result['differences_from_preview'])
                self.assertEqual(len(erp.created), 1)

    def test_pending_cannot_be_reconciled_and_remains_confirmable(self):
        erp = RecoverableERP()
        agent = Agent(erp)
        proposal_id = self.preview(agent)
        with self.assertRaisesRegex(ERPError, 'unresolved create'):
            agent.reconcile(proposal_id)
        self.assertEqual(agent.proposals[proposal_id]['state'], 'pending')
        self.assertEqual(erp.created, [])
        self.assertEqual(erp.reads, [])

    def test_other_finisher_wins_during_readback_and_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            erp = RecoverableERP()
            path = Path(directory) / 'journal.sqlite3'
            proposal_id = self.interrupted(erp, path)
            erp.read_failure = None
            restarted = Agent(erp, ProposalStore(path))
            original_get = erp.get

            def competing_get(doctype, name):
                result = original_get(doctype, name)
                ProposalStore(path).finish(proposal_id, 'completed', result={'winner': True})
                return result

            with patch.object(erp, 'get', side_effect=competing_get), self.assertRaises(ValueError):
                restarted.reconcile(proposal_id)
            self.assertEqual(restarted.store.get(proposal_id)['result'], {'winner': True})
            self.assertEqual(len(erp.created), 1)

    def test_read_error_cannot_revert_a_concurrent_completed_result_to_failed(self):
        with tempfile.TemporaryDirectory() as directory:
            erp = RecoverableERP()
            path = Path(directory) / 'journal.sqlite3'
            proposal_id = self.interrupted(erp, path)
            restarted = Agent(erp, ProposalStore(path))

            def competing_failure(*args):
                ProposalStore(path).finish(proposal_id, 'completed', result={'winner': True})
                raise TimeoutError('late failure')

            with patch.object(erp, 'get', side_effect=competing_failure), self.assertRaises(ValueError):
                restarted.reconcile(proposal_id)
            row = restarted.store.get(proposal_id)
            self.assertEqual(row['state'], 'completed')
            self.assertEqual(row['result'], {'winner': True})
            self.assertEqual(len(erp.created), 1)
