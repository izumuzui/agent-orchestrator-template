#!/usr/bin/env python3
"""Install the versioned Codex hook without replacing unrelated configuration."""
import datetime
import json
from pathlib import Path
import shlex
import shutil


def install(home):
    root = home / '.codex'
    target = root / 'hooks/session_note.py'
    config = root / 'hooks.json'
    data = json.loads(config.read_text()) if config.exists() else {}
    hooks = data.setdefault('hooks', {})
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    for path in (target, config):
        if path.exists():
            shutil.copy2(path, path.with_name(path.name + '.bak-' + stamp))
    target.parent.mkdir(parents=True, exist_ok=True)
    # Installation never authorizes sending conversation text to a provider.
    (target.parent / 'session_note.disabled').touch()
    shutil.copy2(Path(__file__).with_name('codex_session_note.py'), target)
    command = 'python3 ' + shlex.quote(str(target))
    for event in ('SessionEnd', 'Stop'):
        groups = hooks.setdefault(event, [])
        found = False
        for group in groups:
            for hook in group.get('hooks', []):
                if hook.get('command') in (command, "python3 '" + str(target) + "'", 'python3 ~/.codex/hooks/session_note.py'):
                    hook.update(type='command', command=command, timeout=10)
                    found = True
        if not found:
            groups.append({'hooks': [{'type': 'command', 'command': command, 'timeout': 10}]})
    tmp = config.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
    tmp.replace(config)
    print('Installed disabled Codex SessionEnd/Stop note hooks; backups: *.bak-' + stamp)


if __name__ == '__main__':
    install(Path.home())
