"""Narrow arithmetic checks for explicit Markdown aggregation subtotal rows.

Only tables whose detail rows match one complete aggregate result are checked.
This is not a prose/SQL/currency-conversion or general business fact validator.
"""
import json
import re
from decimal import Decimal, InvalidOperation


def aggregate_rollups(data):
    """Small marginal totals from complete groups, preserving explicit partitions."""
    groups = data.get('groups') or []
    if data.get('complete') is not True or not groups or len(groups) > 100:
        return []
    fields = list(groups[0]['group'])
    if len(fields) > 6:
        return []
    partitions = [f for f in fields if f in ('currency', 'company', 'uom', 'stock_uom')
                  or f.endswith('_currency')]
    if not partitions:
        return []  # Do not infer a missing currency/unit partition.
    projections = [partitions] + [[field] + partitions for field in fields if field not in partitions]
    rollups = []
    for selected in projections:
        if set(selected) == set(fields):
            continue
        buckets = {}
        for group in groups:
            key = tuple(group['group'][field] for field in selected)
            bucket = buckets.setdefault(key, {'count': 0, 'sums': {f: Decimal(0) for f in group['sums']}})
            bucket['count'] += group['count']
            for field, value in group['sums'].items():
                bucket['sums'][field] += Decimal(str(value))
        rollups.append({'group_by': selected, 'complete': True,
                        'basis': 'Local Decimal/count calculation over these complete parent groups; no extra ERP reads.',
                        'groups': [{'group': dict(zip(selected, key)), 'count': value['count'],
                                    'sums': {f: str(v) for f, v in value['sums'].items()}}
                                   for key, value in buckets.items()]})
    return rollups


def _text(cell):
    return cell.strip().replace('**', '').strip('` ').strip()


def _number(cell):
    text = _text(cell).replace(',', '')
    if not re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)', text):
        return None
    try:
        value = Decimal(text)
        return value if value.is_finite() else None
    except InvalidOperation:
        return None


def _tables(answer):
    table = []
    for line in answer.splitlines() + ['']:
        if line.strip().startswith('|') and line.strip().endswith('|'):
            cells = [_text(cell) for cell in line.strip().strip('|').split('|')]
            if not all(set(cell) <= set('-: ') for cell in cells):
                table.append(cells)
        elif table:
            yield table
            table = []


def subtotal_checks(answer, messages):
    """Recompute each supported table subtotal independently, never just grand total."""
    calls, sources = {}, []
    for message in messages:
        for call in message.get('tool_calls') or []:
            calls[call.get('id')] = call.get('function', {}).get('name')
        if message.get('role') != 'tool' or calls.get(message.get('tool_call_id')) != 'aggregate_documents':
            continue
        try:
            payload = json.loads(message['content'])
        except (KeyError, TypeError, ValueError):
            continue
        data = payload.get('data') or {}
        if payload.get('ok') and data.get('complete') is True and data.get('groups'):
            sources.append((message['tool_call_id'], data['groups']))
    checks = []
    for table_index, table in enumerate(_tables(answer)):
        detail_rows = []
        for row in table:
            if not any(cell.casefold() in {'小计', '合计', '总计', 'subtotal', 'total'} for cell in row):
                if any(_number(cell) is not None for cell in row):
                    detail_rows.append(row)
                continue
            observed = [_number(cell) for cell in row if _number(cell) is not None]
            if not detail_rows or not observed:
                continue
            for call_id, groups in sources:
                matched, used = [], set()
                for detail in detail_rows:
                    values = [_number(cell) for cell in detail if _number(cell) is not None]
                    labels = [cell for cell in detail if _number(cell) is None]
                    candidates = []
                    for index, group in enumerate(groups):
                        numeric = [Decimal(str(group['count']))] + [Decimal(str(v)) for v in group['sums'].values()]
                        if (index not in used and values == numeric
                                and any(str(value) in labels for value in group['group'].values())):
                            candidates.append(index)
                    if len(candidates) != 1:
                        break  # Unsupported or ambiguous table, not proof of correctness.
                    used.add(candidates[0])
                    matched.append(groups[candidates[0]])
                if len(matched) != len(detail_rows):
                    continue
                # Never silently sum different currencies or units in this check.
                partitions = ('currency', 'uom', 'stock_uom')
                if any(len({g['group'].get(key) for g in matched}) > 1 for key in partitions):
                    continue
                vectors = [[Decimal(str(g['count']))] + [Decimal(str(v)) for v in g['sums'].values()]
                           for g in matched]
                expected = [sum(column, Decimal(0)) for column in zip(*vectors)]
                if len(expected) != len(observed):
                    continue
                checks.append({'source_call_id': call_id, 'table_index': table_index,
                               'source_group_count': len(matched),
                               'columns': ['count'] + list(matched[0]['sums']),
                               'expected': [str(v) for v in expected],
                               'reported': [str(v) for v in observed],
                               'status': 'ok' if expected == observed else 'mismatch'})
                break
            detail_rows = []
    return checks


def subtotal_issues(checks):
    failures = [check for check in checks if check['status'] == 'mismatch']
    if not failures:
        return []
    return ['Program subtotal calculation from matching complete aggregate groups disagrees '
            'with the proposed table: ' + json.dumps(failures, ensure_ascii=False) +
            '. Correct each subtotal independently; a matching grand total does not excuse '
            'opposite errors. Omit unrequested subtotal rows. If needed, cite these program '
            'calculations or call calculate using the existing groups, without new ERP reads.']
