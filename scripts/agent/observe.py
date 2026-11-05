#!/usr/bin/env python3
"""Opt-in, local observation capture. Never promotes feedback lessons."""
import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import uuid

ROOT = Path(__file__).resolve().parents[2]
PHASES = ('requirements', 'design', 'implementation', 'review', 'operation')
FIELDS = {'phase', 'issue_type', 'observation', 'expected', 'references', 'hypotheses', 'unknowns'}


def validate(data):
    if not isinstance(data, dict) or set(data) - FIELDS:
        raise ValueError('unknown fields')
    if data.get('phase') not in PHASES:
        raise ValueError('invalid phase')
    if not isinstance(data.get('issue_type'), str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,79}', data['issue_type']):
        raise ValueError('invalid issue type')
    for key in ('observation', 'expected'):
        if not isinstance(data.get(key), str) or not data[key].strip() or len(data[key]) > 2000:
            raise ValueError('missing or oversized text')
    for key in ('references', 'hypotheses', 'unknowns'):
        values = data.get(key, [])
        if not isinstance(values, list) or len(values) > 20 or any(not isinstance(x, str) or not x.strip() or len(x) > 500 for x in values):
            raise ValueError('invalid list')
    # References are opaque handles, never filesystem paths or copied evidence.
    if any(not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,199}', x) for x in data.get('references', [])):
        raise ValueError('use opaque evidence references')
    return data


def append(root, data):
    validate(data)
    record = {**data, 'id': 'OBS-' + uuid.uuid4().hex,
              'at': datetime.now(timezone.utc).isoformat(),
              'root_cause': 'unconfirmed', 'review_status': 'pending'}
    folder = root / '.agent-state' / 'observations'
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    # A separate fixed lock serializes read/check/append across both clients.
    with (folder / 'capture.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = folder / 'feedback.jsonl'
        with path.open('a+', encoding='utf-8') as handle:
            handle.seek(0)
            existing = handle.read()
            for line in existing.splitlines():
                old = json.loads(line)
                if not isinstance(old, dict) or not isinstance(old.get('id'), str):
                    raise ValueError('invalid existing journal')
                if old['id'] == record['id']:
                    raise ValueError('duplicate ID')
            if existing and not existing.endswith('\n'):
                raise ValueError('incomplete existing journal')
            handle.write(json.dumps(record, ensure_ascii=False) + '\n')
            handle.flush()
            os.fsync(handle.fileno())
    return {'id': record['id'], 'status': 'recorded'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path, help='sanitized local JSON file')
    args = parser.parse_args()
    os.umask(0o077)
    try:
        if args.input.stat().st_size > 32768:
            raise ValueError('input too large')
        print(json.dumps(append(ROOT, json.loads(args.input.read_text(encoding='utf-8')))))
    except (ValueError, OSError, TypeError):
        parser.exit(1, 'capture failed: check sanitized input and local journal; no lesson promoted\n')


if __name__ == '__main__':
    main()
