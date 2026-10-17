"""Built-in tool catalog: schema and handler are registered together."""
from dataclasses import dataclass
from tool_registry import ToolRegistry
from query_policy import normalize_filters, validate_fields


@dataclass(frozen=True)
class ToolContext:
    agent: object
    calculate: object
    has_child_join: object


BUILTIN_TOOLS = ToolRegistry()


@BUILTIN_TOOLS.tool({'type': 'function',
 'function': {'name': 'get_doctype_meta',
              'description': 'Discover fields and child tables for an ERPNext DocType.',
              'parameters': {'type': 'object',
                             'properties': {'doctype': {'type': 'string'}},
                             'required': ['doctype']}}})
def get_doctype_meta(context, args):
    return context.agent.c.meta(args['doctype'])


@BUILTIN_TOOLS.tool({'type': 'function',
 'function': {'name': 'count_documents',
              'description': 'Count distinct documents with ERPNext filters. Explicit child-table '
                             'filters use a complete bounded scan of at most 10000 matching raw rows to '
                             'avoid counting a parent twice; narrow the query if the limit is exceeded.',
              'parameters': {'type': 'object',
                             'properties': {'doctype': {'type': 'string'},
                                            'filters': {'type': 'array',
                                                        'description': 'AND conditions, e.g. [[field, '
                                                                       'operator, value]]. A '
                                                                       'four-element condition may '
                                                                       'start with DocType.',
                                                        'items': {'type': 'array',
                                                                  'minItems': 3,
                                                                  'maxItems': 4,
                                                                  'items': {}}}},
                             'required': ['doctype']}}})
def count_documents(context, args):
    if context.has_child_join(args['doctype'], args.get('filters')):
        return context.agent.c.aggregate(args['doctype'], args.get('filters'))['count']
    return context.agent.c.count(args['doctype'], args.get('filters'))


@BUILTIN_TOOLS.tool({'type': 'function',
 'function': {'name': 'list_documents',
              'description': 'List ERPNext documents with plain fields, filters, pagination and field '
                             'ordering. No SQL expressions, aliases or wildcard fields; use '
                             'aggregate_documents for sums and get_document for full named details. '
                             'For invoice overdue questions set assess_due_date=true for program '
                             'reference_date_evidence; include '
                             'due_date and outstanding_amount to assess overdue, keeping raw status separate.',
              'parameters': {'type': 'object',
                             'properties': {'doctype': {'type': 'string'},
                                            'fields': {'type': 'array',
                                                       'minItems': 1,
                                                       'maxItems': 50,
                                                       'items': {'type': 'string'}},
                                            'filters': {'type': 'array',
                                                        'description': 'AND conditions, e.g. [[field, '
                                                                       'operator, value]]. A '
                                                                       'four-element condition may '
                                                                       'start with DocType.',
                                                        'items': {'type': 'array',
                                                                  'minItems': 3,
                                                                  'maxItems': 4,
                                                                  'items': {}}},
                                            'limit': {'type': 'integer'},
                                            'offset': {'type': 'integer'},
                                            'include_total': {'type': 'boolean',
                                                              'description': 'Default true. Set false for bounded candidate shortlisting to skip the extra count HTTP request. Total and has_more then remain unknown; never claim complete coverage.'},
                                            'order_by': {'type': 'string',
                                                         'description': 'At most three plain field '
                                                                        'names with optional asc/desc, '
                                                                        'e.g. modified desc, name '
                                                                        'asc.'},
                                            'assess_due_date': {'type': 'boolean',
                                                                'description': 'Default false. Enable only for invoice due-date/overdue questions; computes local date evidence from returned fields without extra ERP reads. Leave false for current-balance-only requests.'}},
                             'required': ['doctype']}}})
