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
CURRENCY_CODES = r'USD|EUR|GBP|CNY|RMB|JPY|HKD|AUD|CAD|美元|欧元|英镑|人民币|日元|港币|澳元|加元'
CURRENCY_ALIASES = {'美元': 'USD', '欧元': 'EUR', '英镑': 'GBP', '人民币': 'CNY',
                    '日元': 'JPY', '港币': 'HKD', '澳元': 'AUD', '加元': 'CAD', 'RMB': 'CNY'}
CURRENCY_AMOUNT = re.compile(
    rf'(?P<left>(?<![A-Za-z])(?:{CURRENCY_CODES})\s*[-+]?\d[\d,]*(?:\.\d+)?|'
    r'(?P<symbol>[$€£])\s*[-+]?\d[\d,]*(?:\.\d+)?|'
    rf'[-+]?\d[\d,]*(?:\.\d+)?\s*(?P<right>{CURRENCY_CODES})(?![A-Za-z]))', re.I)
SYMBOL_CURRENCY = {'$': 'USD', '€': 'EUR', '£': 'GBP'}
USER_BASIS = re.compile(r'(?:用户|您|你)(?:提供|给出|给定|输入|报价|口述|所述|的报价|的条件|陈述)|'
                        r'来自(?:用户|您|你)|'
                        r'(?:按|根据)(?:用户|您|你)|'
                        r'来源[:：]\s*用户|\bsource:\s*user|'
                        r'\buser[ -](?:provided|supplied|input|quote)|\byour\s+(?:quote|price|input)|'
                        r'\b(?:provided|quoted)\s+by\s+(?:you|the user)\b', re.I)
ERP_BASIS = re.compile(r'ERP|系统记录|系统返回|系统显示|工具返回', re.I)
DERIVED = re.compile(r'计算|测算|推导|合计|总额|总价|估算|\b(?:calculated|computed|total|estimate)\b', re.I)
EARLIER_SOURCE = re.compile(r'上一轮|此前|之前|早先|\b(?:previous|earlier)\b', re.I)


def _currency_values(messages):
    """Return currency codes actually present in successful tool payloads."""
    values = set()

    def visit(value, key=None):
        if isinstance(value, dict):
            for name, child in value.items():
                if (name == 'currency' or name == 'default_currency'
                        or name.endswith('_currency')) and isinstance(child, str):
                    code = child.strip().upper()
                    values.add(CURRENCY_ALIASES.get(code, code))
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


def _currency_claim(match):
    if match.group('symbol'):
        code = SYMBOL_CURRENCY[match.group('symbol')]
    else:
        token = re.search(CURRENCY_CODES, match.group(), re.I).group().upper()
        code = CURRENCY_ALIASES.get(token, token)
    return code, _first_decimal(match.group())


def _user_calculation_supported(code, amount, quotes, calculations):
    # Narrow provenance check, not dimensional analysis or a general proof.
    # Mixed-currency expressions need explicit conversion evidence, not this
    # exception. A result alone cannot establish which currency it represents.
    if {currency for currency, _ in quotes} != {code}:
        return False
    inputs = {number for _, number in quotes}
    for data in calculations:
        if _first_decimal(str(data.get('result', ''))) != amount:
            continue
        operands = {Decimal(number) for number in re.findall(
            r'(?<![\w.])\d+(?:\.\d+)?(?:[eE][-+]?\d+)?', str(data.get('expression', '')))}
        if inputs & operands:
            return True
    return False


def _quoted_amounts(messages):
    return {_currency_claim(match) for message in messages if message.get('role') == 'user'
            and not (message.get('content') or '').startswith('[PROGRAM EVIDENCE CHECK')
            for match in CURRENCY_AMOUNT.finditer(message.get('content') or '')}


def _currency_answer_sentences(answer):
    """Carry explicit Markdown section attribution to following amount rows.

    A user-quote section is not an ERP currency receipt. Every amount still
    needs an exact current/labelled-prior user quote or a matching calculation.
    Unrelated sections reset attribution rather than leaking it indefinitely.
    """
    section = None
    for line in answer.splitlines():
        stripped = line.strip()
        heading = re.fullmatch(r'\*\*(.+)\*\*', stripped)
        if heading is None:
            heading = re.fullmatch(r'#{1,6}\s+(.+)', stripped)
        if heading:
            label = heading.group(1)
            if USER_BASIS.search(label):
                section = 'user'
            elif (DERIVED.search(label)
                  and re.search(r'金额|总额|总价|小计|合计|费用|price|total|amount', label, re.I)):
                section = 'derived'
            else:
                section = None
        for sentence in re.split(r'[；;]|(?<=[。！？!?])|(?<=[.!?])\s+', line):
            yield sentence, section


