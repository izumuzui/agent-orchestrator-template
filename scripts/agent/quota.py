#!/usr/bin/env python3
"""Manual account-level quota observations and advisory scheduling; no provider calls."""
import argparse
from datetime import datetime, timezone
import fcntl
import json
import math
import os
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / '.agent-state' / 'quota.json'
PROVIDERS = ('codex', 'claude')


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('timestamp must include timezone')
    return parsed.astimezone(timezone.utc)


def percent(value):
    number = float(value)
    if not math.isfinite(number) or not 0 <= number <= 100:
        raise argparse.ArgumentTypeError('remaining percent must be 0..100')
    return number


def choose(data, candidates, now, max_age, reserve):
    eligible, reasons = [], {}
    for provider in candidates:
        windows = data.get(provider, {})
        if 'session' not in windows or 'week' not in windows:
            reasons[provider] = 'missing session or week observation'
            continue
        remaining = []
        for window in ('session', 'week'):
            item = windows[window]
            observed = timestamp(item['observed_at'])
            reset = timestamp(item['resets_at'])
            age = (now - observed).total_seconds()
            if age < 0 or age > max_age * 60:
                reasons[provider] = 'stale or future observation; refresh both windows'
                break
            if now >= reset:
                reasons[provider] = 'reset passed; observe again (no assumed refill)'
                break
            if item['remaining'] <= reserve:
                reasons[provider] = 'at or below reserve'
                break
            remaining.append(item['remaining'])
        else:
            # Minimum window is the bottleneck; percentages are not token counts.
            eligible.append((min(remaining), provider))
            reasons[provider] = 'eligible'
    eligible.sort(key=lambda item: (-item[0], item[1]))
    return {'recommendation': eligible[0][1] if eligible else None,
            'status': 'ready' if eligible else 'wait_or_refresh',
            'reasons': reasons, 'advisory_only': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    record = commands.add_parser('record')
    record.add_argument('provider', choices=PROVIDERS)
    record.add_argument('window', choices=('session', 'week'))
    record.add_argument('--remaining', required=True, type=percent)
    record.add_argument('--resets-at', required=True)
    select = commands.add_parser('select')
    select.add_argument('--candidates', nargs='+', choices=PROVIDERS, required=True,
                        help='Only candidates already qualified for this role')
    select.add_argument('--max-age-minutes', type=float, default=60)
    select.add_argument('--reserve-percent', type=percent, default=10)
    commands.add_parser('show')
    args = parser.parse_args()
    now = datetime.now(timezone.utc)
    if args.command == 'record':
        try:
            reset = timestamp(args.resets_at)
        except ValueError as error:
            parser.error(str(error))
        if reset <= now:
            parser.error('reset must be in the future')
    if args.command == 'select' and (not math.isfinite(args.max_age_minutes) or args.max_age_minutes <= 0):
        parser.error('max age must be positive and finite')
    os.umask(0o077)
    STATE.parent.mkdir(parents=True, exist_ok=True)
    with STATE.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        data = json.loads(STATE.read_text()) if STATE.exists() else {}
        if args.command == 'record':
            data.setdefault(args.provider, {})[args.window] = {
                'remaining': args.remaining, 'resets_at': reset.isoformat(),
                'observed_at': now.isoformat(), 'source': 'manual'}
            name = None
            try:
                with tempfile.NamedTemporaryFile(mode='w', dir=STATE.parent, delete=False) as handle:
                    name = handle.name
                    json.dump(data, handle, indent=2)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(name, STATE)
            finally:
                if name and os.path.exists(name):
                    os.unlink(name)
        if args.command == 'select':
            output = choose(data, args.candidates, now, args.max_age_minutes, args.reserve_percent)
        else:
            output = data
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
