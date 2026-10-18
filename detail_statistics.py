"""Local Decimal statistics over actual, current-turn parent-read results only."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext


def _number(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        raise ValueError(f'Missing/invalid numeric field: {field}')
    try:
        number = Decimal(str(value))
    except InvalidOperation:
        raise ValueError(f'Invalid numeric field: {field}') from None
    if (not number.is_finite() or len(number.as_tuple().digits) > 40
            or (number and abs(number.adjusted()) > 40)):
        raise ValueError(f'Numeric field outside supported precision: {field}')
    return number


def summarize_details(evidence, evidence_refs, table_field, fields=None, row_equals=None):
    """No HTTP, model-supplied rows, eval, or inference of global completeness."""
    if (not isinstance(evidence_refs, list) or not 1 <= len(evidence_refs) <= 40
            or any(not isinstance(i, str) or not i for i in evidence_refs)):
        raise ValueError('evidence_refs must contain 1 to 40 explicit current-turn read references')
    mapping = {'quantity': 'qty', 'amount': 'amount', 'rate': 'rate',
               'currency': 'currency', 'unit': 'uom', 'company': 'company'}
    if fields is not None:
        if not isinstance(fields, dict) or set(fields) - set(mapping):
            raise ValueError('Unknown field mapping')
        mapping.update(fields)
    if any(not isinstance(f, str) or not f.isidentifier() for f in [table_field, *mapping.values()]):
        raise ValueError('Use plain field names')
    row_equals = {} if row_equals is None else row_equals
    if (not isinstance(row_equals, dict) or len(row_equals) > 10
            or any(not isinstance(f, str) or not f.isidentifier()
                   or not isinstance(v, (str, int, bool)) for f, v in row_equals.items())):
        raise ValueError('row_equals must be a small exact field/value object')
    sources, documents, failures = [], [], []
    for evidence_ref in dict.fromkeys(evidence_refs):
        entry = evidence.get(evidence_ref)
        if not entry or entry['tool'] not in ('get_document', 'get_documents'):
            raise ValueError(f'No actual current-turn parent-read evidence: {evidence_ref}')
        args, data = entry['arguments'], entry['data']
        call_id = entry['call_id']
        sources.append({'evidence_ref': evidence_ref, 'call_id': call_id, 'tool': entry['tool'], 'version': entry['version'],
                        'arguments': args, 'io': entry.get('io', {})})
        if entry['tool'] == 'get_document':
            documents.append((args['doctype'], args['name'], data))
        else:
            for result in data['results']:
                if result.get('ok') is True:
                    documents.append((args['doctype'], result['name'], result['data']))
                else:
                    failures.append({'call_id': call_id, 'name': result.get('name'),
                                     'error': result.get('error', 'unknown')})
            if not data.get('complete') and not any(f['call_id'] == call_id for f in failures):
                failures.append({'call_id': call_id, 'error': 'Source reports incomplete coverage'})

    seen, groups, parents, parent_context = {}, {}, set(), {}
    parent_snapshots = {}
    input_rows = duplicates = excluded = 0
    with localcontext() as context:
        context.prec = 200  # bounded inputs: <=40 digits and <=10000 child rows
        for doctype, parent_name, doc in documents:
            if (not isinstance(doc, dict) or doc.get('name') != parent_name
                    or doc.get('doctype', doctype) != doctype):
                raise ValueError('Parent evidence identity mismatch')
            rows = doc.get(table_field)
            if not isinstance(rows, list):
                raise ValueError(f'Missing child table {table_field} in {parent_name}')
            parent_key = (doctype, parent_name)
            observed = {f: doc[f] for f in dict.fromkeys([
                mapping['company'], mapping['currency'], 'docstatus', 'transaction_date', 'posting_date']) if f in doc}
            if parent_key in parent_context and parent_context[parent_key] != observed:
                raise ValueError(f'Conflicting parent observations: {parent_name}')
            parent_context[parent_key] = observed
            # The same parent may be read repeatedly. Never union child rows from
            # different observations and label the result as a complete snapshot.
            # Compare by stable child identity so ordering alone does not conflict.
            snapshot_rows = {}
            for snapshot_row in rows:
                if not isinstance(snapshot_row, dict):
                    raise ValueError('Child evidence row must be an object')
                snapshot_name = snapshot_row.get('name')
                if not isinstance(snapshot_name, str) or not snapshot_name:
                    raise ValueError('Stable child row name is required; equal values do not prove duplicates')
                if snapshot_name in snapshot_rows:
                    raise ValueError(f'Duplicate child row identity within parent snapshot: {snapshot_name}')
                snapshot_rows[snapshot_name] = snapshot_row
            if parent_key in parent_snapshots and parent_snapshots[parent_key] != snapshot_rows:
                raise ValueError(f'Conflicting child-table snapshots for repeated parent: {parent_name}')
            parent_snapshots[parent_key] = snapshot_rows
            for row in rows:
                input_rows += 1
                if input_rows > 10000:
                    raise ValueError('Too many detail rows; narrow the referenced evidence')
                if not isinstance(row, dict) or any(f not in row for f in row_equals):
                    raise ValueError('Missing row filter field; absence is not a non-match')
                if any(row[f] != v for f, v in row_equals.items()):
                    excluded += 1
                    continue
                row_name = row.get('name')
                if not isinstance(row_name, str) or not row_name:
                    raise ValueError('Stable child row name is required; equal values do not prove duplicates')
                if row.get('parent', parent_name) != parent_name or row.get('parenttype', doctype) != doctype:
                    raise ValueError('Child evidence identity mismatch')
                qty, amount, rate = (_number(row.get(mapping[k]), mapping[k]) for k in ('quantity', 'amount', 'rate'))
                currency = row.get(mapping['currency']) or doc.get(mapping['currency'])
                unit = row.get(mapping['unit'])
                company = doc.get(mapping['company'])
                if not isinstance(currency, str) or not currency or not isinstance(unit, str) or not unit:
                    raise ValueError('Missing currency/unit; no automatic conversion or inference')
                if company is not None and not isinstance(company, str):
                    raise ValueError('Invalid company field')
                key = (doctype, parent_name, table_field, row_name)
                signature = (qty, amount, rate, currency, unit, company)
                if key in seen:
                    if seen[key] != signature:
                        raise ValueError(f'Conflicting duplicate row: {row_name}')
                    duplicates += 1
                    continue
                seen[key] = signature
                parents.add(parent_key)
                group = groups.setdefault((company, currency, unit), {
                    'line_count': 0, 'parents': set(), 'quantity_sum': Decimal(0),
                    'line_amount_sum': Decimal(0), 'weighted_rate_numerator': Decimal(0),
                    'rate_min': rate, 'rate_max': rate})
                group['line_count'] += 1
                group['parents'].add(parent_key)
                group['quantity_sum'] += qty
                group['line_amount_sum'] += amount
                group['weighted_rate_numerator'] += qty * rate
                group['rate_min'] = min(group['rate_min'], rate)
                group['rate_max'] = max(group['rate_max'], rate)
        output = []
        for (company, currency, unit), group in groups.items():
            denominator = group['quantity_sum']
            mean = ((group['weighted_rate_numerator'] / denominator).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    if denominator else None)
            output.append({'company': company or 'unknown', 'currency': currency, 'unit': unit,
                           'line_count': group['line_count'], 'distinct_parent_count': len(group['parents']),
                           **{k: format(group[k], 'f') for k in ('quantity_sum', 'line_amount_sum',
                              'rate_min', 'rate_max', 'weighted_rate_numerator')},
                           'weighted_rate_denominator': format(denominator, 'f'),
                           'weighted_rate': format(mean, 'f') if mean is not None else None,
                           'weighted_rate_reason': None if denominator else 'zero_denominator'})
    return {'line_count': len(seen), 'distinct_parent_count': len(parents), 'groups': output,
            'duplicates_collapsed': duplicates, 'examined_rows': input_rows, 'excluded_rows': excluded,
            'complete': not failures, 'failures': failures, 'sources': sources,
            'parent_observations': [{'doctype': d, 'name': n, 'fields': v} for (d, n), v in parent_context.items()],
            'query_scope': {'table_field': table_field, 'fields': mapping, 'row_equals': row_equals,
                            'parent_names': [{'doctype': d, 'name': n} for d, n in parent_context]},
            'calculation': {'weighted_rate': 'sum(quantity * rate) / sum(quantity)',
                            'numerator_is_not_line_amount_sum': True,
                            'rounding': 'Decimal ROUND_HALF_UP to 2 decimal places; sums unrounded'},
            'coverage': 'complete covers only referenced parent reads and selected rows, never the whole business dataset. '
                        'Partial reads are successful-record subtotals. Empty groups have no rate or mean. '
                        'Currency/company/unit groups are separate; no cross-group numerical totals. '
                        'Sequential reads are not a transactional snapshot; cache times remain in sources.'}
