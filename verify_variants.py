"""Run new real-model variants and save evidence; NEVER confirms or creates POs.

Expectations are available to the human reviewer only, not passed to the model.
Machine checks cover transport/errors and unchanged ERP PO IDs. Business answers
still require explicit manual grading; this is not the employer's hidden set.
"""
import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from agent import Agent, ERPNextClient, LLMRunner, configure_console


def po_names(client):
    total = client.count('Purchase Order')
    names = set()
    while len(names) < total:
        rows = client.list('Purchase Order', ['name'], limit=100, offset=len(names), order_by='name asc')
        fresh = {row['name'] for row in rows}
        if not rows or fresh & names:
            raise RuntimeError('Unstable PO pagination; cannot establish no-write gate')
        names.update(fresh)
    if len(names) != total or client.count('Purchase Order') != total:
        raise RuntimeError('PO dataset changed while establishing no-write gate')
    return sorted(names)


def run_case(case):
    client = ERPNextClient()
    # No persistent proposal store. No command parser and no confirmation path.
    runner = LLMRunner(Agent(client))
    before = po_names(client)
    started = time.monotonic()
    result = {'id': case['id'], 'question': case['question'],
              'expected_for_human_review_only': case['expected'], 'manual_grade': 'pending'}
    try:
        result['answer'], _ = runner.ask(case['question'], [])
    except Exception as exc:
        result['error'] = str(exc)
    result['history'] = runner.last_trace
    result['tool_receipts'] = runner.receipts()
    result['elapsed_seconds'] = round(time.monotonic() - started, 2)
    result['po_names_before'] = before
    result['po_names_after'] = po_names(client)
    result['no_erp_po_write'] = result['po_names_before'] == result['po_names_after']
    result['prepared_previews'] = [
        {'proposal_id': key, 'doc': value['doc'], 'total': value['total']}
        for key, value in runner.agent.proposals.items()
    ]
    return result


def main():
    configure_console()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ids', nargs='*', help='Optional case IDs; default all')
    parser.add_argument('--workers', type=int, choices=(1, 2), default=2)
    parser.add_argument('--output', default='variants_run.json')
    options = parser.parse_args()
    root = Path(__file__).parent
    spec = json.loads((root / 'review_cases.json').read_text(encoding='utf-8'))
    cases = [case for case in spec['cases'] if not options.ids or case['id'] in options.ids]
    if not cases:
        raise SystemExit('No matching cases')
    runner = LLMRunner(Agent(ERPNextClient()))
    if not runner.available():
        raise SystemExit('Configure .env locally first')
    report = {'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'model': runner.model,
              'base_url': runner.base, 'thinking': os.getenv('LLM_ENABLE_THINKING', 'provider default'),
              'thinking_budget': os.getenv('LLM_THINKING_BUDGET'),
              'scope': spec['scope'], 'business_grading': 'manual, pending review', 'results': []}
    target = root / 'evidence' / options.output
    target.parent.mkdir(exist_ok=True)
    if target.exists():
        raise SystemExit('Output already exists; choose a new --output filename to preserve the original audit.')
    with ThreadPoolExecutor(max_workers=options.workers) as pool:
        tasks = {pool.submit(run_case, case): case['id'] for case in cases}
        for task in as_completed(tasks):
            result = task.result()
            report['results'].append(result)
            report['results'].sort(key=lambda row: row['id'])
            target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            print(result['id'], 'ERROR' if 'error' in result else 'ANSWER',
                  f"{result['elapsed_seconds']}s", 'no-write:', result['no_erp_po_write'], flush=True)
            print(result.get('answer') or result.get('error'), flush=True)
    if any('error' in row or not row['no_erp_po_write'] for row in report['results']):
        return 1
    print('Business correctness remains pending manual review:', target, flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
