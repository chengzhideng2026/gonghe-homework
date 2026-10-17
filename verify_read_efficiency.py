"""Read-only live evidence for request reuse; --model opts into paid LLM calls."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from agent import Agent, ERPNextClient, LLMRunner, configure_console
from read_policy import RequestLimitError


def run(with_model=False):
    client = ERPNextClient()
    runner = LLMRunner(Agent(client))
    cases = []
    before = client.count('Purchase Order')
    with patch.object(client, '_http_req', wraps=client._http_req) as wire:
        with client.read_policy.turn():
            first = client.count('Item')
            repeated = client.count('Item')
            assert first == repeated
            io = client.read_policy.report()
            assert (io['http_attempts'], io['cache_hits']) == (1, 1)
            cases.append({'case': 'same_exact_count_twice', 'count': first, 'io': io})
        with client.read_policy.turn():
            page = runner._tool('list_documents', {'doctype': 'Item', 'fields': ['name', 'stock_uom'],
                                                  'filters': [['disabled', '=', 0]],
                                                  'limit': 2, 'include_total': False})
            io = client.read_policy.report()
            assert io['http_attempts'] == 1 and page['pagination']['total'] is None
            cases.append({'case': 'bounded_candidate_page_without_count', 'result': page, 'io': io})
        client.read_policy.max_requests = 1
        with client.read_policy.turn(), client.read_policy.fresh():
            client.count('Item')
            try:
                client.count('Supplier')
            except RequestLimitError:
                pass
            else:
                raise AssertionError('Budget failed to prevent an extra request')
            io = client.read_policy.report()
            assert io['http_attempts'] == 1 and io['rejected_requests'] == 1
            cases.append({'case': 'second_request_rejected_before_transport', 'io': io})
        client.read_policy.max_requests = 40
        with client.read_policy.turn():
            result = client.aggregate('Item')
            io = client.read_policy.report()
            assert result['count'] == first and result['complete']
            assert io['http_attempts'] >= 3 and io['cache_hits'] == 0
            cases.append({'case': 'complete_aggregation_fresh_checks', 'result': result, 'io': io})
        # Count the transport calls themselves, not just model-tool receipts.
        assert wire.call_count == sum(case['io']['http_attempts'] for case in cases)
        assert all(call.args[0] == 'GET' for call in wire.call_args_list)
        transport_calls = wire.call_count
    model_cases = []
    if with_model:
        client.read_policy.clear()
        history = []
        questions = [
            '只用 count_documents 查询 Item 记录总数，简短回答，不要查询其他信息。',
            '把刚才查到的 Item 数量乘以2。使用 calculate 计算即可，不要重复请求ERP。',
            '请再次用 count_documents 读取相同的 Item 总数。若客户端返回缓存，标注原读取时间，不要称为实时数据。',
        ]
        for question in questions:
            with patch.object(client, '_http_req', wraps=client._http_req) as wire:
                answer, _ = runner.ask(question, history)
                assert wire.call_count == runner.last_io['http_attempts']
                assert all(call.args[0] == 'GET' for call in wire.call_args_list)
            model_cases.append({'question': question, 'answer': answer, 'io': runner.last_io,
                                'receipts': runner.receipts()})
        assert any(r['tool'] == 'count_documents' and r['status'] == 'ok' for r in model_cases[0]['receipts'])
        assert model_cases[0]['io']['http_attempts'] == 1
        assert any(r['tool'] == 'calculate' and r['status'] == 'ok'
                   and r['summary']['result'] == str(first * 2) for r in model_cases[1]['receipts'])
        assert model_cases[1]['io']['http_attempts'] == 0
        # If >TTL elapsed, the third turn legitimately goes to ERP again.
        assert any(r['tool'] == 'count_documents' and r['status'] == 'ok' for r in model_cases[2]['receipts'])
    after = client.count('Purchase Order')
    assert before == after
    return {'timestamp_utc': datetime.now(timezone.utc).isoformat(),
            'scope': 'Read-only client efficiency and model protocol evidence; directed development cases, not hidden-test scores. '
                     'No ERP API changes, batch endpoint, semantic cache or complete-coverage inference from partial pages.',
            'defaults_tested': {'business_ttl_seconds': client.read_policy.ttl,
                               'metadata_ttl_seconds': client.read_policy.metadata_ttl,
                               'per_turn': client.read_policy.max_requests,
                               'per_minute': client.read_policy.per_minute,
                               'min_interval_seconds': client.read_policy.interval},
            'deterministic_cases': cases, 'deterministic_transport_calls': transport_calls,
            'model': runner.model if with_model else None, 'model_cases': model_cases,
            'model_history': history if with_model else [],
            'po_count_before': before, 'po_count_after': after, 'no_write_dispatched': True}


def main():
    configure_console()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', action='store_true', help='Consumes model API quota')
    parser.add_argument('--output', default='read_efficiency.json')
    args = parser.parse_args()
    if Path(args.output).name != args.output:
        parser.error('--output must be a filename inside evidence/')
    target = Path(__file__).with_name('evidence') / args.output
    if target.exists():
        parser.error('Choose a new output filename to preserve earlier evidence')
    result = run(args.model)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'ok': True, 'deterministic_transport_calls': result['deterministic_transport_calls'],
                      'model_turn_io': [case['io'] for case in result['model_cases']],
                      'answers': [case['answer'] for case in result['model_cases']],
                      'po_count_unchanged': result['po_count_before'] == result['po_count_after']},
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
