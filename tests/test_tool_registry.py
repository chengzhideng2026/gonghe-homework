import io
import json
import unittest
from contextlib import redirect_stdout
from decimal import Decimal
from unittest.mock import Mock, patch

import agent as app
from agent import Agent, LLMRunner
from erp_tools import BUILTIN_TOOLS
from tool_registry import ToolRegistry
from test_agent import FakeERP


def definition(name='echo_value'):
    return {'type': 'function', 'function': {'name': name, 'description': 'Test extension',
            'parameters': {'type': 'object', 'properties': {'value': {'type': 'number'}},
                           'required': ['value']}}}


def reply(message):
    return io.BytesIO(json.dumps({'choices': [{'message': message, 'finish_reason': 'stop'}]}).encode())


def call(name, arguments='{}', call_id='c1'):
    return {'role': 'assistant', 'tool_calls': [{'id': call_id, 'type': 'function',
            'function': {'name': name, 'arguments': arguments}}]}


class TestToolRegistry(unittest.TestCase):
    def test_registration_couples_discovery_handler_and_metadata(self):
        registry = ToolRegistry()
        seen = []
        registry.register(definition(), lambda context, args: seen.append(context) or args['value'],
                          version='2')
        view = registry.snapshot()
        self.assertEqual(view.definitions()[0]['function']['name'], 'echo_value')
        self.assertEqual(view.invoke('echo_value', {'value': 3}, 'context'), 3)
        self.assertEqual(seen, ['context'])
        self.assertEqual(view.metadata('echo_value')['version'], '2')
        self.assertEqual(registry.describe()[0]['effect'], 'read')

    def test_duplicate_privileged_or_invalid_registration_does_not_replace_handler(self):
        registry = ToolRegistry()
        for invalid in (None, [], {'type': 'function', 'function': None}):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                registry.register(invalid, lambda context, args: None)
        registry.register(definition(), lambda context, args: 'original')
        with self.assertRaisesRegex(ValueError, 'already registered'):
            registry.register(definition(), lambda context, args: 'replacement')
        for name in ('confirm', 'reconcile', 'execute_sql', 'shell', 'http_get', 'cancel_document'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                registry.register(definition(name), lambda context, args: None)
        with self.assertRaises(ValueError):
            registry.register(definition('unsafe'), lambda context, args: None, effect='write')
        self.assertEqual(registry.snapshot().invoke('echo_value', {'value': 3}, None), 'original')

    def test_definitions_are_copied_on_registration_and_discovery(self):
        registry = ToolRegistry()
        original = definition()
        registry.register(original, lambda context, args: args)
        original['function']['parameters']['properties'].clear()
        exported = registry.definitions()
        exported[0]['function']['name'] = 'tampered'
        self.assertEqual(registry.definitions()[0]['function']['name'], 'echo_value')
        self.assertEqual(registry.snapshot().invoke('echo_value', {'value': 2}, None), {'value': 2})

    def test_disabling_blocks_even_previously_advertised_views(self):
        registry = ToolRegistry()
        handler = Mock()
        registry.register(definition(), handler)
        view = registry.snapshot()
        registry.set_enabled('echo_value', False)
        self.assertEqual(registry.definitions(), [])
        with self.assertRaisesRegex(ValueError, 'not available'):
            view.invoke('echo_value', {'value': 1}, None)
        handler.assert_not_called()
        registry.set_enabled('echo_value', True)
        registry.snapshot().invoke('echo_value', {'value': 1}, None)
        handler.assert_called_once()

    def test_removed_or_replaced_tool_never_runs_under_an_old_contract(self):
        registry = ToolRegistry()
        original, replacement = Mock(), Mock()
        registry.register(definition(), original)
        view = registry.snapshot()
        registry.unregister('echo_value')
        with self.assertRaises(ValueError):
            view.invoke('echo_value', {'value': 1}, None)
        registry.register(definition(), replacement, version='2')
        with self.assertRaises(ValueError):
            view.invoke('echo_value', {'value': 1}, None)
        original.assert_not_called()
        replacement.assert_not_called()
        registry.snapshot().invoke('echo_value', {'value': 1}, None)
        replacement.assert_called_once()

    def test_session_clones_do_not_change_other_sessions_or_default_catalog(self):
        first, second = BUILTIN_TOOLS.clone(), BUILTIN_TOOLS.clone()
        first.set_enabled('calculate', False)
        first.unregister('get_document')
        self.assertEqual(len(first.definitions()), 6)
        self.assertEqual(len(second.definitions()), 8)
        self.assertEqual(len(BUILTIN_TOOLS.definitions()), 8)

    def test_json_arguments_preserve_decimal_policy_and_reject_non_objects_or_nonfinite(self):
        registry = ToolRegistry()
        handler = Mock(side_effect=lambda context, args: args['value'])
        registry.register(definition(), handler, decimal_arguments=True)
        view = registry.snapshot()
        result = view.invoke_json('echo_value', '{"value":1.00000000000000001}', None)
        self.assertEqual(result, Decimal('1.00000000000000001'))
        for raw in ('[]', 'null', '{"value":NaN}', '{"value":Infinity}', '{"value":false}',
                    '{"value":1,"url":"https://evil.invalid"}', '{}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                view.invoke_json('echo_value', raw, None)
        self.assertEqual(handler.call_count, 1)

    def test_handler_started_before_revocation_can_finish_without_catalog_lock(self):
        registry = ToolRegistry()
        def running(context, args):
            registry.set_enabled('echo_value', False)
            return args['value']
        registry.register(definition(), running)
        view = registry.snapshot()
        self.assertEqual(view.invoke('echo_value', {'value': 1}, None), 1)
        with self.assertRaises(ValueError):
            view.invoke('echo_value', {'value': 2}, None)


class TestRegistryRunnerIntegration(unittest.TestCase):
    def runner(self, registry=None):
        runner = LLMRunner(Agent(FakeERP()), registry)
        runner.base, runner.key, runner.model = 'https://example.invalid/v1', 'test-key', 'test-model'
        return runner

    def test_new_tool_is_advertised_executed_and_receipted_without_dispatch_changes(self):
        runner = self.runner()
        runner.registry.register(definition(), lambda context, args: {'value': str(args['value'])},
                                 version='plugin-1', decimal_arguments=True)
        responses = [call('echo_value', '{"value":1.00000000000000001}'),
                     {'role': 'assistant', 'content': 'Recorded exact value.'}]
        requests = []
        def respond(request, timeout):
            requests.append(json.loads(request.data))
            return reply(responses.pop(0))
        with patch('agent.urlopen', side_effect=respond):
            runner.ask('Use the extension', [])
        self.assertEqual(len(requests[0]['tools']), 9)
        receipt = runner.receipts()[0]
        self.assertEqual(receipt['arguments']['value'], '1.00000000000000001')
        self.assertEqual(receipt['tool_version'], 'plugin-1')
        self.assertEqual(receipt['tool_effect'], 'read')
        self.assertEqual(receipt['summary']['value'], '1.00000000000000001')
        self.assertEqual(runner.agent.c.created, [])

    def test_revocation_during_model_request_blocks_execution_and_next_advertisement(self):
        runner = self.runner()
        runner.agent.c.count = Mock(return_value=18)
        requests = []
        def respond(request, timeout):
            requests.append(json.loads(request.data))
            if len(requests) == 1:
                runner.registry.set_enabled('count_documents', False)
                return reply(call('count_documents', '{"doctype":"Item"}'))
            return reply({'role': 'assistant', 'content': 'The tool is unavailable.'})
        with patch('agent.urlopen', side_effect=respond):
            runner.ask('Count Item', [])
        self.assertEqual(len(requests[0]['tools']), 8)
        self.assertEqual(len(requests[1]['tools']), 7)
        self.assertFalse(any(t['function']['name'] == 'count_documents' for t in requests[1]['tools']))
        runner.agent.c.count.assert_not_called()
        self.assertEqual(runner.receipts()[0]['status'], 'error')

    def test_new_registration_is_available_only_after_a_new_advertisement(self):
        runner = self.runner()
        handler = Mock(return_value=3)
        requests = []
        def respond(request, timeout):
            requests.append(json.loads(request.data))
            if len(requests) == 1:
                runner.registry.register(definition(), handler)
                return reply(call('echo_value', '{"value":3}', 'unadvertised'))
            if len(requests) == 2:
                return reply(call('echo_value', '{"value":3}', 'advertised'))
            return reply({'role': 'assistant', 'content': '3'})
        with patch('agent.urlopen', side_effect=respond):
            runner.ask('Use the new tool', [])
        handler.assert_called_once()
        self.assertEqual((len(requests[0]['tools']), len(requests[1]['tools'])), (8, 9))
        self.assertEqual([r['status'] for r in runner.receipts()], ['error', 'ok'])

    def test_empty_registry_omits_tools_and_tool_choice_from_provider_request(self):
        runner = self.runner(ToolRegistry())
        requests = []
        def respond(request, timeout):
            requests.append(json.loads(request.data))
            return reply({'role': 'assistant', 'content': 'No live tools are available.'})
        with patch('agent.urlopen', side_effect=respond):
            runner.ask('What tools are available?', [])
        self.assertNotIn('tools', requests[0])
        self.assertNotIn('tool_choice', requests[0])
        self.assertEqual(runner.receipts(), [])

    def test_cli_enable_disable_and_inventory_do_not_call_the_model(self):
        output = io.StringIO()
        with patch.object(app, 'ERPNextClient', return_value=FakeERP()), \
             patch.object(app, 'ProposalStore', return_value=None), \
             patch.object(app.LLMRunner, 'available', return_value=True), \
             patch.object(app.LLMRunner, 'ask') as ask, \
             patch('sys.argv', ['agent.py']), \
             patch('builtins.input', side_effect=['/tools', '/tools disable count_documents',
                   '/tools enable count_documents', '/tools disable missing', '/quit']), redirect_stdout(output):
            app.main()
        ask.assert_not_called()
        rendered = output.getvalue()
        self.assertIn('"enabled": false', rendered)
        self.assertIn('"enabled": true', rendered)
        self.assertIn('Tool not registered: missing', rendered)
