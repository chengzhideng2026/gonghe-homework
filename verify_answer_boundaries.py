"""Directed before/after answer review; never confirms or writes ERP documents."""
import argparse
import hashlib
import json
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from agent import Agent, ERPNextClient, LLMRunner, configure_console
from proposal_store import ProposalStore
from verify_variants import po_names


class NoWritesERP(ERPNextClient):
    def create(self, *args, **kwargs):
        raise AssertionError('ERP writes are forbidden in this acceptance run')


def run_case(case, fixture_root):
    client = NoWritesERP()
    store = ProposalStore(fixture_root / (case['id'] + '.sqlite3'))
    runner = LLMRunner(Agent(client, store=store))
    result = {'id': case['id'], 'boundary': case['boundary'], 'turns': [],
              'review_criteria_not_sent_to_model': case['review_criteria'],
              'business_review': {'reviewer': 'AI-assisted review', 'status': 'pending'},
              'human_operator_validation': {'status': 'not_performed'}}
    history = []
    started = time.monotonic()
    for question in [case['question']] + ([case['follow_up']] if case.get('follow_up') else []):
        row = {'question': question}
        with patch.object(client, '_http_req', wraps=client._http_req) as wire:
            try:
                row['answer'], history = runner.ask(question, history)
            except Exception as exc:
                row['error'] = str(exc)
            row.update(history=runner.last_trace, receipts=runner.receipts(), io=runner.last_io,
                       turn_id=runner.turn_id, provider_usage=runner._turn_usages,
                       erp_http_methods=[call.args[0] for call in wire.call_args_list])
        result['turns'].append(row)
        if row.get('error'):
            break
    result['local_proposals'] = [{'proposal_id': key, 'state': value['state'],
                                  'doc': value['doc'], 'total': value['total'],
                                  'created_name': value.get('created_name')}
                                 for key, value in store.active(runner.agent._target_binding()).items()]
    result['elapsed_seconds'] = round(time.monotonic() - started, 3)
    return result


def main():
    configure_console()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, help='New JSON filename under evidence/')
    parser.add_argument('--phase', required=True, choices=['before', 'after'])
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    if Path(args.output).name != args.output or not args.output.endswith('.json'):
        parser.error('Use a JSON filename inside evidence/')
    target = root / 'evidence' / args.output
    if target.exists():
        parser.error('Choose a new filename to preserve earlier evidence')
    spec = json.loads((root / 'answer_boundary_cases.json').read_text(encoding='utf-8'))
    audit = NoWritesERP()
    before = po_names(audit)
    report = {'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'phase': args.phase,
              'scope': spec['scope'],
              'git_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root).decode().strip(),
              'runtime_sha256': {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                                 for name in ['agent.py', 'erp_tools.py', 'tool_receipts.py', 'context_budget.py']},
              'spec_sha256': hashlib.sha256((root / 'answer_boundary_cases.json').read_bytes()).hexdigest(),
              'program_checks': {'no_post': 'pending', 'po_names_unchanged': 'pending'},
              'human_operator_validation': {'status': 'not_performed'}, 'results': []}
    fixture_parent = root / '.local' / 'answer-boundary-checks'
    fixture_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=fixture_parent) as fixture:
        for case in spec['cases']:
            row = run_case(case, Path(fixture))
            report['results'].append(row)
            target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            print(row['id'], row['elapsed_seconds'], flush=True)
            for turn in row['turns']:
                print(turn.get('answer') or turn.get('error'), flush=True)
    after = po_names(audit)
    no_post = all(method == 'GET' for row in report['results']
                  for turn in row['turns'] for method in turn['erp_http_methods'])
    report['program_checks'] = {'no_post': no_post, 'po_names_unchanged': before == after,
                                'po_names_before': before, 'po_names_after': after,
                                'scope': 'Execution checks only, not proof of business prose correctness'}
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    if not no_post or before != after or any(turn.get('error') for row in report['results'] for turn in row['turns']):
        return 1
    print('Execution checks passed. Business prose still requires review; no human operation is claimed.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
