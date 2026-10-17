"""Local durable confirmation journal. No credentials; never retries ERP writes."""
import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path


_UNSET = object()


def _scope_matches(proposal, target_binding):
    # None retains trusted local maintenance/test access. Application paths
    # must pass their connection binding; this is not OS/SaaS authorization.
    if target_binding is None:
        return True
    stored = proposal.get('target_binding')
    return (isinstance(stored, dict) and isinstance(target_binding, dict)
            and isinstance(stored.get('endpoint'), str) and bool(stored['endpoint'])
            and isinstance(stored.get('identity_fingerprint'), str) and bool(stored['identity_fingerprint'])
            and stored == target_binding)


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

    def get(self, proposal_id, target_binding=None):
        with self._connect() as db:
            row = db.execute('SELECT body FROM proposals WHERE id=?', (proposal_id,)).fetchone()
        proposal = json.loads(row[0]) if row else None
        return proposal if proposal is not None and _scope_matches(proposal, target_binding) else None

    def active(self, target_binding=None):
        with self._connect() as db:
            rows = db.execute('SELECT id, body FROM proposals').fetchall()
        visible = {}
        for key, body in rows:
            proposal = json.loads(body)
            if proposal['state'] != 'completed' and _scope_matches(proposal, target_binding):
                visible[key] = proposal
        return visible

    def _read_for_mutation(self, db, proposal_id, target_binding):
        row = db.execute('SELECT body FROM proposals WHERE id=?', (proposal_id,)).fetchone()
        if row:
            proposal = json.loads(row[0])
            if _scope_matches(proposal, target_binding):
                return proposal
        # Do not disclose another connection's state or recorded ERP name.
        raise ValueError('Unknown proposal id')

    def claim(self, proposal_id, ttl, target_binding=None):
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            proposal = self._read_for_mutation(db, proposal_id, target_binding)
            if proposal['state'] != 'pending':
                raise ValueError(f"Proposal is {proposal['state']}; do not create again. Recorded document: {proposal.get('created_name', 'unknown')}")
            if time.time() - proposal['created_at'] > ttl:
                raise ValueError('Proposal expired; prepare and review a fresh preview')
            proposal['state'] = 'creating'
            db.execute('UPDATE proposals SET body=? WHERE id=?', (json.dumps(proposal), proposal_id))
        return proposal

    def finish(self, proposal_id, state, target_binding=None, expected_states=None,
               expected_created_name=_UNSET, **updates):
        """Update an authorized row, optionally comparing state/name atomically."""
        if isinstance(expected_states, str):
            expected_states = {expected_states}
        elif expected_states is not None:
            expected_states = set(expected_states)
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            proposal = self._read_for_mutation(db, proposal_id, target_binding)
            if ((expected_states is not None and proposal['state'] not in expected_states)
                    or (expected_created_name is not _UNSET
                        and proposal.get('created_name') != expected_created_name)):
                raise ValueError('Proposal changed while the operation was in progress; reload its state')
            proposal.update(updates, state=state)
            db.execute('UPDATE proposals SET body=? WHERE id=?', (json.dumps(proposal), proposal_id))

    def discard(self, proposal_id, target_binding=None):
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            proposal = self._read_for_mutation(db, proposal_id, target_binding)
            if proposal['state'] != 'pending':
                raise ValueError('Only a pending proposal can be discarded')
            proposal['state'] = 'discarded'
            db.execute('UPDATE proposals SET body=? WHERE id=?', (json.dumps(proposal), proposal_id))
