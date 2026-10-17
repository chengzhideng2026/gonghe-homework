import unittest
from unittest.mock import Mock
from agent import check_model


class TestModelCheck(unittest.TestCase):
    def runner(self):
        runner = Mock()
        runner.available.return_value = True
        runner.agent.c.count.return_value = 18
        runner.ask.return_value = ('18', [])
        runner.max_rounds, runner.model = 16, 'test-model'
        runner.receipts.return_value = [{'tool': 'count_documents', 'status': 'ok',
                                         'arguments': {'doctype': 'Item'}, 'summary': 18}]
        return runner

    def test_check_requires_real_matching_tool_receipt_not_only_model_text(self):
        runner = self.runner()
        self.assertTrue(check_model(runner)['ok'])
        runner.receipts.return_value = []
        result = check_model(runner)
        self.assertFalse(result['ok'])
        self.assertEqual(result['stage'], 'tool_protocol')

    def test_bad_erp_or_configuration_does_not_consume_model_request(self):
        runner = self.runner()
        runner.available.return_value = False
        self.assertEqual(check_model(runner)['stage'], 'configuration')
        runner.ask.assert_not_called()
        runner.available.return_value = True
        runner.agent.c.count.side_effect = TimeoutError('ERP unavailable')
        self.assertEqual(check_model(runner)['stage'], 'erp')
        runner.ask.assert_not_called()
