"""Summarize actual client-side tool messages, independently of model prose.

Receipts show what was queried and returned, not a proof that every sentence in
the answer follows from the data. Full transcripts are retained by eval scripts.
"""
import json


def tool_receipts(messages):
    calls, receipts = {}, []
    for message in messages:
        for call in message.get('tool_calls') or []:
            function = call['function']
            try:
                args = json.loads(function.get('arguments') or '{}')
            except (ValueError, TypeError):
                args = {'unparsed_arguments': function.get('arguments')}
            calls[call['id']] = {'call_id': call['id'], 'tool': function['name'], 'arguments': args}
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
                                      'record_names': [row.get('name') for row in data.get('records', [])],
                                      'warnings': data.get('warnings', [])}
            elif name == 'aggregate_documents' and isinstance(data, dict):
                receipt['summary'] = {key: data.get(key) for key in ('doctype', 'count', 'complete', 'groups', 'consistency')}
            elif name == 'get_document' and isinstance(data, dict):
                receipt['summary'] = {key: data[key] for key in ('doctype', 'name', 'docstatus') if key in data}
            elif name == 'get_doctype_meta' and isinstance(data, dict):
                receipt['summary'] = {'doctype': data.get('doctype'),
                                      'schemas': [doc.get('name') for doc in data.get('docs', [])]}
            elif name == 'prepare_purchase_order' and isinstance(data, dict):
                receipt['summary'] = {key: data.get(key) for key in ('proposal_id', 'estimated_total', 'requires_confirmation')}
            else:
                receipt['summary'] = data
        receipts.append(receipt)
    return receipts
