#!/usr/bin/env python3
"""Persist scoped, curated corrections; GitHub input is untrusted inbox data."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}')
STATES = ('proposed', 'active', 'rejected', 'retired')
KINDS = ('ui', 'review', 'failure')


def scope(value):
    if not value or '\\' in value or value.startswith('/') or any(x in value.split('/') for x in ('', '.', '..')):
        raise ValueError('scope must be a repository-relative path/prefix without traversal')
    return str(PurePosixPath(value))


def nonempty(value):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 4000


def validate(entry):
    if not isinstance(entry, dict) or not ID.fullmatch(str(entry.get('id', ''))):
        raise ValueError('invalid feedback ID')
    if entry.get('kind') not in KINDS or entry.get('status') not in STATES:
        raise ValueError('invalid kind/status')
    scope(entry['scope'])
    for field in ('observation', 'expected', 'source'):
        if not nonempty(entry.get(field)):
            raise ValueError('missing or oversized ' + field)
    source = entry['source']
    if not (source.startswith('user:') and len(source) > 5) and not (urlparse(source).scheme == 'https' and urlparse(source).netloc):
        raise ValueError('source must be an HTTPS reference or user:<safe-reference>')
    if entry['status'] == 'active':
        for field in ('evidence', 'prevention'):
            if not nonempty(entry.get(field)):
                raise ValueError('active lesson requires ' + field)
    return entry


def entries(root):
    result = []
    for path in sorted((root / '.ai/feedback/entries').glob('*.json')):
        item = validate(json.loads(path.read_text()))
        if path.stem != item['id']:
            raise ValueError('filename must match feedback ID')
        result.append(item)
    return result


def save(path, data, exclusive=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    if exclusive:
        with path.open('x', encoding='utf-8') as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write('\n')
        return
    name = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False, encoding='utf-8') as handle:
            name = handle.name
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write('\n')
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        if name and os.path.exists(name):
            os.unlink(name)


def collect(repo, pr, root):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo) or pr < 1:
        raise ValueError('invalid repository or PR number')
    collected = []
    for kind, endpoint in [('comment', f'issues/{pr}/comments'),
                           ('inline', f'pulls/{pr}/comments'),
                           ('review', f'pulls/{pr}/reviews')]:
        result = subprocess.run(['gh', 'api', '--paginate', '--slurp', f'repos/{repo}/{endpoint}'],
                                capture_output=True, text=True, timeout=60, check=True)
        for page in json.loads(result.stdout):
            for item in page:
                if item.get('body', '').strip():
                    collected.append({'kind': kind, **{key: item.get(key) for key in
                                      ('id', 'html_url', 'body', 'path', 'line', 'updated_at')}})
    # All network reads must finish before updating the inbox. Never send raw API
    # errors to model context; they may contain private server details.
    folder = root / '.agent-state/feedback-inbox' / repo.replace('/', '_') / str(pr)
    for item in collected:
        if not isinstance(item['id'], int) or item['id'] < 1:
            raise ValueError('invalid GitHub comment ID')
    for item in collected:
        save(folder / f"{item['kind']}-{item['id']}.json", item)
    return {'inbox_items': len(collected), 'status': 'untrusted_candidates', 'promoted': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    record = commands.add_parser('record')
    record.add_argument('--id', required=True)
    record.add_argument('--kind', choices=KINDS, required=True)
    for key in ('scope', 'observation', 'expected', 'source'):
        record.add_argument('--' + key, required=True)
    transition = commands.add_parser('status')
    transition.add_argument('id')
    transition.add_argument('status', choices=STATES)
    transition.add_argument('--evidence')
    transition.add_argument('--prevention')
    context = commands.add_parser('context')
    context.add_argument('--path', required=True)
    commands.add_parser('check')
    commands.add_parser('list')
    sync = commands.add_parser('sync-github')
    sync.add_argument('--repo', required=True)
    sync.add_argument('--pr', type=int, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    try:
        if args.command == 'record':
            item = validate({key: getattr(args, key) for key in
                             ('id', 'kind', 'scope', 'observation', 'expected', 'source')} |
                            {'status': 'proposed', 'evidence': '', 'prevention': '', 'history': []})
            save(ROOT / '.ai/feedback/entries' / (item['id'] + '.json'), item, exclusive=True)
            output = item
        elif args.command == 'status':
            if not ID.fullmatch(args.id):
                raise ValueError('invalid feedback ID')
            path = ROOT / '.ai/feedback/entries' / (args.id + '.json')
            item = validate(json.loads(path.read_text()))
            old = item['status']
            allowed = {'proposed': {'active', 'rejected'}, 'active': {'retired'},
                       'rejected': set(), 'retired': set()}
            if args.status not in allowed[old]:
                raise ValueError('invalid transition; create a new sourced correction instead')
            item['status'] = args.status
            for field in ('evidence', 'prevention'):
                if getattr(args, field) is not None:
                    item[field] = getattr(args, field)
            validate(item)
            item['history'].append({'from': old, 'to': args.status,
                                    'at': datetime.now(timezone.utc).isoformat()})
            save(path, item)
            output = item
        elif args.command == 'sync-github':
            output = collect(args.repo, args.pr, ROOT)
        else:
            output = entries(ROOT)
            if args.command == 'context':
                target = scope(args.path)
                output = [item for item in output if item['status'] in ('active', 'proposed')
                          and (target == item['scope'] or target.startswith(item['scope'] + '/'))]
            if args.command == 'check':
                output = {'valid_records': len(output)}
        print(json.dumps(output, ensure_ascii=False, indent=2))
    except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError):
        parser.exit(1, 'feedback operation failed: check schema, state transition, paths, or gh authentication; no rule was promoted automatically\n')


if __name__ == '__main__':
    main()
