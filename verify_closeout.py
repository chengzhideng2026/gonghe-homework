"""Run a small, read-only closeout variation set; business grading remains manual."""
import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from agent import Agent, ERPNextClient, LLMRunner, configure_console
from verify_variants import po_names


def run_case(case):
    client = ERPNextClient()
    runner = LLMRunner(Agent(client))
    before = po_names(client)
    started = time.monotonic()
    row = {'id': case['id'], 'question': case['question'],
           'expected_for_human_review_only': case.get('expected'), 'manual_grade': 'pending'}
    history = []
    try:
        answer, history = runner.ask(case['question'], history)
        row['turns'] = [{'question': case['question'], 'answer': answer,
                         'receipts': runner.receipts(), 'io': runner.last_io,
                         'context': runner.last_context}]
        if case.get('follow_up'):
            answer, history = runner.ask(case['follow_up'], history)
            row['turns'].append({'question': case['follow_up'], 'answer': answer,
                                 'receipts': runner.receipts(), 'io': runner.last_io,
                                 'context': runner.last_context})
    except Exception as exc:
        row['error'] = str(exc)
        row['turns'] = []
    row['history'] = history
    row['elapsed_seconds'] = round(time.monotonic() - started, 2)
    row['po_names_before'] = before
    row['po_names_after'] = po_names(client)
    row['no_erp_po_write'] = row['po_names_before'] == row['po_names_after']
    row['prepared_previews'] = [{'proposal_id': key, 'doc': value['doc'], 'total': value['total']}
                                for key, value in runner.agent.proposals.items()]
    return row


def main():
    configure_console()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='closeout_run.json')
    parser.add_argument('--ids', nargs='*')
    options = parser.parse_args()
    root = Path(__file__).parent
    spec = json.loads((root / 'closeout_cases.json').read_text(encoding='utf-8'))
    cases = [case for case in spec['cases'] if not options.ids or case['id'] in options.ids]
    if not cases or len(cases) > 8:
        raise SystemExit('Choose between 1 and 8 cases')
    target = root / 'evidence' / options.output
    if target.exists():
        raise SystemExit('Output already exists; choose a new filename')
    report = {'timestamp_utc': datetime.now(timezone.utc).isoformat(),
              'model': LLMRunner(Agent(ERPNextClient())).model,
              'case_specification': 'closeout_cases.json',
              'scope': spec['scope'], 'business_grading': 'manual, pending review', 'results': []}
    for case in cases:
        row = run_case(case)
        report['results'].append(row)
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(row['id'], 'ERROR' if 'error' in row else 'ANSWER', row['elapsed_seconds'],
              'no-write:', row['no_erp_po_write'], flush=True)
        if row.get('turns'):
            print(row['turns'][-1]['answer'], flush=True)
    if any('error' in row or not row['no_erp_po_write'] for row in report['results']):
        return 1
    print('Business correctness remains pending manual review:', target, flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