def _currency_issues(answer, messages):
    current = _current_turn_messages(messages)
    observed = _currency_values(current)
    quotes = _quoted_amounts(current)
    earlier_quotes = _quoted_amounts(messages[:len(messages) - len(current)])
    calculations = []
    prepared_totals = set()
    for receipt in tool_receipts(current):
        if receipt['status'] == 'ok' and receipt['tool'] in {'calculate', 'prepare_purchase_order'}:
            # Receipt summaries deliberately omit detail; use the paired body.
            body = next((m for m in current if m.get('role') == 'tool'
                         and m.get('tool_call_id') == receipt['call_id']), None)
            if body:
                data = json.loads(body['content']).get('data', {})
                if receipt['tool'] == 'calculate':
                    calculations.append(data)
                else:
                    # The unchanged preview handler computes this Decimal total.
                    # It is a local program result, not an ERP document fact.
                    doc = data.get('doc', {})
                    code = doc.get('currency')
                    if any((code, _first_decimal(str(item.get('rate', '')))) in quotes | earlier_quotes
                           for item in doc.get('items', [])):
                        prepared_totals.add((code, _first_decimal(str(data.get('estimated_total', '')))))
    for sentence, section in _currency_answer_sentences(answer):
        for match in CURRENCY_AMOUNT.finditer(sentence):
            claimed, amount = _currency_claim(match)
            prefix = sentence[max(0, match.start()-48):match.start()]
            suffix = sentence[match.end():match.end()+96]
            if QUALIFIED.search(prefix) or QUALIFIED.search(suffix):
                continue
            attribution = re.sub(r'(?:非|不是|并非|未经|未由|not\s+(?:from\s+|verified\s+by\s+)?)ERP',
                                 '', sentence, flags=re.I)
            if (USER_BASIS.search(sentence) or section in {'user', 'derived'}) and not ERP_BASIS.search(attribution):
                source_quotes = earlier_quotes if EARLIER_SOURCE.search(sentence) else quotes
                # A direct quoted price must match actual user input; a derived
                # total must also match a successful current-turn calculation.
                # Merely placing an unrelated number under a user heading is
                # not evidence, nor can an explicit ERP claim borrow the heading.
                direct_quote = ((USER_BASIS.search(sentence) or section == 'user')
                                and (claimed, amount) in source_quotes)
                computed = ((DERIVED.search(sentence) or section == 'derived')
                            and _user_calculation_supported(claimed, amount,
                                                            source_quotes, calculations))
                if direct_quote or computed or (claimed, amount) in prepared_totals:
                    continue
                return ['A user-sourced currency amount does not match the current (or explicitly '
                        'labelled earlier) user input or '
                        'a successful calculate result using that input. Preserve the explicit user '
                        'quote, label its source as user, and calculate requested totals; do not '
                        'relabel it as ERP-verified or silently convert currencies.']
            if claimed not in observed:
                scope = ', '.join(sorted(observed)) if observed else 'no currency field'
                return ['An explicit currency amount was stated without matching currency evidence '
                        f'(claimed {claimed}; observed {scope}). Preserve the returned amount but '
                        'omit the currency claim or query a source that returns currency; do not '
                        'infer a currency from company, locale, symbol or an unrelated document. '
                        'Explicit user quotes are valid user-provided conditions, not ERP facts: '
                        'attribute them to the user and use calculate for derived amounts, without '
                        'asking the user to prove the currency already supplied.']
    return []


def _first_decimal(text):
    match = re.search(r'[-+]?\d[\d,]*(?:\.\d+)?', text or '')
    if not match:
        return None
    try:
        return Decimal(match.group(0).replace(',', ''))
    except InvalidOperation:
        return None


def _table_cells(line):
    line = line.strip()
    if '|' not in line:
        return None
    return [cell.strip() for cell in re.split(r'(?<!\\)\|', line.strip('|'))]


def _table_separator(line, width):
    cells = _table_cells(line)
    return (cells is not None and len(cells) == width and width >= 2
            and all(re.fullmatch(r':?-{3,}:?', cell) for cell in cells))


def _markdown_tables(answer):
    """Yield only contiguous header/separator/rows of matching width."""
    lines = answer.splitlines()
    index = 0
    fence = None
    while index + 1 < len(lines):
        marker = re.match(r'^\s*(`{3,}|~{3,})', lines[index])
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            index += 1
            continue
        if fence:
            index += 1
            continue
        header = _table_cells(lines[index])
        if not header or not _table_separator(lines[index + 1], len(header)):
            index += 1
            continue
        index += 2
        rows = []
        while index < len(lines):
            row = _table_cells(lines[index])
            if row is None or len(row) != len(header):
                break
            if (index + 1 < len(lines) and _table_separator(lines[index + 1], len(row))):
                break  # Adjacent table: its header is not a data row here.
            rows.append(row)
            index += 1
        yield header, rows


def _shortage_table_issues(answer):
    """Catch contradictions within one structurally complete Markdown table."""
    for cells, rows in _markdown_tables(answer):
        lowered = [cell.lower() for cell in cells]
        shortage = next((i for i, cell in enumerate(lowered)
                         if '缺口' in cell or 'shortage' in cell or 'shortfall' in cell), None)
        required = next((i for i, cell in enumerate(lowered)
                         if ('需求' in cell or 'required' in cell or 'need' in cell)
                         and not any(unit in cell for unit in ('uom', 'unit', '单位'))), None)
        actual = next((i for i, cell in enumerate(lowered)
                       if ('实际库存' in cell or 'actual_qty' in cell or 'available' in cell)
                       and not any(unit in cell for unit in ('uom', 'unit', '单位'))), None)
        required_unit = next((i for i, cell in enumerate(lowered)
                              if '需求单位' in cell or 'required_uom' in cell or 'required uom' in cell
                              or 'required unit' in cell), None)
        actual_unit = next((i for i, cell in enumerate(lowered)
                            if '库存单位' in cell or '实际单位' in cell or 'actual_uom' in cell
                            or 'actual uom' in cell or 'available_uom' in cell
                            or 'available uom' in cell or 'available unit' in cell), None)
        if shortage is None or required is None or actual is None:
            continue
        for row_cells in rows:
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
