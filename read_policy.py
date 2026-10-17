"""Bounded client-side read reuse and upstream request limits; no ERP changes.

One client belongs to one synchronous CLI session. This is not a distributed
tenant quota service. Cache entries are exact requests, never inferred matches.
"""
import copy
import hashlib
import json
import math
import os
import time
from collections import OrderedDict, deque
from contextlib import contextmanager
from datetime import datetime, timezone


class RequestLimitError(RuntimeError):
    pass


def _number(name, default, minimum, maximum, integer=False):
    value = float(os.getenv(name, str(default)))
    if not math.isfinite(value) or not minimum <= value <= maximum or (integer and not value.is_integer()):
        raise ValueError(f'{name} must be between {minimum} and {maximum}' + (' and integral' if integer else ''))
    return int(value) if integer else value


class ReadPolicy:
    def __init__(self, *, ttl=None, metadata_ttl=None, max_requests=None,
                 per_minute=None, interval=None, clock=time.monotonic, sleep=time.sleep):
        self.ttl = _number('ERP_READ_CACHE_TTL', 30, 0, 3600) if ttl is None else ttl
        self.metadata_ttl = _number('ERP_META_CACHE_TTL', 600, 0, 86400) if metadata_ttl is None else metadata_ttl
        self.max_requests = _number('ERP_MAX_REQUESTS_PER_TURN', 40, 1, 1000, True) if max_requests is None else max_requests
        self.per_minute = _number('ERP_MAX_REQUESTS_PER_MINUTE', 120, 1, 10000, True) if per_minute is None else per_minute
        self.interval = _number('ERP_MIN_REQUEST_INTERVAL', .25, 0, 10) if interval is None else interval
        self.clock, self.sleep = clock, sleep
        self.cache = OrderedDict()
        self.cache_bytes = 0
        self.window = deque()
        self.last_attempt = None
        self.active, self.bypass = False, 0
        self.events, self.stats = [], {}

    @contextmanager
    def turn(self):
        if self.active:
            raise RuntimeError('A client cannot serve concurrent/nested model turns')
        self.active = True
        self.events = []
        self.stats = dict(http_attempts=0, cache_hits=0, rejected_requests=0)
        try:
            yield self
        finally:
            self.active = False

    @contextmanager
    def fresh(self):
        """Authoritative checks bypass both cache reads and cache population."""
        self.bypass += 1
        try:
            yield
        finally:
            self.bypass -= 1

    def clear(self):
        self.cache.clear()
        self.cache_bytes = 0

    def mark(self):
        return dict(self.stats), len(self.events)

    def report(self, mark=None):
        before, offset = mark if mark is not None else ({}, 0)
        return {**{key: value - before.get(key, 0) for key, value in self.stats.items()},
                'sources': copy.deepcopy(self.events[offset:]),
                'source_log_capped': len(self.events) >= 256,
                'limits': {'requests_per_turn': self.max_requests, 'requests_per_minute': self.per_minute},
                'freshness': 'Cache hits are prior observations at fetched_at, not proof of current state. '
                             'Exact request reuse only; partial pages retain their original coverage.'}

    def _event(self, source, path, fetched_at=None, age=None):
        if self.active and len(self.events) < 256:
            self.events.append({'source': source, 'path': path, 'fetched_at': fetched_at,
                                'age_seconds': round(age, 3) if age is not None else None})

    def request(self, method, path, params, scope, send):
        method = method.upper()
        read = method == 'GET'
        # Credentials never enter the retained key, event log or business cache.
        key = hashlib.sha256(json.dumps([scope, path, params], sort_keys=True,
                                      ensure_ascii=False, allow_nan=False).encode()).hexdigest()
        ttl = self.metadata_ttl if path == '/api/method/frappe.desk.form.load.getdoctype' else self.ttl
        reusable = read and self.active and not self.bypass and ttl > 0
        now = self.clock()
        if reusable and key in self.cache:
            stored, fetched_at, data, size = self.cache[key]
            if now - stored < ttl:
                self.cache.move_to_end(key)
                self.stats['cache_hits'] += 1
                self._event('cache', path, fetched_at, now-stored)
                return copy.deepcopy(data)
            self.cache_bytes -= self.cache.pop(key)[3]
        if not read:
            # Even a failed/timed-out write may have reached the ERP.
            self.clear()
        while self.window and now-self.window[0] >= 60:
            self.window.popleft()
        exhausted = self.active and self.stats['http_attempts'] >= self.max_requests
        if exhausted or len(self.window) >= self.per_minute:
            if self.active:
                self.stats['rejected_requests'] += 1
            self._event('budget_rejected', path)
            raise RequestLimitError('ERP request budget exhausted; narrow the filters or reuse verified evidence. '
                                    'No additional HTTP request was sent; incomplete data cannot establish a total. '
                                    'The rolling minute limit requires waiting before a later request.')
        if self.last_attempt is not None:
            delay = self.interval - (now-self.last_attempt)
            if delay > 0:
                self.sleep(delay)
        self.last_attempt = self.clock()
        self.window.append(self.last_attempt)
        if self.active:
            self.stats['http_attempts'] += 1
        try:
            result = send()
        except Exception:
            self._event('http_error', path)
            raise
        fetched_at = datetime.now(timezone.utc).isoformat()
        self._event('http', path, fetched_at, 0)
        if reusable:
            size = len(json.dumps(result, ensure_ascii=False, default=str).encode())
            # Bound both retained entries and payload bytes, including metadata.
            if size <= 1024 * 1024:
                if key in self.cache:
                    self.cache_bytes -= self.cache.pop(key)[3]
                self.cache[key] = (self.clock(), fetched_at, copy.deepcopy(result), size)
                self.cache_bytes += size
                while len(self.cache) > 64 or self.cache_bytes > 4 * 1024 * 1024:
                    self.cache_bytes -= self.cache.popitem(last=False)[1][3]
        return result
