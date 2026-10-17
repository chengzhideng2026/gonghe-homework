"""Real multi-turn stock -> shortage -> PO preview check. Never confirms writes."""
import argparse
import json
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from agent import Agent, ERPNextClient, LLMRunner, configure_console
from verify_variants import po_names


QUESTIONS = [
    '请查 RM-BRG-NSK-6203 在 Stores 仓的实物数量、单位和在途，只说已核实的数据。',
    '如果把这个仓库的这种物料补到 180 Nos 的实物目标，还差多少？按当前实物算，在途另列，暂不采购。',
    '只做采购预览：向 Hangzhou Precision Bearings 买上一步的实物缺口，单价 USD 4.20，使用作业参考日期。不要创建。',
]


def main():
    configure_console()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='conversation_check.json')
    options = parser.parse_args()
    target = Path(__file__).parent / 'evidence' / options.output
    if target.exists():
        raise SystemExit('Output exists; choose a new --output filename')
    target.parent.mkdir(exist_ok=True)
    client = ERPNextClient()
    agent = Agent(client)  # Isolated memory proposals, never /confirm.
    runner = LLMRunner(agent)
    history = []
    report = {'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'model': runner.model,
              'scope': 'Real multi-turn conversation; final text requires manual review',
              'po_names_before': po_names(client), 'turns': []}
    error = None
    try:
        for question in QUESTIONS:
            started = time.monotonic()
            answer, _ = runner.ask(question, history)
            report['turns'].append({'question': question, 'answer': answer,
                                    'tool_receipts': runner.receipts(),
                                    'elapsed_seconds': round(time.monotonic() - started, 2)})
            print(answer, flush=True)
        previews = list(agent.proposals.values())
        assert len(previews) == 1, 'Expected one final preview'
        preview = previews[0]
        doc = preview['doc']
        item = doc['items'][0]
        assert doc['supplier'] == 'Hangzhou Precision Bearings'
        assert doc['currency'] == 'USD' and doc['transaction_date'] == '2025-10-15'
        assert item['item_code'] == 'RM-BRG-NSK-6203' and item['uom'] == 'Nos'
        assert item['qty'] == 50 and Decimal(str(item['rate'])) == Decimal('4.20')
        assert Decimal(preview['total']) == Decimal('210')
        report['deterministic_preview_check'] = 'pass'
        report['preview'] = preview
    except Exception as exc:
        error = exc
        report['error'] = str(exc)
    finally:
        report['history'] = runner.last_trace
        report['po_names_after'] = po_names(client)
        report['no_erp_po_write'] = report['po_names_before'] == report['po_names_after']
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    if error or not report['no_erp_po_write']:
        raise SystemExit(str(error) if error else 'Unexpected ERP PO change')
    print('Preview assertions and unchanged PO IDs: PASS; answer text pending manual review.', flush=True)


if __name__ == '__main__':
    main()
