"""Narrow evidence checks for known claim types; not a general truth verifier."""
import json
import re
from decimal import Decimal, InvalidOperation
from tool_receipts import tool_receipts


MOVEMENT = re.compile(
    r'已(?:经)?(?:发到|发往|发料|领料|领用|转入|转到|转移)|'
    r'\b(?:already|was|were|has been|have been)\s+(?:issued|transferred)\b', re.I)
QUALIFIED = re.compile(
    r'不代表|不能(?:证明|断定|推断|认定|说明)|无法(?:证明|断定|推断|认定)|'
    r'未(?:能)?(?:证明|核实|确认)|没有.{0,12}证据|尚无.{0,12}证据|'
    r'不确定|尚不清楚|'
    r'cannot\s+(?:prove|infer|conclude)|not\s+(?:proof|evidence)|no\s+evidence|'
    r'\b(?:unverified|unconfirmed|uncertain|unknown)\b|'
    r'not\s+(?:been\s+)?(?:verified|confirmed|established)', re.I)
QUESTION = re.compile(r'是否|有无|有没有|\bwhether\b', re.I)

# Currency is checked only when an answer makes an explicit amount claim. A
# number without a currency remains outside this narrow check. Symbols map to
# one unambiguous code; ¥ is deliberately omitted because it can mean CNY or
# JPY. This is an evidence boundary, not a currency conversion or fact proof.
CURRENCY_AMOUNT = re.compile(
    r'(?P<left>\b(?:USD|EUR|GBP|CNY|RMB|JPY|HKD|AUD|CAD)\s*[-+]?\d[\d,]*(?:\.\d+)?|'
    r'(?P<symbol>[$€£])\s*[-+]?\d[\d,]*(?:\.\d+)?|'
    r'[-+]?\d[\d,]*(?:\.\d+)?\s*(?P<right>USD|EUR|GBP|CNY|RMB|JPY|HKD|AUD|CAD)\b)', re.I)
SYMBOL_CURRENCY = {'$': 'USD', '€': 'EUR', '£': 'GBP'}


def _currency_values(messages):
    """Return currency codes actually present in successful tool payloads."""
    values = set()

    def visit(value, key=None):
        if isinstance(value, dict):
            for name, child in value.items():
                if (name == 'currency' or name == 'default_currency'
                        or name.endswith('_currency')) and isinstance(child, str):
                    values.add(child.strip().upper())
                visit(child, name)
        elif isinstance(value, list):
            for child in value:
                visit(child, key)

    for message in messages:
        if message.get('role') != 'tool':
            continue
        try:
            payload = json.loads(message.get('content', '{}'))
        except (ValueError, TypeError):
            continue
        if payload.get('ok'):
            visit(payload.get('data'))
    return values


def _current_turn_messages(messages):
    """Exclude unrelated prior turns while retaining the current tool round."""
    if not isinstance(messages, list):
        return messages
    for index in range(len(messages) - 1, -1, -1):
        message = messages[index]
        if (message.get('role') == 'user'
                and not (message.get('content') or '').startswith('[PROGRAM EVIDENCE CHECK')):
            return messages[index:]
    return messages


def _currency_issues(answer, messages):
    observed = _currency_values(_current_turn_messages(messages))
    for sentence in re.split(r'\n|(?<=[。！？!?])|(?<=[.!?])\s+', answer):
        for match in CURRENCY_AMOUNT.finditer(sentence):
            token = (match.group('left') or match.group('right') or '').upper()
            symbol = match.group('symbol')
            if symbol:
                claimed = SYMBOL_CURRENCY[symbol]
            elif match.group('right'):
                claimed = match.group('right').upper()
            else:
                claimed = token.split()[0]
            prefix = sentence[max(0, match.start()-48):match.start()]
            suffix = sentence[match.end():match.end()+96]
            if QUALIFIED.search(prefix) or QUALIFIED.search(suffix):
                continue
            if claimed not in observed:
                scope = ', '.join(sorted(observed)) if observed else 'no currency field'
                return ['An explicit currency amount was stated without matching currency evidence '
                        f'(claimed {claimed}; observed {scope}). Preserve the returned amount but '
                        'omit the currency claim or query a source that returns currency; do not '
                        'infer a currency from company, locale, symbol or an unrelated document.']
    return []


def _first_decimal(text):
    match = re.search(r'[-+]?\d[\d,]*(?:\.\d+)?', text or '')
    if not match:
        return None
    try:
        return Decimal(match.group(0).replace(',', ''))
    except InvalidOperation:
        return None


