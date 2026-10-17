"""Small, turn-preserving context budget for the synchronous CLI runner."""
from __future__ import annotations

import copy
import json
from decimal import Decimal


SUMMARY_MARKER = '[HISTORICAL TOOL EVIDENCE SUMMARY — NOT CURRENT STATE]'


def _message_size(messages):
    return len(json.dumps(messages, ensure_ascii=False, default=str).encode('utf-8'))


def _safe_scalar(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Decimal):
        return str(value)
    return str(value)[:200]


def _important_record(record):
    if not isinstance(record, dict):
        return record
    keys = ('name', 'doctype', 'item_code', 'item_name', 'warehouse', 'stock_uom',
            'uom', 'qty', 'actual_qty', 'ordered_qty', 'reserved_qty',
            'reserved_qty_for_production', 'currency', 'amount', 'grand_total',
            'supplier', 'company', 'status', 'docstatus', 'transaction_date',
            'schedule_date', 'proposal_id')
    return {key: _safe_scalar(record[key]) for key in keys if key in record}


def _tool_summary(call, result):
    """Make a compact, explicitly stale summary without retaining arbitrary ERP text."""
    function = call.get('function', {}) if isinstance(call, dict) else {}
    name = function.get('name', 'unknown')
    try:
        args = json.loads(function.get('arguments') or '{}', parse_float=str)
    except (ValueError, TypeError):
        args = {'unparsed_arguments': str(function.get('arguments', ''))[:300]}
    summary = {'tool': name, 'arguments': args}
    try:
        payload = json.loads(result.get('content', '{}'))
    except (ValueError, TypeError, AttributeError):
        payload = {'ok': False, 'error': 'unparseable prior tool result'}
    summary['ok'] = bool(payload.get('ok'))
    if not summary['ok']:
        summary['error'] = str(payload.get('error', 'unknown error'))[:240]
        return summary
    data = payload.get('data')
    if name == 'count_documents' or name == 'calculate':
        summary['data'] = data
    elif name == 'get_document' and isinstance(data, dict):
        summary['data'] = _important_record(data)
    elif name == 'get_documents' and isinstance(data, dict):
        summary['data'] = {key: data.get(key) for key in
                           ('doctype', 'requested_names', 'success_count', 'error_count', 'complete')}
        summary['data']['results'] = [
            {'name': row.get('name'), 'ok': row.get('ok'),
             'data': _important_record(row.get('data')) if row.get('ok') else None,
             'error': str(row.get('error'))[:240] if not row.get('ok') else None}
            for row in (data.get('results') or [])[:20]
        ]
    elif name == 'list_documents' and isinstance(data, dict):
        summary['data'] = {
            'query_scope': data.get('query_scope'),
            'pagination': data.get('pagination'),
            'records': [_important_record(row) for row in (data.get('records') or [])[:20]],
            'warnings': data.get('warnings', []),
        }
    elif name == 'aggregate_documents' and isinstance(data, dict):
        summary['data'] = {key: data.get(key) for key in
                           ('doctype', 'count', 'matched_rows', 'duplicates_collapsed', 'complete', 'groups')}
    elif name == 'prepare_purchase_order' and isinstance(data, dict):
        summary['data'] = {key: data.get(key) for key in
                           ('proposal_id', 'idempotency_key', 'estimated_total', 'requires_confirmation', 'doc')}
    elif isinstance(data, dict):
        summary['data'] = _important_record(data)
    else:
        summary['data'] = _safe_scalar(data)
    io = payload.get('io')
    if isinstance(io, dict):
        sources = io.get('sources') or []
        summary['evidence'] = [{key: source.get(key) for key in
                                ('source', 'path', 'fetched_at', 'age_seconds')}
                               for source in sources[:8] if isinstance(source, dict)]
    summary['freshness'] = 'historical observation; re-query current state before relying on it'
    return summary


def _group_messages(messages):
    systems, turns, current = [], [], []
    for message in messages:
        if message.get('role') == 'system':
            if current:
                turns.append(current)
                current = []
            systems.append(message)
        elif message.get('role') == 'user':
            if (current and isinstance(message.get('content'), str)
                    and message['content'].startswith('[PROGRAM EVIDENCE CHECK')):
                current.append(message)
                continue
            if current:
                turns.append(current)
            current = [message]
        else:
            if not current:
                current = [message]
            else:
                current.append(message)
    if current:
        turns.append(current)
    return systems, turns


