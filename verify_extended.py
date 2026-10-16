"""Extended real ERP/model checks; optional ONE local draft write, never submit.

python verify_extended.py
python verify_extended.py --create-test-po   # seeded localhost environment only
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from agent import Agent, ERPNextClient, LLMRunner, ERPError, configure_console
from proposal_store import ProposalStore


QUESTIONS = [
    '请按客户汇总尚未收回的销售发票金额，给出总额、前两名和占比。按未结余额，不要按逾期状态筛选。请按币种分开。',
    '请汇总Payment Entry，分别给出收款、付款总额及净流入，按币种分开，不要把内部转账重复相加。',
    'Nordic Air Industries那个尚未交付的1HP R32订单，现货够吗？请给出订单号、待交数量、仓库现货和缺口。',
]


def main():
    configure_console()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--create-test-po', action='store_true')
    options = parser.parse_args()
    root = Path(__file__).parent
    out = root / 'evidence'
    out.mkdir(exist_ok=True)
    c = ERPNextClient()
    before = c.count('Purchase Order')
    report = {'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'model_results': []}
    # Different DocTypes and complete Decimal sums; neither path uses an LLM.
    ar = c.aggregate('Sales Invoice', [['docstatus', '=', 1], ['outstanding_amount', '>', 0]],
                     ['currency', 'customer'], ['outstanding_amount'])
    ap = c.aggregate('Purchase Invoice', [['docstatus', '=', 1], ['outstanding_amount', '>', 0]],
                     ['currency', 'supplier'], ['outstanding_amount'])
    from decimal import Decimal
    assert sum(Decimal(g['sums']['outstanding_amount']) for g in ar['groups']) == Decimal('37720')
    assert sum(Decimal(g['sums']['outstanding_amount']) for g in ap['groups']) == Decimal('22784')
    report['real_aggregates'] = {'receivables': ar, 'payables': ap}
    runner = LLMRunner(Agent(c))
    for question in QUESTIONS:
        print('QUESTION:', question, flush=True)
        history = []
        answer, _ = runner.ask(question, history)
        print(answer, flush=True)
        report['model_results'].append({'question': question, 'answer': answer, 'history': history})
        (out / 'extended_audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    assert c.count('Purchase Order') == before
    report['read_only_po_count_unchanged'] = True
    if options.create_test_po:
        if c.base not in {'http://localhost:8080', 'http://127.0.0.1:8080'}:
            raise RuntimeError('Write verification is restricted to the local homework seed')
        receipt = out / 'audit_write.json'
        if receipt.exists():
            raise RuntimeError('Audit write receipt exists; reconcile it rather than creating again')
        store = ProposalStore(root / '.local' / 'audit-proposals.sqlite3')
        agent = Agent(c, store)
        runner = LLMRunner(agent)
        previous = set(agent.proposals)
        history = []
        answer, _ = runner.ask('Prepare a purchase order for 100 Meter of RM-COIL-CU-2.0 from Tongling Magnet Wire Co. at USD 29 per Meter. Preview only.', history)
        print(answer, flush=True)
        new = set(agent.proposals) - previous
        assert len(new) == 1
        proposal_id = new.pop()
        preview = agent.proposals[proposal_id]
        doc = preview['doc']
        assert doc['supplier'] == 'Tongling Magnet Wire Co.'
        assert doc['currency'] == 'USD' and doc['transaction_date'] == '2025-10-15'
        assert doc['items'] == [{'item_code': 'RM-COIL-CU-2.0', 'qty': 100.0, 'uom': 'Meter', 'rate': 29.0}]
        assert c.count('Purchase Order') == before
        receipt.write_text(json.dumps({'state': 'attempting', 'proposal_id': proposal_id, 'preview': preview}, indent=2), encoding='utf-8')
        # Explicit test-harness confirmation, after inspecting payload. Never an LLM tool.
        result = Agent(c, ProposalStore(store.path)).confirm(proposal_id)
        receipt.write_text(json.dumps({'result': result, 'model_history': history}, ensure_ascii=False, indent=2), encoding='utf-8')
        assert result['verified']['docstatus'] == 0
        assert result['verified']['grand_total'] == 2900
        assert not result['review_required'], result['differences_from_preview']
        try:
            Agent(c, ProposalStore(store.path)).confirm(proposal_id)
        except ERPError:
            pass
        else:
            raise AssertionError('Duplicate confirmation was not blocked')
        assert c.count('Purchase Order') == before + 1
        report['created_draft'] = result['name']
        print('Created and verified ONE local draft:', result['name'], flush=True)
    (out / 'extended_audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
