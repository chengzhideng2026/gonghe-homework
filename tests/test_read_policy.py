"""Request-level accounting, freshness boundaries and bounded retrieval tests."""
import copy
import io
import json
import unittest
from unittest.mock import Mock, patch
from urllib.parse import unquote

from agent import Agent, ERPError, ERPNextClient, LLMRunner
from read_policy import ReadPolicy, RequestLimitError
from test_agent import FakeERP


class Clock:
    def __init__(self):
        self.now = 0
        self.waits = []

    def __call__(self):
        return self.now

    def sleep(self, delay):
        self.waits.append(delay)
        self.now += delay


class TestReadPolicy(unittest.TestCase):
    def policy(self, **kwargs):
        self.clock = Clock()
        return ReadPolicy(ttl=30, metadata_ttl=600, max_requests=40,
                          per_minute=120, interval=0, clock=self.clock, sleep=self.clock.sleep, **kwargs)

    def request(self, policy, send, params=None, scope='tenant-A', path='/api/resource/Item', method='GET'):
        return policy.request(method, path, params, scope, send)

    def test_exact_reuse_across_turns_has_age_and_defensive_copies(self):
        p = self.policy()
        send = Mock(return_value=[{'name': 'A'}])
        with p.turn():
            first = self.request(p, send)
            first[0]['name'] = 'mutated'
        self.clock.now = 5
        with p.turn():
            second = self.request(p, send)
            self.assertEqual(second, [{'name': 'A'}])
            self.assertEqual(p.report()['http_attempts'], 0)
            self.assertEqual(p.report()['cache_hits'], 1)
            source = p.report()['sources'][0]
            self.assertEqual(source['age_seconds'], 5)
            self.assertTrue(source['fetched_at'])
        send.assert_called_once()

    def test_business_and_metadata_ttls_expire_independently(self):
        p = self.policy()
        send = Mock(return_value=18)
        meta = '/api/method/frappe.desk.form.load.getdoctype'
        with p.turn():
            self.request(p, send)
            self.request(p, send, path=meta)
        self.clock.now = 31
        with p.turn():
            self.request(p, send)
            self.request(p, send, path=meta)
            self.assertEqual((p.report()['http_attempts'], p.report()['cache_hits']), (1, 1))
        self.clock.now = 601
        with p.turn():
            self.request(p, send, path=meta)
            self.assertEqual(p.report()['http_attempts'], 1)

    def test_filter_field_offset_and_scope_changes_never_reuse_partial_pages(self):
        p = self.policy()
        send = Mock(return_value=[{'name': 'A'}])
        with p.turn():
            for params, scope in [({'filters': 'A', 'fields': 'name', 'offset': 0}, 'A'),
                                  ({'filters': 'B', 'fields': 'name', 'offset': 0}, 'A'),
                                  ({'filters': 'A', 'fields': 'name,amount', 'offset': 0}, 'A'),
                                  ({'filters': 'A', 'fields': 'name', 'offset': 1}, 'A'),
                                  ({'filters': 'A', 'fields': 'name', 'offset': 0}, 'B')]:
                self.request(p, send, params, scope)
            self.assertEqual(p.report()['http_attempts'], 5)
            self.assertEqual(p.report()['cache_hits'], 0)

    def test_no_cache_outside_turn_and_zero_ttl_can_disable_business_reuse(self):
        p = self.policy()
        send = Mock(return_value=18)
        self.request(p, send)
        self.request(p, send)
        p.ttl = 0
        with p.turn():
            self.request(p, send)
            self.request(p, send)
            self.assertEqual(p.report()['http_attempts'], 2)
        self.assertEqual(send.call_count, 4)

    def test_errors_are_not_cached_and_failed_attempts_consume_budget(self):
        p = self.policy()
        p.max_requests = 1
        send = Mock(side_effect=TimeoutError('lost response'))
        with p.turn():
            with self.assertRaises(TimeoutError):
                self.request(p, send)
            with self.assertRaises(RequestLimitError):
                self.request(p, send)
            self.assertEqual(p.report()['http_attempts'], 1)
            self.assertEqual(p.report()['rejected_requests'], 1)
        with p.turn():
            with self.assertRaises(TimeoutError):
                self.request(p, send)
        self.assertEqual(send.call_count, 2)

    def test_cache_hit_needs_no_remaining_network_budget(self):
        p = self.policy()
        p.max_requests = 1
        send = Mock(return_value=18)
        with p.turn():
            self.request(p, send)
            self.request(p, send)
            with self.assertRaises(RequestLimitError):
                self.request(p, send, params={'different': True})
            self.assertEqual((p.report()['http_attempts'], p.report()['cache_hits']), (1, 1))
        send.assert_called_once()

    def test_rate_limit_survives_turn_reset_and_spacing_uses_clock(self):
        p = self.policy()
        p.per_minute, p.interval = 2, .25
        send = Mock(return_value=18)
        with p.turn(), p.fresh():
            self.request(p, send)
            self.request(p, send)
        self.assertEqual(self.clock.waits, [.25])
        with p.turn(), self.assertRaises(RequestLimitError):
            self.request(p, send, scope='other')
        self.clock.now = 61
        with p.turn():
            self.request(p, send)
        self.assertEqual(send.call_count, 3)

    def test_timed_out_post_invalidates_all_cached_reads_and_never_retries(self):
        p = self.policy()
        send = Mock(return_value=18)
        with p.turn():
            self.request(p, send)
            failure = Mock(side_effect=TimeoutError('unknown write outcome'))
            with self.assertRaises(TimeoutError):
                self.request(p, failure, method='POST')
            self.request(p, send)
        failure.assert_called_once()
        self.assertEqual(send.call_count, 2)

    def test_cache_is_bounded_by_count_and_payload_bytes(self):
        p = self.policy()
        p.max_requests = p.per_minute = 1000
        with p.turn():
            for number in range(80):
                self.request(p, lambda: 'x' * 100000, params={'page': number})
        self.assertLessEqual(len(p.cache), 64)
        self.assertLessEqual(p.cache_bytes, 4 * 1024 * 1024)
        retained = len(p.cache)
        with p.turn():
            self.request(p, lambda: 'x' * (1024 * 1024 + 1), params={'oversized': True})
        self.assertEqual(len(p.cache), retained)