def _shortage_table_issues(answer):
    """Catch an internally contradictory shortage column before final acceptance."""
    lines = [line.strip() for line in answer.splitlines() if '|' in line]
    for index, header in enumerate(lines):
        cells = [cell.strip() for cell in header.strip('|').split('|')]
        lowered = [cell.lower() for cell in cells]
        shortage = next((i for i, cell in enumerate(lowered)
                         if '缺口' in cell or 'shortage' in cell or 'shortfall' in cell), None)
        required = next((i for i, cell in enumerate(lowered)
                         if '需求' in cell or 'required' in cell or 'need' in cell), None)
        actual = next((i for i, cell in enumerate(lowered)
                       if '实际库存' in cell or 'actual_qty' in cell or 'available' in cell), None)
        required_unit = next((i for i, cell in enumerate(lowered)
                              if '需求单位' in cell or 'required_uom' in cell or 'required uom' in cell
                              or 'required unit' in cell), None)
        actual_unit = next((i for i, cell in enumerate(lowered)
                            if '库存单位' in cell or '实际单位' in cell or 'actual_uom' in cell
                            or 'actual uom' in cell or 'available_uom' in cell
                            or 'available uom' in cell or 'available unit' in cell), None)
        if shortage is None or required is None or actual is None:
            continue
        if index + 1 < len(lines) and all(re.fullmatch(r':?-{2,}:?', cell.replace(' ', ''))
                                          for cell in [c.strip() for c in lines[index + 1].strip('|').split('|')]):
            rows = lines[index + 2:]
        else:
            rows = lines[index + 1:]
        for row in rows:
            row_cells = [cell.strip() for cell in row.strip('|').split('|')]
            if len(row_cells) <= max(shortage, required, actual):
                continue
            if (required_unit is not None and actual_unit is not None
                    and max(required_unit, actual_unit) < len(row_cells)
                    and row_cells[required_unit].strip().lower() != row_cells[actual_unit].strip().lower()):
                return ['The shortage table mixes requirement and available quantities with different units. '
                        'Do not calculate a shortage across UOMs; convert with verified ERP evidence or '
                        'report the two unit values separately. WIP, reserved and projected quantities '
                        'are not interchangeable with actual available stock.']
            if not any(re.search(r'\d', cell) for cell in row_cells):
                continue
            need, have = _first_decimal(row_cells[required]), _first_decimal(row_cells[actual])
            reported = _first_decimal(row_cells[shortage])
            if need is None or have is None or reported is None:
                continue
            expected = max(need - have, Decimal(0))
            if reported != expected:
                return ['The shortage table is internally inconsistent: for rows with required/actual '
                        'quantities, the shortage column must equal max(required - actual, 0). '
                        'When actual exceeds required, write shortage=0 and put the surplus in a separate '
                        'surplus/余量 column; do not put a positive surplus inside the shortage column.']
    return []


def _has_event_records(receipt):
    """A nonempty read is not proof the event supports the answer's claim."""
    summary = receipt.get('summary')
    if not isinstance(summary, dict):
        return False
    if receipt['tool'] == 'list_documents':
        return any(summary.get('record_names') or [])
    if receipt['tool'] == 'get_document':
        return bool(summary.get('name'))
    if receipt['tool'] == 'get_documents':
        return any(summary.get('record_names') or [])
    if receipt['tool'] == 'aggregate_documents':
        count = summary.get('count')
        return summary.get('complete') is True and type(count) in (int, float) and count > 0
    return False


def evidence_issues(answer, messages):
    """Detect unsupported stock-movement wording when only snapshots were read.

    Nonempty event reads permit a claim to proceed for normal model/manual
    review; this does not prove relevance or verify arbitrary sentences.
    It never performs ERP operations and never rewrites an answer silently.
    """
    receipts = [r for r in tool_receipts(messages)
                if r['status'] == 'ok' and r['tool'] in {'list_documents', 'get_document', 'get_documents', 'aggregate_documents'}]
    currency_issue = _currency_issues(answer, messages)
    shortage_issue = _shortage_table_issues(answer)
    reads = {r.get('arguments', {}).get('doctype') for r in receipts}
    has_events = any(r.get('arguments', {}).get('doctype') in {'Stock Entry', 'Stock Ledger Entry'}
                     and _has_event_records(r) for r in receipts)
    if 'Bin' not in reads or has_events:
        return currency_issue + shortage_issue
    # Preserve question endings and split English sentence boundaries too, so
    # a later sentence's uncertainty cannot qualify an earlier assertion.
    for sentence in re.split(r'\n|(?<=[。！？!?])|(?<=[.!?])\s+', answer):
        for match in MOVEMENT.finditer(sentence):
            prefix = sentence[max(0, match.start()-40):match.start()]
            suffix = sentence[match.end():match.end()+80]
            if (QUALIFIED.search(prefix) or QUALIFIED.search(suffix)
                    or QUESTION.search(prefix) or sentence.rstrip().endswith(('?', '？'))):
                continue
            return currency_issue + shortage_issue + ['Stock movement asserted from a Bin snapshot without Stock Entry/Stock Ledger event evidence. '
                    'If the user asks only about current stock, report snapshot quantities and locations and remove '
                    'the unrequested historical assertion rather than researching unrelated movements to justify it. '
                    'If the user explicitly asks about issue/transfer history, read relevant Stock Entry/Stock Ledger '
                    'events or state that history is unverified; never infer it from a warehouse label. '
                    'Omit unrequested projection formulas; if arithmetic is necessary, use calculate.']
    return currency_issue + shortage_issue
