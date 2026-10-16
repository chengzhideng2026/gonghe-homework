"""Reproducible REST integration checks. No model or writes by default.

Run: python verify_live.py
Optional local seeded-database write test: python verify_live.py --create-test-po
The opt-in creates ONE DRAFT, never submits, and records its name in evidence/.
"""
import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from agent import ERPNextClient, Agent, REFERENCE_DATE, overdue


def run(create_test_po=False):
    client = ERPNextClient()
    checks = []
    def check(name, actual, expected):
        checks.append({'check': name, 'passed': actual == expected,
                       'actual': actual, 'expected': expected})

    check('Item count', client.count('Item'), 18)
    copper = client.list('Bin', ['item_code', 'warehouse', 'actual_qty', 'ordered_qty',
                                 'reserved_qty_for_production'],
                         [['item_code', '=', 'RM-COIL-CU-2.0'], ['warehouse', '=', 'Stores - CCM']])
    check('Copper stock/on-order/reserved',
          [[r['actual_qty'], r['ordered_qty'], r['reserved_qty_for_production']] for r in copper],
          [[50, 200, 60]])
    orders = client.list('Purchase Order', ['name', 'grand_total', 'status'],
                         [['status', '=', 'To Receive and Bill']], limit=100)
    check('Open PO count', len(orders), 6)
    check('Open PO total', str(sum((Decimal(str(o['grand_total'])) for o in orders), Decimal(0))), '15065.5')
    sales = client.list('Sales Order', ['name', 'customer'], limit=100)
    check('Sales order count matches API count', len(sales), client.count('Sales Order'))
    customers = Counter(o['customer'] for o in sales)
    check('Most sales orders', customers.most_common(2), [('GreenAir HVAC Solutions', 5), ('Summit Climate OEM', 4)])
    wo = client.get('Work Order', 'MFG-WO-2026-00020')
    shortages = []
    for line in wo['required_items']:
        bins = client.list('Bin', ['actual_qty'], [['item_code', '=', line['item_code']],
                                                ['warehouse', '=', line['source_warehouse']]])
        have = sum(r['actual_qty'] for r in bins)
        if line['required_qty'] > have:
            shortages.append([line['item_code'], line['required_qty'], have])
    check('Work order shortages', sorted(shortages), sorted([
        ['SA-MOTOR-1HP', 30, 20], ['SA-PUMP-R32', 30, 20], ['RM-COIL-CU-2.0', 60, 50]]))
    bom = client.get('BOM', 'BOM-FG-COMP-1HP-R32-001')
    check('1HP/R32 BOM cost', bom['total_cost'], 575.2)
    prices = client.list('Item Price', ['price_list_rate'], [['item_code', '=', 'FG-COMP-1HP-R32'],
                                                          ['price_list', '=', 'Standard Selling']])
    check('1HP/R32 list price', [p['price_list_rate'] for p in prices], [600])
    invoices = client.list('Sales Invoice', ['name', 'customer', 'due_date', 'outstanding_amount'], limit=100)
    check('Invoice coverage', len(invoices), client.count('Sales Invoice'))
    late = overdue(invoices)
    check('Overdue invoice names', sorted(i['name'] for i in late),
          [f'ACC-SINV-2026-{n:05}' for n in (11, 13, 15, 17)])
    check('Overdue amount', sum(i['outstanding_amount'] for i in late), 25380)
    check('Missing laptop item', client.list('Item', ['name'], [['item_name', 'like', '%laptop%']]), [])
    check('Employee count', client.count('Employee'), 0)
    work_orders = client.list('Work Order', ['name', 'production_item', 'status'],
                              [['status', 'in', ['Not Started', 'In Process']]], limit=100)
    check('Ambiguous cancellation candidates', sorted(o['name'] for o in work_orders),
          ['MFG-WO-2026-00019', 'MFG-WO-2026-00020'])
    meta = client.meta('Purchase Order')
    check('Generic metadata discovery', bool(meta), True)
    agent = Agent(client)
    before = client.count('Purchase Order')
    preview = agent.proposal_po('Tongling Magnet Wire Co.', 'RM-COIL-CU-2.0', 100, 'Meter', 29)
    check('PO preview amount', preview['estimated_total'], '2900')
    check('PO preview has no write', client.count('Purchase Order'), before)
    check('PO dates pinned', [preview['doc']['transaction_date'], preview['doc']['schedule_date']],
          [REFERENCE_DATE, REFERENCE_DATE])
    write_result = None
    receipt = Path(__file__).with_name('evidence') / 'test_po_receipt.json'
    if create_test_po:
        if receipt.exists():
            raise RuntimeError('Write test already recorded; inspect evidence/test_po_receipt.json before another run')
        if not all(c['passed'] for c in checks):
            raise RuntimeError('Read checks must pass before write test')
        # Leave a durable attempt record first: a lost response must not cause blind re-creation.
        receipt.parent.mkdir(exist_ok=True)
        receipt.write_text(json.dumps({'state': 'attempting', 'preview': preview}, indent=2), encoding='utf-8')
        write_result = agent.confirm(preview['proposal_id'])
        receipt.write_text(json.dumps(write_result, indent=2), encoding='utf-8')
        doc = write_result['verified']
        check('Test PO draft status', doc['docstatus'], 0)
        check('Test PO amount', doc['grand_total'], 2900)
        check('Test PO transaction date', doc['transaction_date'], REFERENCE_DATE)
        check('Test PO count increased once', client.count('Purchase Order'), before + 1)
        try:
            agent.confirm(preview['proposal_id'])
        except ValueError:
            check('Repeated confirmation blocked', True, True)
        else:
            check('Repeated confirmation blocked', False, True)
    result = {'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'reference_date': REFERENCE_DATE,
              'scope': 'Real ERPNext REST integration; no LLM involved', 'checks': checks,
              'evidence': {'copper': copper, 'open_purchase_orders': orders, 'customers': dict(customers),
                           'shortages': shortages, 'overdue': late, 'open_work_orders': work_orders,
                           'preview': preview, 'created_test_po': write_result}}
    out = Path(__file__).with_name('evidence')
    out.mkdir(exist_ok=True)
    (out / ('live_write.json' if create_test_po else 'live_read.json')).write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    for c in checks:
        print(('PASS' if c['passed'] else 'FAIL') + ': ' + c['check'])
        if not c['passed']:
            print(f"  actual={c['actual']!r}, expected={c['expected']!r}")
    return all(c['passed'] for c in checks)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--create-test-po', action='store_true')
    args = parser.parse_args()
    raise SystemExit(0 if run(args.create_test_po) else 1)
