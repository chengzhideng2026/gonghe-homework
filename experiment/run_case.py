"""Run ONE frozen case/variant once. No retries; raw evidence retained for review."""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, unquote, urlsplit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--env-file', required=True)
    parser.add_argument('--variant', choices=['baseline', 'experiment', 'fixed'], required=True)
    parser.add_argument('--case', choices=['D01', 'D02'], required=True)
    parser.add_argument('--interface-pair', action='store_true', help='Final authorized pair on frozen D02 only')
    options = parser.parse_args()
    root = Path(__file__).resolve().parent
    spec_bytes = (root / 'cases.json').read_bytes()
    spec = json.loads(spec_bytes)
    case = next(c for c in spec['cases'] if c['id'] == options.case)
    pair_plan = None
    if options.interface_pair:
        pair_plan = json.loads((root / 'interface_pair.json').read_text(encoding='utf-8'))
        if (options.case != pair_plan['source_case'] or options.variant not in pair_plan['variants']
                or case['question'] != pair_plan['question']):
            raise RuntimeError('Final pair must use frozen D02 unchanged, baseline/fixed once each')
    elif options.variant == 'fixed':
        raise RuntimeError('Fixed variant is only allowed in the final interface pair')
    repo = Path(options.repo).resolve()
    sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo).decode().strip()
    if options.variant == 'baseline' and sha != spec['baseline']:
        raise RuntimeError('Wrong baseline')
    for line in Path(options.env_file).read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))
    sys.path.insert(0, str(repo))
    import agent as app
    from execution_trace import ExecutionTraceWriter
    from verify_variants import po_names
    app.configure_console()
    prefix = 'interface_' if options.interface_pair else ''
    output = root / 'evidence' / f'{prefix}{options.case}_{options.variant}.json'
    # Exclusive marker survives interruption. Do not re-run even if result is missing.
    with output.with_suffix('.started').open('x', encoding='utf-8') as marker:
        marker.write(datetime.now(timezone.utc).isoformat())
    if output.exists():
        raise RuntimeError('Refusing to overwrite first result')
    events = []
    request_measurements = []
    phase = 'audit_before'
    native = app.urlopen
    client = app.ERPNextClient()
    runner = app.LLMRunner(app.Agent(client))
    runner.trace_writer = ExecutionTraceWriter(root.parent / '.local' / 'experiment-traces')
    model_url = runner.base + '/chat/completions'

    def wire(request, timeout):
        if request.full_url == model_url and request.get_method() == 'POST' and phase == 'ask':
            body = json.loads(request.data)
            body['max_tokens'] = 4096
            request.data = json.dumps(body).encode('utf-8')
            messages_json = json.dumps(body['messages']).encode('utf-8')
            tools_json = json.dumps(body.get('tools', [])).encode('utf-8')
            request_measurements.append({
                'round': len(request_measurements) + 1, 'payload_bytes': len(request.data),
                'messages_bytes': len(messages_json), 'tool_definition_bytes': len(tools_json),
                'messages_sha256': hashlib.sha256(messages_json).hexdigest(),
                'tools_sha256': hashlib.sha256(tools_json).hexdigest(),
                'public_evidence_refs_in_tool_bodies': [json.loads(m['content'])['evidence_ref']
                    for m in body['messages'] if m.get('role') == 'tool'
                    and 'evidence_ref' in json.loads(m['content'])]})
            kind = 'model'
        elif request.full_url.startswith(client.base + '/'):
            part = urlsplit(request.full_url[len(client.base):])
            rpc = {'/api/method/frappe.client.get_count', '/api/method/frappe.desk.form.load.getdoctype'}
            if (request.get_method() != 'GET' or 'cmd' in parse_qs(part.query)
                    or not (unquote(part.path).startswith('/api/resource/') or part.path in rpc)):
                raise AssertionError('ERP writes and non-allowlisted endpoints are forbidden')
            kind = 'erp'
        else:
            raise AssertionError('Unexpected endpoint')
        event = {'phase': phase, 'kind': kind, 'method': request.get_method(),
                 'url': request.full_url if kind == 'erp' else model_url}
        events.append(event)
        try:
            result = native(request, timeout=timeout)
            event['status'] = 'response_received'
            return result
        except Exception as exc:
            event.update(status='error', error_type=type(exc).__name__)
            raise

    report = {'case': case, 'variant': options.variant, 'git_sha': sha,
              'cases_sha256': hashlib.sha256(spec_bytes).hexdigest(),
              'timestamp_utc': datetime.now(timezone.utc).isoformat(),
              'runtime_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in repo.glob('*.py')},
              'settings': {'model': runner.model, 'turn_timeout': runner.turn_timeout,
                           'max_rounds': runner.max_rounds, 'model_timeout': runner.timeout,
                           'erp_per_turn': client.read_policy.max_requests,
                           'erp_per_minute': client.read_policy.per_minute,
                           'erp_interval': client.read_policy.interval,
                           'context_bytes': runner.context_max_bytes, 'max_tokens': 4096},
              'business_review': 'pending AI review, not a program pass',
              'human_operation': 'not_performed'}
    if pair_plan is not None:
        report['interface_pair_plan'] = pair_plan
        report['retained_oracle'] = {'file': 'D02_baseline.json',
            'sha256': hashlib.sha256((root / 'evidence' / 'D02_baseline.json').read_bytes()).hexdigest(),
            'expected': json.loads((root / 'evidence' / 'D02_baseline.json').read_text(encoding='utf-8'))['independent_oracle']['expected']}
    try:
        with patch('agent.urlopen', side_effect=wire):
            audit = app.ERPNextClient()
            before = po_names(audit)
            report['purchase_names_before'] = before
            if options.variant == 'baseline' and not options.interface_pair:
                phase = 'independent_oracle'
                # Independent raw reads + direct Decimal formula, no experiment tool reuse.
                filters = [['company', '=', 'Crestwind Compressor Manufacturing Co.'],
                           ['docstatus', '=', 1], ['transaction_date', '<=', '2025-10-15'],
                           [case['child_doctype'], 'item_code', '=', case['item']]]
                total = audit.count(case['doctype'], filters)
                raw = []
                while len(raw) < total:
                    page = audit.list(case['doctype'], ['name'], filters, 100, len(raw), 'name asc')
                    if not page:
                        raise RuntimeError('Oracle incomplete pagination')
                    raw.extend(page)
                if len(raw) != total or audit.count(case['doctype'], filters) != total:
                    raise RuntimeError('Oracle unstable pagination')
                names = list(dict.fromkeys(row['name'] for row in raw))
                docs = [audit.get(case['doctype'], name) for name in names]
                groups = {}
                for doc in docs:
                    if (doc['docstatus'] != 1 or doc['transaction_date'] > '2025-10-15'
                            or doc['company'] != 'Crestwind Compressor Manufacturing Co.'):
                        raise RuntimeError('Oracle scope mismatch')
                    for row in doc['items']:
                        if row['item_code'] != case['item']:
                            continue
                        key = (doc['company'], doc['currency'], row['uom'])
                        group = groups.setdefault(key, {'rows': [], 'parents': set(),
                            'qty': Decimal(0), 'amount': Decimal(0), 'numerator': Decimal(0), 'rates': []})
                        qty, amount, rate = [Decimal(str(row[f])) for f in ('qty', 'amount', 'rate')]
                        group['rows'].append(row['name'])
                        group['parents'].add(doc['name'])
                        group['qty'] += qty
                        group['amount'] += amount
                        group['numerator'] += qty * rate
                        group['rates'].append(rate)
                expected = []
                for (company, currency, unit), group in groups.items():
                    expected.append({'company': company, 'currency': currency, 'unit': unit,
                        'line_count': len(group['rows']), 'parent_count': len(group['parents']),
                        'qty': str(group['qty']), 'amount': str(group['amount']),
                        'min': str(min(group['rates'])), 'max': str(max(group['rates'])),
                        'numerator': str(group['numerator']), 'denominator': str(group['qty']),
                        'weighted_rate': str((group['numerator'] / group['qty']).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)) if group['qty'] else None})
                report['independent_oracle'] = {'filters': filters, 'raw_parent_page': raw,
                                               'documents': docs, 'expected': expected}
            phase = 'ask'
            started = time.monotonic()
            try:
                report['answer'], _ = runner.ask(case['question'], [])
            except Exception as exc:
                report['error'] = app.redact(exc, (runner.key,), 1000)
            finally:
                report['elapsed_seconds'] = round(time.monotonic() - started, 3)
                report['history'] = runner.last_trace
                report['receipts'] = runner.receipts()
                report['tool_calls'] = runner._turn_calls
                report['io'] = runner.last_io
                report['context'] = runner.last_context
                report['end_reason'] = runner._trace_end_reason
                report['actual_model_request_measurements'] = request_measurements
                calls = sum(e['kind'] == 'model' for e in events)
                usage = runner._turn_usages
                report['model_calls'] = calls
                report['erp_http_requests'] = sum(e['kind'] == 'erp' and e['phase'] == 'ask' for e in events)
                report['usage'] = {'status': 'reported' if usage and len(usage) == calls else 'unknown_or_partial',
                                   'events': usage or 'unknown'}
                report['usage']['totals'] = ({k: sum(u[k] for u in usage) for k in ('prompt_tokens', 'completion_tokens', 'total_tokens')}
                    if usage and len(usage) == calls and all(all(k in u for k in ('prompt_tokens', 'completion_tokens', 'total_tokens')) for u in usage) else 'unknown')
            phase = 'audit_after'
            report['purchase_names_after'] = po_names(audit)
            report['purchase_names_unchanged'] = before == report['purchase_names_after']
    finally:
        report['wire_events'] = events
        report['erp_writes'] = sum(e['kind'] == 'erp' and e['method'] != 'GET' for e in events)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    print(options.case, options.variant, report.get('elapsed_seconds'), report.get('model_calls'), report.get('erp_http_requests'))
    print(report.get('answer') or report.get('error'))


if __name__ == '__main__':
    main()
