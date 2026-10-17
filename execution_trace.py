"""Best-effort local execution trace writer; it never changes business outcomes."""
from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path


_SENSITIVE = re.compile(r'^(api[_-]?key|api[_-]?secret|access[_-]?token|refresh[_-]?token|client[_-]?secret|authorization|password|secret|token)$', re.I)


def _redact(value, depth=0):
    if depth > 5:
        return '[TRUNCATED]'
    if isinstance(value, dict):
        return {str(key): ('[REDACTED]' if _SENSITIVE.search(str(key).replace('-', '_')) else _redact(item, depth + 1))
                for key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item, depth + 1) for item in value[:50]]
    if isinstance(value, str):
        return value[:2000]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return str(value)[:2000]


class ExecutionTraceWriter:
    def __init__(self, root=None):
        self.root = Path(root or Path(__file__).with_name('.local') / 'traces')

    def write(self, turn_id, record):
        self.root.mkdir(parents=True, exist_ok=True)
        target = self.root / f'{turn_id}.json'
        fd, temporary = tempfile.mkstemp(prefix=f'{turn_id}.', suffix='.tmp', dir=self.root)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream:
                json.dump(_redact(record), stream, ensure_ascii=False, allow_nan=False, indent=2)
                stream.write('\n')
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
        except Exception:
            try:
                os.unlink(temporary)
            except OSError:
                pass
            raise
