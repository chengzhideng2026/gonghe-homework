"""Local durable confirmation journal. No credentials; never retries ERP writes."""
import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path


class ProposalStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS proposals (id TEXT PRIMARY KEY, body TEXT NOT NULL)')

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    def put(self, proposal_id, proposal):
        with self._connect() as db:
            db.execute('INSERT INTO proposals VALUES (?, ?)', (proposal_id, json.dumps(proposal, allow_nan=False)))

    def get(self, proposal_id):
        with self._connect() as db:
            row = db.execute('SELECT body FROM proposals WHERE id=?', (proposal_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def active(self):
        with self._connect() as db:
            rows = db.execute('SELECT id, body FROM proposals').fetchall()
        return {key: json.loads(body) for key, body in rows if json.loads(body)['state'] != 'completed'}

    def claim(self, proposal_id, ttl):
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT body FROM proposals WHERE id=?', (proposal_id,)).fetchone()
            if not row:
                raise ValueError('Unknown proposal id')
            proposal = json.loads(row[0])
            if proposal['state'] != 'pending':
                raise ValueError(f"Proposal is {proposal['state']}; do not create again. Recorded document: {proposal.get('created_name', 'unknown')}")
            if time.time() - proposal['created_at'] > ttl:
                raise ValueError('Proposal expired; prepare and review a fresh preview')
            proposal['state'] = 'creating'
            db.execute('UPDATE proposals SET body=? WHERE id=?', (json.dumps(proposal), proposal_id))
        return proposal

    def finish(self, proposal_id, state, **updates):
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT body FROM proposals WHERE id=?', (proposal_id,)).fetchone()
            if not row:
                raise ValueError('Unknown proposal id')
            proposal = json.loads(row[0])
            proposal.update(updates, state=state)
            db.execute('UPDATE proposals SET body=? WHERE id=?', (json.dumps(proposal), proposal_id))

    def discard(self, proposal_id):
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT body FROM proposals WHERE id=?', (proposal_id,)).fetchone()
            if not row:
                raise ValueError('Unknown proposal id')
            proposal = json.loads(row[0])
            if proposal['state'] != 'pending':
                raise ValueError('Only a pending proposal can be discarded')
            proposal['state'] = 'discarded'
            db.execute('UPDATE proposals SET body=? WHERE id=?', (json.dumps(proposal), proposal_id))