def _summary_for_turn(turn):
    users = [message.get('content', '') for message in turn if message.get('role') == 'user']
    calls = [message for message in turn if message.get('role') == 'assistant' and message.get('tool_calls')]
    results = {message.get('tool_call_id'): message for message in turn if message.get('role') == 'tool'}
    summaries = []
    for call in calls:
        for tool_call in call.get('tool_calls') or []:
            summaries.append(_tool_summary(tool_call, results.get(tool_call.get('id'), {})))
    answer = next((message.get('content') for message in reversed(turn)
                   if message.get('role') == 'assistant' and message.get('content')), None)
    body = {'user_request': users[-1] if users else '', 'tool_evidence': summaries}
    if answer:
        body['assistant_answer'] = str(answer)[:1200]
    return SUMMARY_MARKER + '\n' + json.dumps(body, ensure_ascii=False, default=str)


def _complete_turn(turn):
    call_ids = {tool_call.get('id') for message in turn
                if message.get('role') == 'assistant'
                for tool_call in (message.get('tool_calls') or [])}
    result_ids = {message.get('tool_call_id') for message in turn if message.get('role') == 'tool'}
    return call_ids == result_ids


def compact_messages(messages, max_bytes):
    """Keep complete turns; archive old tool details as stale evidence summaries."""
    if not isinstance(messages, list) or max_bytes <= 0:
        return copy.deepcopy(messages), {'trimmed': False, 'bytes': _message_size(messages), 'over_budget': False}
    systems, turns = _group_messages(messages)
    prior_summaries = [message.get('content', '') for message in systems
                       if isinstance(message.get('content'), str)
                       and message['content'].startswith(SUMMARY_MARKER)]
    systems = [message for message in systems if message not in
               [item for item in systems if isinstance(item.get('content'), str)
                and item['content'].startswith(SUMMARY_MARKER)]]
    prior_summary = '\n\n'.join(prior_summaries)
    prior_messages = ([{'role': 'system', 'content': prior_summary}] if prior_summary else [])
    candidate = systems + prior_messages + [message for turn in turns for message in turn]
    if _message_size(candidate) <= max_bytes:
        return copy.deepcopy(candidate), {'trimmed': False, 'bytes': _message_size(candidate), 'over_budget': False}
    # The current/latest turn is never split. Retain as many complete recent turns
    # as fit, while preserving an explicit source-marked summary for discarded ones.
    latest = turns[-1:] if turns else []
    kept = []
    removed = []
    for turn in reversed(turns[:-1]):
        if not _complete_turn(turn):
            removed.append(turn)
            continue
        trial = systems + [message for old_turn in list(reversed(kept + [turn])) + latest
                           for message in old_turn]
        if _message_size(trial) <= max_bytes:
            kept.append(turn)
        else:
            removed.append(turn)
    kept = list(reversed(kept))
    summary_messages = []
    if removed:
        summaries = [_summary_for_turn(turn) for turn in reversed(removed)]
        summary_messages = [{'role': 'system', 'content': '\n\n'.join(summaries)[:8000]}]
    base = systems + [message for old_turn in kept + latest for message in old_turn]
    summary_text = '\n\n'.join(item for item in
                               [prior_summary] + [message['content'] for message in summary_messages]
                               if item)
    summary_messages = []
    if summary_text:
        remaining = max_bytes - _message_size(base)
        if remaining > 120:
            summary_messages = [{'role': 'system', 'content': summary_text[:remaining]}]
        elif remaining > 0:
            summary_messages = [{'role': 'system', 'content':
                                 SUMMARY_MARKER + ' Earlier evidence was compacted; re-query before relying on it.'[:remaining]}]
    result = systems + summary_messages + [message for old_turn in kept + latest
                                           for message in old_turn]
    size = _message_size(result)
    return copy.deepcopy(result), {'trimmed': bool(removed), 'bytes': size,
                                   'over_budget': size > max_bytes,
                                   'removed_turns': len(removed),
                                   'preserved_turns': len(kept) + len(latest)}
