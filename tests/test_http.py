"""Exercise actual urllib serialization, rather than a fake ERP client."""
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from agent import ERPNextClient, Agent, ERPError
from test_agent import FakeERP


class TestHTTPTransport(unittest.TestCase):
    def test_resource_paths_are_encoded_without_changing_document_identity(self):
        paths = []
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                paths.append(self.path)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({'data': {'name': 'A/B #1'}}).encode())
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            client = ERPNextClient(base=f'http://127.0.0.1:{server.server_port}')
            result = client.get('Purchase Order', 'A/B #1')
            self.assertEqual(result['name'], 'A/B #1')
            self.assertEqual(paths, ['/api/resource/Purchase%20Order/A%2FB%20%231'])
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


class TestWriteRecovery(unittest.TestCase):
    def test_successful_create_with_failed_readback_keeps_name_and_blocks_recreate(self):
        class ReadFailure(FakeERP):
            def get(self, *args):
                raise TimeoutError('read failed')
        erp = ReadFailure()
        agent = Agent(erp)
        preview = agent.proposal_po('Tongling Magnet Wire Co.', 'RM-COIL-CU-2.0', 100, 'Meter', 29)
        with self.assertRaisesRegex(ERPError, 'PUR-TEST-0001 was created'):
            agent.confirm(preview['proposal_id'])
        with self.assertRaises(ERPError):
            agent.confirm(preview['proposal_id'])
        self.assertEqual(len(erp.created), 1)

    def test_nonfinite_amounts_are_rejected_before_any_erp_call(self):
        agent = Agent(FakeERP())
        for qty, rate in [(float('nan'), 29), (100, float('inf'))]:
            with self.subTest(qty=qty, rate=rate), self.assertRaises(ValueError):
                agent.proposal_po('Tongling Magnet Wire Co.', 'RM-COIL-CU-2.0', qty, 'Meter', rate)
