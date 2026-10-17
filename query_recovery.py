"""Avoid repeating a field projection already observed to fail in this turn."""
import json
from query_policy import normalize_filters


def projection_failure(messages, tool, args):
    if tool != 'aggregate_documents':
        return None
    required = set(args.get('group_by') or []) | set(args.get('sum_fields') or [])
    for message in reversed(messages):
        if message.get('role') != 'tool':
            continue
        try:
            payload = json.loads(message.get('content', '{}'))
        except (TypeError, ValueError):
            continue
        data = payload.get('data') or {}
        scope = data.get('query_scope') if isinstance(data, dict) else None
        if (not payload.get('ok') or not scope or scope.get('doctype') != args.get('doctype')
                or scope.get('filters') != normalize_filters(args.get('filters'))):
            continue
        rows = data.get('records') or []
        requested = set(scope.get('fields') or []) & required
        missing = {field for field in requested if any(field not in row for row in rows)}
        if rows and missing:
            return ('No ERP request sent: this turn already observed missing projected fields '
                    + ', '.join(sorted(missing)) + ' for the same DocType/filters. '
                    'Do not repeat the unavailable projection through aggregation. Discover the '
                    'parent Table relationship with metadata; filter the parent endpoint with '
                    '[Child DocType, child_field, operator, value] plus parent date/docstatus filters. '
                    'Page all matching parent names, deduplicate them, then read only those parents '
                    'and verify child rows, currency, units and completeness.')
    return None
