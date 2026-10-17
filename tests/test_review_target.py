import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from agent import Agent, ERPError
from proposal_store import ProposalStore
from test_agent import FakeERP


class BoundERP(FakeERP):
    def __init__(self, base, authorization='token demo:demo-secret'):
        super().__init__()
        self.base = base
        self.headers = {'Authorization': authorization}


class TestTargetBinding(unittest.TestCase):
    def preview(self, agent):
        return agent.proposal_po('Tongling Magnet Wire Co.', 'RM-COIL-CU-2.0', 100, 'Meter', 29)['proposal_id']

    def test_restart_with_different_target_or_credentials_cannot_write(self):
        for new in [BoundERP('https://production.example.invalid'),
                    BoundERP('https://test.example.invalid', 'token other:other-secret')]:
            with self.subTest(base=new.base), tempfile.TemporaryDirectory() as directory:
                store = Path(directory) / 'journal.sqlite3'
                original = BoundERP('https://test.example.invalid')
                proposal_id = self.preview(Agent(original, ProposalStore(store)))
                with self.assertRaisesRegex(ValueError, 'target or credential'):
                    Agent(new, ProposalStore(store)).confirm(proposal_id)
                self.assertEqual(new.created, [])
                self.assertEqual(original.created, [])

    def test_equivalent_endpoint_format_and_complete_readback(self):
        class ExactERP(BoundERP):
            def get(self, doctype, name):
                doc = dict(self.created[-1][1])
                doc.update(name=name, status='Draft', grand_total=2900)
                return doc
        erp = ExactERP('https://TEST.example.invalid:443/')
        agent = Agent(erp)
        proposal_id = self.preview(agent)
        erp.base = 'https://test.example.invalid'
        result = agent.confirm(proposal_id)
        self.assertFalse(result['review_required'])
        self.assertEqual(result['differences_from_preview'], [])

    def test_old_pending_preview_without_binding_is_rejected(self):
        erp = BoundERP('https://test.example.invalid')
        agent = Agent(erp)
        proposal_id = self.preview(agent)
        del agent.proposals[proposal_id]['target_binding']
        with self.assertRaises(ValueError):
            agent.confirm(proposal_id)
        self.assertEqual(erp.created, [])

    def test_same_target_and_credentials_restart_with_complete_readback(self):
        class ExactERP(BoundERP):
            def get(self, doctype, name):
                doc = dict(self.created[-1][1])
                doc.update(name=name, status='Draft', grand_total=2900)
                return doc
        with tempfile.TemporaryDirectory() as directory:
            store = Path(directory) / 'journal.sqlite3'
            original = ExactERP('https://test.example.invalid')
            proposal_id = self.preview(Agent(original, ProposalStore(store)))
            restarted = ExactERP('https://test.example.invalid')
            result = Agent(restarted, ProposalStore(store)).confirm(proposal_id)
            self.assertFalse(result['review_required'])
            self.assertEqual(result['differences_from_preview'], [])
            self.assertEqual(len(restarted.created), 1)
            self.assertEqual(original.created, [])
            self.assertEqual(ProposalStore(store).get(proposal_id)['state'], 'completed')

    def test_invalid_target_urls_are_rejected_before_erp_access(self):
        urls = [
            'https://demo:secret@test.example.invalid',
            'https://demo@test.example.invalid',
            'https://test.example.invalid?site=other',
            'https://test.example.invalid#fragment',
            'file:///tmp/erp',
            'https://',
        ]
        for base in urls:
            erp = BoundERP(base)
            with self.subTest(base=base), patch.object(erp, 'list') as listing, \
                    self.assertRaisesRegex(ERPError, 'HTTP'):
                self.preview(Agent(erp))
            listing.assert_not_called()
            self.assertEqual(erp.created, [])

    def test_explicit_zero_port_is_not_the_default_endpoint(self):
        erp = BoundERP('http://test.example.invalid:0')
        agent = Agent(erp)
        proposal_id = self.preview(agent)
        self.assertEqual(agent.proposals[proposal_id]['target_binding']['endpoint'],
                         'http://test.example.invalid:0')
        erp.base = 'http://test.example.invalid'
        with self.assertRaisesRegex(ValueError, 'target or credential'):
            agent.confirm(proposal_id)
        self.assertEqual(erp.created, [])
