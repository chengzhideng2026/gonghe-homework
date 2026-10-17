"""Program contracts for local preview evidence; model prose is reviewed separately."""
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent import Agent, LLMRunner
from context_budget import _tool_summary
from execution_trace import ExecutionTraceWriter
from proposal_store import ProposalStore
from test_agent import FakeERP


class TestPreviewEvidenceBoundaries(unittest.TestCase):
    def test_real_ask_keeps_preview_state_out_of_erp_payload_and_in_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            erp = FakeERP()
            store = ProposalStore(Path(directory) / 'proposals.sqlite3')
            runner = LLMRunner(Agent(erp, store=store))
            runner.trace_writer = ExecutionTraceWriter(Path(directory) / 'traces')
            runner.key, runner.model = 'test-key', 'test-model'
            args = {'supplier': 'Tongling Magnet Wire Co.', 'item': 'RM-COIL-CU-2.0',
                    'qty': 2, 'uom': 'Meter', 'rate': 3, 'currency': 'USD'}
            replies = [
                {'role': 'assistant', 'content': None, 'tool_calls': [
                    {'id': 'preview', 'type': 'function', 'function': {
                        'name': 'prepare_purchase_order', 'arguments': json.dumps(args)}}]},
                {'role': 'assistant', 'content': 'Local preview only.'}]
            requests = []
            def model(request, timeout):
                requests.append(json.loads(request.data))
                return io.BytesIO(json.dumps({'choices': [{'message': replies.pop(0),
                                                            'finish_reason': 'stop'}]}).encode())
            with patch('agent.urlopen', side_effect=model):
                runner.ask('Prepare a preview only.', [])
            tool_message = next(message for message in requests[-1]['messages']
                                if message.get('tool_call_id') == 'preview')
            preview = json.loads(tool_message['content'])['data']
            persisted = store.get(preview['proposal_id'], runner.agent._target_binding())
            self.assertEqual(preview['local_state'], persisted['state'])
            self.assertEqual(persisted['state'], 'pending')
            self.assertIsNone(preview['erp_document'])
            self.assertNotIn('created_name', persisted)
            self.assertEqual(preview['doc']['docstatus'], 0)
            self.assertEqual(preview['doc'], persisted['doc'])
            self.assertNotIn('local_state', persisted['doc'])
            self.assertNotIn('erp_document', persisted['doc'])
            self.assertEqual(erp.created, [])
            summary = runner.receipts()[0]['summary']
            self.assertEqual(summary['local_state'], 'pending')
            self.assertIsNone(summary['erp_document'])
            historical = _tool_summary({'function': {'name': 'prepare_purchase_order',
                                                    'arguments': json.dumps(args)}}, tool_message)
            self.assertEqual(historical['data']['local_state'], 'pending')
            self.assertIsNone(historical['data']['erp_document'])
            self.assertEqual(historical['data']['doc']['docstatus'], 0)

    def test_actual_erp_status_receipt_uses_remote_identity_and_has_no_local_pending(self):
        class ExistingDraftERP(FakeERP):
            def get(self, doctype, name):
                self.reads.append((doctype, name))
                return {'doctype': doctype, 'name': name, 'docstatus': 0, 'status': 'Draft'}
        erp = ExistingDraftERP()
        runner = LLMRunner(Agent(erp))
        runner.key, runner.model = 'test-key', 'test-model'
        replies = [
            {'role': 'assistant', 'content': None, 'tool_calls': [
                {'id': 'read', 'type': 'function', 'function': {'name': 'get_document',
                 'arguments': '{"doctype":"Purchase Order","name":"EXISTING-PO"}'}}]},
            {'role': 'assistant', 'content': 'The returned document is a draft.'}]
        def model(request, timeout):
            return io.BytesIO(json.dumps({'choices': [{'message': replies.pop(0),
                                                        'finish_reason': 'stop'}]}).encode())
        with tempfile.TemporaryDirectory() as directory:
            runner.trace_writer = ExecutionTraceWriter(directory)
            with patch('agent.urlopen', side_effect=model):
                runner.ask('Read this existing order.', [])
        summary = runner.receipts()[0]['summary']
        self.assertEqual(summary['name'], 'EXISTING-PO')
        self.assertEqual(summary['docstatus'], 0)
        self.assertNotIn('local_state', summary)
        self.assertEqual(runner.agent.proposals, {})
        self.assertEqual(erp.created, [])