class TestReadIntegration(unittest.TestCase):
    def client(self):
        c = ERPNextClient(key='synthetic-A', secret='synthetic-B')
        c.read_policy.interval = 0
        return c

    def test_endpoint_credential_and_routing_header_changes_are_isolated(self):
        c = self.client()
        with patch.object(c, '_http_req', return_value=18) as send, c.read_policy.turn():
            c.count('Item')
            c.headers['Authorization'] = 'token another:credential'
            c.count('Item')
            c.headers['X-Frappe-Site-Name'] = 'other-site'
            c.count('Item')
            c.base = 'http://127.0.0.1:8081'
            c.count('Item')
            self.assertEqual(send.call_count, 4)
        report = json.dumps(c.read_policy.report())
        self.assertNotIn('synthetic', report)
        self.assertNotIn('credential', report)

    def test_candidate_mode_skips_count_and_never_claims_completeness(self):
        c = self.client()
        runner = LLMRunner(Agent(c))
        with patch.object(c, '_http_req', return_value=[{'name': 'A'}]) as send, c.read_policy.turn():
            result = runner._tool('list_documents', {'doctype': 'Item', 'fields': ['name'],
                                                   'filters': [['name', 'like', '%A%']], 'include_total': False})
            self.assertEqual(send.call_count, 1)
            self.assertIsNone(result['pagination']['total'])
            self.assertIsNone(result['pagination']['has_more'])
            self.assertEqual(result['pagination']['total_basis'], 'not_queried')
            self.assertTrue(result['warnings'])

    def test_list_pages_reuse_count_but_not_different_offsets(self):
        c = self.client()
        runner = LLMRunner(Agent(c))
        def send(method, path, **kwargs):
            return 2 if 'get_count' in path else [{'name': str(kwargs['params']['limit_start'])}]
        with patch.object(c, '_http_req', side_effect=send) as wire, c.read_policy.turn():
            first = runner._tool('list_documents', {'doctype': 'Item', 'limit': 1})
            last = runner._tool('list_documents', {'doctype': 'Item', 'limit': 1, 'offset': 1})
            self.assertTrue(first['pagination']['has_more'])
            self.assertFalse(last['pagination']['has_more'])
            self.assertEqual(wire.call_count, 3)  # two pages, one count
            self.assertEqual(c.read_policy.report()['cache_hits'], 1)

    def test_aggregate_bypasses_cached_count_and_detects_real_count_change(self):
        c = self.client()
        counts = iter([1, 1, 2])  # prime cache, scan start, scan end
        def send(method, path, **kwargs):
            return next(counts) if 'get_count' in path else [{'name': 'A', 'amount': 10}]
        with patch.object(c, '_http_req', side_effect=send) as wire, c.read_policy.turn():
            c.count('Item')
            with self.assertRaisesRegex(ERPError, 'count changed'):
                c.aggregate('Item', sum_fields=['amount'])
            self.assertEqual(wire.call_count, 4)
            self.assertEqual(c.read_policy.report()['cache_hits'], 0)

    def test_batch_counts_each_upstream_request_and_reports_partial_budget_failure(self):
        c = self.client()
        c.read_policy.max_requests = 2
        def send(method, path, **kwargs):
            return {'name': unquote(path.rsplit('/', 1)[-1])}
        with patch.object(c, '_http_req', side_effect=send) as wire, c.read_policy.turn():
            result = c.get_many('Item', ['A', 'A', 'B', 'C'])
            self.assertFalse(result['complete'])
            self.assertEqual((result['success_count'], result['error_count']), (2, 1))
            self.assertEqual(wire.call_count, 2)
            self.assertIn('budget exhausted', result['results'][-1]['error'])

    def test_preview_and_confirmation_validate_fresh_even_inside_read_turn(self):
        c = self.client()
        fake = FakeERP()
        def send(method, path, **kwargs):
            self.assertEqual(method, 'GET')  # disabled supplier must block POST
            return copy.deepcopy(fake.list(unquote(path.rsplit('/', 1)[-1])))
        a = Agent(c)
        with patch.object(c, '_http_req', side_effect=send), c.read_policy.turn():
            a._validate_parties('Tongling Magnet Wire Co.', 'RM-COIL-CU-2.0', 'Meter')
            fake.items[0]['disabled'] = 1
            with self.assertRaisesRegex(ERPError, 'Item is disabled'):
                a.proposal_po('Tongling Magnet Wire Co.', 'RM-COIL-CU-2.0', 100, 'Meter', 29)
            fake.items[0]['disabled'] = 0
            preview = a.proposal_po('Tongling Magnet Wire Co.', 'RM-COIL-CU-2.0', 100, 'Meter', 29)
            fake.suppliers[0]['disabled'] = 1
            with self.assertRaisesRegex(ERPError, 'Supplier is disabled'):
                a.confirm(preview['proposal_id'])
            self.assertEqual(a.proposals[preview['proposal_id']]['state'], 'pending')

    def test_reconciliation_uses_fresh_remote_values_not_cached_document(self):
        c = self.client()
        a = Agent(c)
        state = {'name': 'PO1', 'docstatus': 0, 'items': [], 'grand_total': 0}
        with patch.object(c, '_http_req', side_effect=lambda *a, **k: copy.deepcopy(state)) as wire, c.read_policy.turn():
            c.get('Purchase Order', 'PO1')
            a.proposals['p1'] = {'state': 'failed', 'created_name': 'PO1', 'doc': {'items': [{}]},
                                 'target_binding': a._target_binding()}
            def check(proposal, name):
                self.assertEqual(c.get('Purchase Order', name)['docstatus'], 1)
                return {'name': name, 'review_required': True}
            state['docstatus'] = 1
            with patch.object(a, '_readback_result', side_effect=check):
                result = a.reconcile('p1')
            self.assertTrue(result['review_required'])
            self.assertEqual(wire.call_count, 2)

    def test_runner_receipts_count_http_and_cache_hits_and_refresh(self):
        c = self.client()
        runner = LLMRunner(Agent(c))
        runner.key, runner.model = 'test', 'test'
        def model_reply():
            return [{'role': 'assistant', 'tool_calls': [
                    {'id': 'c1', 'type': 'function', 'function': {'name': 'count_documents', 'arguments': '{"doctype":"Item"}'}},
                    {'id': 'c2', 'type': 'function', 'function': {'name': 'count_documents', 'arguments': '{"doctype":"Item"}'}}]},
                    {'role': 'assistant', 'content': '18'}]
        def response(request, timeout):
            return io.BytesIO(json.dumps({'choices': [{'message': replies.pop(0)}]}).encode())
        with patch.object(c, '_http_req', return_value=18) as wire, patch('agent.urlopen', side_effect=response):
            replies = model_reply()
            runner.ask('Count Item', [])
            self.assertEqual((runner.last_io['http_attempts'], runner.last_io['cache_hits']), (1, 1))
            self.assertEqual(runner.receipts()[1]['io']['sources'][0]['source'], 'cache')
            runner.force_fresh_next = True
            replies = model_reply()
            runner.ask('Count Item freshly', [])
            self.assertEqual((runner.last_io['http_attempts'], runner.last_io['cache_hits']), (2, 0))
            self.assertEqual(wire.call_count, 3)
