"""Read-only first rerun of selected frozen questions; no business auto-grading."""
import argparse
import hashlib
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit
from unittest.mock import patch

import agent as app
import verify_answer_boundaries as harness
from execution_trace import ExecutionTraceWriter
from verify_variants import po_names


def main():
    app.configure_console()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--retry-of', help='Earlier JSON filename under evidence/')
    parser.add_argument('--retry-reason')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    if Path(args.output).name != args.output or not args.output.endswith('.json'):
        parser.error('Use a new JSON filename under evidence/')
    target = root / 'evidence' / args.output
    if target.exists():
        parser.error('Refusing to overwrite earlier evidence')
    spec = json.loads((root / 'n05_n07_cases.json').read_text(encoding='utf-8'))
    native, real_runner = app.urlopen, app.LLMRunner
    events, runners, active = [], [], None
    audit = harness.NoWritesERP()
    model_url = app.validate_url(app.os.getenv('LLM_BASE_URL'), endpoint=True) + '/chat/completions'

    def readonly_wire(request, timeout):
        if request.full_url == model_url:
            if request.get_method() != 'POST':
                raise AssertionError('Unexpected model method')
            if sum(e['kind'] == 'model' for e in events) >= 24:
                raise RuntimeError('Evaluation model-call cap reached')
            payload = json.loads(request.data)
            payload['max_tokens'] = 4096
            request.data = json.dumps(payload).encode('utf-8')
            kind = 'model'
        elif request.full_url.startswith(audit.base + '/'):
            part = urlsplit(request.full_url[len(audit.base):])
            allowed_rpc = {'/api/method/frappe.client.get_count', '/api/method/frappe.desk.form.load.getdoctype'}
            if (request.get_method() != 'GET' or 'cmd' in parse_qs(part.query)
                    or not (unquote(part.path).startswith('/api/resource/') or part.path in allowed_rpc)):
                raise AssertionError('ERP method/endpoint is not read-only')
            kind = 'erp'
        else:
            raise AssertionError('Unexpected endpoint')
        event = {'case': active, 'kind': kind, 'method': request.get_method(),
                 'url': request.full_url if kind == 'erp' else model_url}
        events.append(event)
        try:
            result = native(request, timeout=timeout)
            event['status'] = 'response_received'
            return result
        except Exception as exc:
            event.update(status='error', error_type=type(exc).__name__)
            raise

    def configured_runner(agent):
        runner = real_runner(agent)
        runner.turn_timeout, runner.max_rounds = 180, 12
        agent.c.read_policy.max_requests = 30
        runner.trace_writer = ExecutionTraceWriter(root / '.local' / 'n05_n07_traces')
        runners.append(runner)
        return runner

    report = {'timestamp_utc': datetime.now(timezone.utc).isoformat(),
              'scope': spec['scope'], 'model_settings': {'turn_seconds': 180, 'max_rounds': 12,
              'output_token_cap': 4096, 'erp_requests_per_turn': 30},
              'source_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in root.glob('*.py')}, 'results': [],
              'business_review': 'not_assessed', 'human_operator_validation': 'not_performed'}
    if args.retry_of:
        if Path(args.retry_of).name != args.retry_of or not args.retry_reason:
            parser.error('Retry requires an earlier evidence filename and an explicit reason')
        prior = root / 'evidence' / args.retry_of
        report['retry'] = {'file': args.retry_of, 'sha256': hashlib.sha256(prior.read_bytes()).hexdigest(),
                           'reason': args.retry_reason}
    fixtures = root / '.local' / 'selected-regression-fixtures'
    fixtures.mkdir(parents=True, exist_ok=True)
    with patch('agent.urlopen', readonly_wire), patch.object(harness, 'LLMRunner', configured_runner):
        before = po_names(audit)
        with tempfile.TemporaryDirectory(dir=fixtures) as directory:
            for case in spec['cases']:
                active = case['id']
                row = harness.run_case(case, Path(directory))
                row['program_subtotal_checks'] = runners[-1].last_subtotal_checks
                report['results'].append(row)
                report['wire_events'] = events
                target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
                print(case['id'], row['elapsed_seconds'], flush=True)
                for turn in row['turns']:
                    print(turn.get('answer') or turn.get('error'), flush=True)
        active = None
        after = po_names(audit)
    report['execution_checks'] = {'erp_writes': sum(e['kind'] == 'erp' and e['method'] != 'GET' for e in events),
                                  'purchase_names_unchanged': before == after,
                                  'before_names': before, 'after_names': after,
                                  'agent_erp_http': sum(e['kind'] == 'erp' and e['case'] is not None for e in events),
                                  'audit_erp_http': sum(e['kind'] == 'erp' and e['case'] is None for e in events)}
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return 1 if before != after or any(t.get('error') for r in report['results'] for t in r['turns']) else 0


if __name__ == '__main__':
    raise SystemExit(main())