def list_documents(context, args):
    limit = max(1, min(int(args.get('limit', 20)), 100))
    offset = max(0, int(args.get('offset', 0)))
    fields = args.get('fields')
    validate_fields(fields)
    if fields:
        fields = list(dict.fromkeys(['name'] + fields))
    rows = context.agent.c.list(args['doctype'], fields, args.get('filters'), limit, offset, args.get('order_by') or 'name asc')
    total = context.agent.c.count(args['doctype'], args.get('filters')) if args.get('include_total', True) else None
    joined = context.has_child_join(args['doctype'], args.get('filters'))
    has_more = offset + len(rows) < total if total is not None else None
    occurrences = {}
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get('name'), str):
            occurrences[row['name']] = occurrences.get(row['name'], 0) + 1
    duplicate_names = [document for document, count in occurrences.items() if count > 1]
    warnings = []
    if total is None:
        warnings.append('Candidate page only: total count was deliberately not queried to save an HTTP request. has_more is unknown; no complete coverage or full-category total is established. next_offset is only a possible continuation.')
    if joined:
        warnings.append('Child-table join filters may repeat parent documents. pagination.total, offset, returned and next_offset refer to raw joined rows, not distinct documents. Use count_documents or aggregate_documents for distinct parent counts. Do not sum repeated parent amounts or silently drop matching child rows.')
    elif duplicate_names:
        warnings.append('Duplicate document names appeared without an explicit child-join filter; the page may overlap or be unstable. Do not use it as a complete total.')
    if rows and args.get('fields') and any((field not in rows[0] for field in args['fields'])):
        warnings.append('Requested fields are missing; child DocTypes may return only names. Read parent documents; do not assume missing values are zero.')
    if args['doctype'] == 'Bin':
        warnings.append('CURRENT SNAPSHOT ONLY: warehouse is a location label, not evidence of a completed issue/transfer/receipt. Do not describe material as already issued or transferred without Stock Entry/Stock Ledger event evidence. projected_qty is returned by ERP; its formula cannot be inferred from a subset of planning fields.')
    return {'records': rows, 'pagination': {'offset': offset, 'limit': limit, 'returned': len(rows), 'total': total, 'total_basis': 'not_queried' if total is None else ('raw_join_rows' if joined else 'documents'), 'unique_names_returned': len(occurrences), 'duplicate_names': duplicate_names, 'has_more': has_more, 'next_offset': offset + len(rows) if rows and (has_more or total is None) else None}, 'query_scope': {'doctype': args['doctype'], 'filters': normalize_filters(args.get('filters')), 'fields': fields or ['name'], 'coverage': 'Coverage is limited to these exact filters. Name/keyword matches are search candidates, not proof of every member of a business category. Only returned field values are established; historical events and causes require separate evidence.'}, 'warnings': warnings}


@BUILTIN_TOOLS.tool({'type': 'function',
 'function': {'name': 'get_document',
              'description': 'Read one ERPNext document by DocType and name, including child tables. '
                             'For invoice overdue questions set assess_due_date=true for program '
                             'reference_date_evidence beside unchanged data; use it, not raw ERP status.',
              'parameters': {'type': 'object',
                             'properties': {'doctype': {'type': 'string'}, 'name': {'type': 'string'},
                                            'assess_due_date': {'type': 'boolean',
                                                                'description': 'Default false. Enable only for invoice due-date/overdue questions; leave false for balance-only requests. No extra ERP read.'}},
                             'required': ['doctype', 'name']}}})
def get_document(context, args):
    return context.agent.c.get(args['doctype'], args['name'])


