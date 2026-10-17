"""Summarize actual client-side tool messages, independently of model prose.

Receipts show what was queried and returned, not a proof that every sentence in
the answer follows from the data. Full transcripts are retained by eval scripts.
"""
import json


def tool_receipts(messages, tool_metadata=None):
    tool_metadata = tool_metadata or {}
    calls, receipts = {}, []
    for message in messages:
        for call in message.get('tool_calls') or []:
            function = call['function']
            try:
                raw_args = function.get('arguments') or '{}'
                metadata = tool_metadata.get(call['id'], {})
                decimal_arguments = metadata.get('decimal_arguments', function['name'] == 'prepare_purchase_order')
                args = json.loads(raw_args, parse_float=str) if decimal_arguments else json.loads(raw_args)
            except (ValueError, TypeError):
                args = {'unparsed_arguments': function.get('arguments')}
            calls[call['id']] = {'call_id': call['id'], 'tool': function['name'], 'arguments': args}
            if call['id'] in tool_metadata:
                calls[call['id']].update(tool_version=tool_metadata[call['id']]['version'],
                                        tool_effect=tool_metadata[call['id']]['effect'])
        if message.get('role') != 'tool':
            continue
        receipt = dict(calls.get(message.get('tool_call_id'),
                                 {'call_id': message.get('tool_call_id'), 'tool': 'unknown'}))
        try:
            result = json.loads(message['content'])
        except (ValueError, TypeError, KeyError):
            receipt.update(status='unparsed', summary='Tool payload could not be decoded')
            receipts.append(receipt)
            continue
        if not result.get('ok'):
            receipt.update(status='error', error=str(result.get('error', 'Unknown error'))[:300])
        else:
            receipt['status'] = 'ok'
            data = result.get('data')
            name = receipt['tool']
            if name == 'list_documents' and isinstance(data, dict):
                receipt['summary'] = {'pagination': data.get('pagination'),
                                      'query_scope': data.get('query_scope'),
                                      'record_names': [row.get('name') for row in data.get('records', [])],
                                      'warnings': data.get('warnings', [])}
            elif name == 'aggregate_documents' and isinstance(data, dict):
                receipt['summary'] = {key: data.get(key) for key in
                                      ('doctype', 'count', 'matched_rows', 'duplicates_collapsed', 'complete', 'groups', 'consistency')}
                if 'computed_rollups' in data:
                    receipt['summary']['computed_rollups'] = data['computed_rollups']
            elif name == 'get_document' and isinstance(data, dict):
                receipt['summary'] = {key: data[key] for key in ('doctype', 'name', 'docstatus') if key in data}
            elif name == 'get_documents' and isinstance(data, dict):
                receipt['summary'] = {key: data.get(key) for key in
                                      ('doctype', 'input_count', 'requested_names', 'requested_count',
                                       'success_count', 'error_count', 'complete', 'consistency')}
                results = data.get('results') or []
                receipt['summary']['record_names'] = [row['name'] for row in results
                                                      if row.get('ok') is True]
                receipt['summary']['failures'] = [{'name': row.get('name'), 'error': row.get('error')}
                                                  for row in results if row.get('ok') is not True]
            elif name == 'get_doctype_meta' and isinstance(data, dict):
                receipt['summary'] = {'doctype': data.get('doctype'),
                                      'schemas': [doc.get('name') for doc in data.get('docs', [])]}
            elif name == 'prepare_purchase_order' and isinstance(data, dict):
                receipt['summary'] = {key: data.get(key) for key in
                                      ('proposal_id', 'estimated_total', 'requires_confirmation',
                                       'local_state', 'erp_document', 'state_scope')}
            else:
                receipt['summary'] = data
        if 'io' in result:
            receipt['io'] = result['io']
        if result.get('ok') and 'reference_date_evidence' in result:
            receipt['reference_date_evidence'] = result['reference_date_evidence']
        receipts.append(receipt)
    return receipts
