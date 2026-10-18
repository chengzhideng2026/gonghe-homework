"""The simulated model can select references using tool content alone."""
import io
import json
import unittest
from unittest.mock import Mock, patch

from agent import Agent, LLMRunner
from test_detail_statistics import document


def call(call_id, name, args):
    return {'id': call_id, 'type': 'function', 'function': {'name': name, 'arguments': json.dumps(args)}}


def reply(message):
    return io.BytesIO(json.dumps({'choices': [{'message': message, 'finish_reason': 'stop'}]}).encode())


class ReferenceProtocolTests(unittest.TestCase):
    def runner(self):
        client = Mock()
        client.get.side_effect = lambda doctype, name: document(name)
        runner = LLMRunner(Agent(client))
        runner.key, runner.model, runner.base = 'test', 'test', 'https://example.invalid/v1'
        return runner

    def test_multiple_sources_require_explicit_body_references_and_retain_scope(self):
        runner = self.runner()
        requests = []
        selected = []
        def respond(request, timeout):
            body = json.loads(request.data)
            requests.append(body)
            if len(requests) == 1:
                return reply({'role': 'assistant', 'content': None, 'tool_calls': [
                    call('opaque-provider-' + name, 'get_document', {'doctype': 'Unseen Form', 'name': name})
                    for name in ('P1', 'P2', 'P3')]})
            if len(requests) == 2:
                # Do not inspect tool_call_id, assistant call IDs or runner internals.
                returned = [json.loads(m['content']) for m in body['messages'] if m['role'] == 'tool']
                selected.extend(p['evidence_ref'] for p in returned if p['data']['name'] in ('P2', 'P3'))
                return reply({'role': 'assistant', 'content': None, 'tool_calls': [
                    call('stats', 'summarize_details', {'evidence_refs': selected,
                         'table_field': 'lines', 'row_equals': {'code': 'A'}})]})
            return reply({'role': 'assistant', 'content': 'Statistics for selected evidence only.'})
        with patch('agent.urlopen', side_effect=respond):
            runner.ask('Selected evidence')
        summary = runner.receipts()[-1]['summary']
        self.assertEqual((summary['line_count'], summary['distinct_parent_count']), (4, 2))
        self.assertEqual(summary['groups'][0]['quantity_sum'], '16')
        self.assertEqual({s['arguments']['name'] for s in summary['sources']}, {'P2', 'P3'})
        self.assertEqual({s['call_id'] for s in summary['sources']}, {'opaque-provider-P2', 'opaque-provider-P3'})
        self.assertEqual([s['evidence_ref'] for s in summary['sources']], selected)
        self.assertEqual(summary['query_scope']['row_equals'], {'code': 'A'})
        self.assertEqual({p['name'] for p in summary['query_scope']['parent_names']}, {'P2', 'P3'})
        self.assertEqual(runner.agent.c.get.call_count, 3)
        schema = next(t for t in requests[0]['tools'] if t['function']['name'] == 'summarize_details')['function']['parameters']
        self.assertEqual(schema['required'], ['evidence_refs', 'table_field'])
        self.assertNotIn('doctype', schema['properties'])

    def test_stale_body_reference_does_not_select_new_read_even_with_same_parent(self):
        runner = self.runner()
        old_refs, new_refs = [], []
        counter = 0
        def respond(request, timeout):
            nonlocal counter
            counter += 1
            messages = json.loads(request.data)['messages']
            if counter in (1, 3):
                return reply({'role': 'assistant', 'content': None, 'tool_calls': [
                    call('opaque-' + str(counter), 'get_document', {'doctype': 'Unseen Form', 'name': 'P1'})]})
            payload = json.loads([m['content'] for m in messages if m['role'] == 'tool'][-1])
            if counter == 2:
                old_refs.append(payload['evidence_ref'])
                return reply({'role': 'assistant', 'content': 'Observation saved.'})
            if counter == 4:
                new_refs.append(payload['evidence_ref'])
                return reply({'role': 'assistant', 'content': None, 'tool_calls': [
                    call('stale', 'summarize_details', {'evidence_refs': old_refs, 'table_field': 'lines'})]})
            return reply({'role': 'assistant', 'content': 'Need an explicit current reference.'})
        with patch('agent.urlopen', side_effect=respond):
            _, history = runner.ask('Read first')
            runner.ask('New read with stale reference', history)
        self.assertNotEqual(old_refs, new_refs)
        self.assertEqual(runner.receipts()[-1]['status'], 'error')
        self.assertIn('No actual current-turn', runner.receipts()[-1]['error'])
        self.assertEqual(runner.agent.c.get.call_count, 2)


if __name__ == '__main__':
    unittest.main()