@BUILTIN_TOOLS.tool({'type': 'function',
 'function': {'name': 'get_documents',
              'description': 'Read 1 to 20 named parent documents of one DocType, including child '
                             'tables. Names are deduplicated in input order. Returns per-document '
                             'success or error; complete is true only when every requested document '
                             'succeeded. Never use partial results as a complete total. Completeness '
                             'covers these names only, not all records matching a business question. '
                             'Read-only; no joins, writes or retries. This is NOT a server batch API: '
                             'each uncached name requires its own upstream HTTP request. Shortlist first. '
                             'For invoice overdue questions set assess_due_date=true for separate '
                             'program reference_date_evidence on successful records.',
              'parameters': {'type': 'object',
                             'properties': {'doctype': {'type': 'string', 'minLength': 1},
                                            'assess_due_date': {'type': 'boolean',
                                                                'description': 'Default false. Enable only for invoice due-date/overdue questions; leave false for balance-only requests. No extra ERP read.'},
                                            'names': {'type': 'array',
                                                      'minItems': 1,
                                                      'maxItems': 20,
                                                      'items': {'type': 'string', 'minLength': 1}}},
                             'required': ['doctype', 'names'],
                             'additionalProperties': False}}})
def get_documents(context, args):
    return context.agent.c.get_many(args['doctype'], args['names'])


@BUILTIN_TOOLS.tool({'type': 'function',
 'function': {'name': 'prepare_purchase_order',
              'description': 'Validate and preview a Purchase Order. Explicit quote currency is '
                             'required and must match company base currency; never silently reinterpret '
                             'or convert a foreign quote. Never creates it; returns a proposal '
                             'requiring explicit user /confirm. local_state=pending describes only '
                             'the local proposal; doc.docstatus is a prospective value and '
                             'erp_document=null means no ERP document was created by this preview.',
              'parameters': {'type': 'object',
                             'properties': {'supplier': {'type': 'string'},
                                            'item': {'type': 'string'},
                                            'qty': {'type': 'number'},
                                            'uom': {'type': 'string'},
                                            'rate': {'type': 'number'},
                                            'currency': {'type': 'string',
                                                         'description': 'Currency code of the agreed '
                                                                        'unit price, e.g. USD. Must be '
                                                                        'explicitly supplied; foreign '
                                                                        'quotes are rejected.'},
                                            'transaction_date': {'type': 'string'},
                                            'schedule_date': {'type': 'string'},
                                            'company': {'type': 'string',
                                                        'description': 'Exact company name; required if '
                                                                       'multiple companies exist'}},
                             'required': ['supplier', 'item', 'qty', 'uom', 'rate', 'currency']}}}, effect='prepare', decimal_arguments=True)
def prepare_purchase_order(context, args):
    if not isinstance(args.get('currency'), str) or not args['currency'].strip():
        raise ValueError('An explicit quote currency is required for the purchase preview')
    return context.agent.proposal_po(**args)


@BUILTIN_TOOLS.tool({'type': 'function',
 'function': {'name': 'aggregate_documents',
              'description': 'Complete bounded scan with stable pagination and Decimal sums/grouped '
                             'counts per distinct parent name. Explicit child-join duplicates are '
                             'folded only when parent projections agree; count differs from '
                             'matched_rows. Use for totals and rankings; incomplete/conflicting scans '
                             'fail. Group money by currency/company; do not mix units. Read parent '
                             'details for child-row amounts.',
              'parameters': {'type': 'object',
                             'properties': {'doctype': {'type': 'string'},
                                            'filters': {'type': 'array',
                                                        'items': {'type': 'array',
                                                                  'minItems': 3,
                                                                  'maxItems': 4,
                                                                  'items': {}}},
                                            'group_by': {'type': 'array', 'items': {'type': 'string'}},
                                            'sum_fields': {'type': 'array',
                                                           'items': {'type': 'string'}}},
                             'required': ['doctype']}}})
def aggregate_documents(context, args):
    return context.agent.c.aggregate(args['doctype'], args.get('filters'), args.get('group_by'), args.get('sum_fields'))


@BUILTIN_TOOLS.tool({'type': 'function',
 'function': {'name': 'calculate',
              'description': 'Calculate differences, percentages, margins and other arithmetic from '
                             'verified tool data using Decimal. No arbitrary code or ERP access.',
              'parameters': {'type': 'object',
                             'properties': {'expression': {'type': 'string'}},
                             'required': ['expression']}}})
def calculate(context, args):
    return context.calculate(args['expression'])
