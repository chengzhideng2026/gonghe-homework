"""Collect real model/tool transcripts for manual acceptance; never confirms writes.

Requires a locally configured .env. Makes paid model API calls.
Run: python verify_llm.py
"""
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from agent import Agent, ERPNextClient, LLMRunner, configure_console

QUESTIONS = [
    "What's the current stock of copper coil?",
    'List all open purchase orders.',
    'Which customer placed the most sales orders?',
    'Which components are blocking Work Order MFG-WO-2026-00020?',
    "What's the gross margin on the 1HP/R32 compressor?",
    'Show me overdue sales invoices.',
    "What's the stock of laptops?",
    'How many employees do we have?',
    'Cancel the manufacturing run for the new compressor model.',
    'Create a new purchase order for 100 m of RM-COIL-CU-2.0 from Tongling Magnet Wire Co. at $29 per meter.',
]


def main():
    configure_console()
    client = ERPNextClient()
    runner = LLMRunner(Agent(client))
    if not runner.available():
        raise SystemExit('Missing LLM_API_KEY or LLM_MODEL. Configure .env locally first.')
    before = client.count('Purchase Order')
    report = {'timestamp_utc': datetime.now(timezone.utc).isoformat(),
              'model': runner.model, 'base_url': runner.base,
              'thinking': os.getenv('LLM_ENABLE_THINKING', 'provider default'),
              'thinking_budget': os.getenv('LLM_THINKING_BUDGET'),
              'scope': 'Real LLM responses and tool traces; requires manual grading against ORIGINAL_README.md',
              'results': []}
    out = Path(__file__).with_name('evidence')
    out.mkdir(exist_ok=True)
    errors = 0
    for question in QUESTIONS:
        history = []
        started = time.monotonic()
        print('QUESTION:', question, flush=True)
        try:
            answer, history = runner.ask(question, history)
            result = {'question': question, 'answer': answer, 'history': history}
            print(answer, flush=True)
        except Exception as exc:
            errors += 1
            result = {'question': question, 'error': str(exc), 'history': history}
            print('ERROR:', exc, flush=True)
        report['results'].append(result)
        result['elapsed_seconds'] = round(time.monotonic() - started, 2)
        report['purchase_order_count_unchanged'] = client.count('Purchase Order') == before
        (out / 'llm_acceptance.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    if not report['purchase_order_count_unchanged']:
        raise SystemExit('Unexpected Purchase Order count change; inspect ERPNext before continuing.')
    print('Transcripts saved to evidence/llm_acceptance.json; review correctness manually.')
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
