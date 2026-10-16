import unittest
from unittest.mock import patch

from agent import ERPError, ERPNextClient


class TestAggregationArgumentReview(unittest.TestCase):
    def test_repeated_fields_are_summed_and_grouped_once(self):
        client = ERPNextClient()
        rows = [
            {'name': 'A', 'currency': 'USD', 'amount': '10.10'},
            {'name': 'B', 'currency': 'USD', 'amount': '0.20'},
        ]
        with patch.object(client, 'count', return_value=len(rows)), \
                patch.object(client, 'list', return_value=rows) as listing:
            result = client.aggregate(
                'Invoice', group_by=['currency', 'currency'],
                sum_fields=['amount', 'amount'],
            )
        self.assertEqual(result['groups'], [
            {'group': {'currency': 'USD'}, 'count': 2, 'sums': {'amount': '10.30'}}
        ])
        self.assertEqual(listing.call_args.args[1], ['name', 'currency', 'amount'])

    def test_non_array_arguments_are_rejected_before_querying(self):
        client = ERPNextClient()
        for argument in ('group_by', 'sum_fields'):
            for value in ('amount', '', {}, False, 0, ('amount',)):
                with self.subTest(argument=argument, value=value), \
                        patch.object(client, 'count') as count, \
                        self.assertRaisesRegex(ValueError, 'arrays'):
                    client.aggregate('Invoice', **{argument: value})
                count.assert_not_called()

    def test_invalid_field_names_are_rejected_before_querying(self):
        client = ERPNextClient()
        for field in ('', 'sum(amount)', False, None, []):
            with self.subTest(field=field), patch.object(client, 'count') as count, \
                    self.assertRaisesRegex(ValueError, 'plain field names'):
                client.aggregate('Invoice', sum_fields=[field])
            count.assert_not_called()

    def test_false_and_empty_values_are_not_silently_summed_as_zero(self):
        client = ERPNextClient()
        for value in (False, True, '', ' ', [], {}):
            with self.subTest(value=value), \
                    patch.object(client, 'count', return_value=1), \
                    patch.object(client, 'list', return_value=[{'name': 'A', 'amount': value}]), \
                    self.assertRaisesRegex(ERPError, 'non-numeric'):
                client.aggregate('Invoice', sum_fields=['amount'])

    def test_null_and_numeric_zero_remain_valid(self):
        client = ERPNextClient()
        rows = [{'name': 'A', 'amount': None}, {'name': 'B', 'amount': 0}]
        with patch.object(client, 'count', return_value=len(rows)), \
                patch.object(client, 'list', return_value=rows):
            result = client.aggregate('Invoice', sum_fields=['amount'])
        self.assertEqual(result['groups'][0]['sums']['amount'], '0')


if __name__ == '__main__':
    unittest.main()
