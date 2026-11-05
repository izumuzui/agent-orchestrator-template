import concurrent.futures
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'observe.py'
spec = importlib.util.spec_from_file_location('observe', SCRIPT)
observe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(observe)
DATA = dict(phase='requirements', issue_type='missing_clarification', observation='An assumption was treated as agreed.', expected='Keep the choice open.', references=['evidence:case-1'])


class CaptureTests(unittest.TestCase):
    def test_concurrent_clients(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / 'scripts/agent/observe.py'
            script.parent.mkdir(parents=True)
            script.write_text(SCRIPT.read_text())
            source = root / 'input.json'
            source.write_text(json.dumps(DATA))
            def run(_):
                return subprocess.run([sys.executable, str(script), '--input', str(source)], capture_output=True, text=True)
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                results = list(pool.map(run, range(20)))
            self.assertTrue(all(x.returncode == 0 for x in results))
            journal = root / '.agent-state/observations/feedback.jsonl'
            records = [json.loads(x) for x in journal.read_text().splitlines()]
            self.assertEqual(len({x['id'] for x in records}), 20)
            self.assertTrue(all(x['root_cause'] == 'unconfirmed' for x in records))
            self.assertEqual(journal.stat().st_mode & 0o777, 0o600)
            self.assertFalse((root / '.ai/feedback').exists())
            self.assertEqual(set(json.loads(results[0].stdout)), {'id', 'status'})

    def test_validation_before_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for bad in ({**DATA, 'phase': 'unknown'}, {**DATA, 'observation': ''}, {**DATA, 'secret': 'x'}, {**DATA, 'references': ['/private/path']}, {**DATA, 'hypotheses': 'cause'}):
                with self.assertRaises(ValueError):
                    observe.append(root, bad)
            self.assertFalse((root / '.agent-state').exists())

    def test_corrupt_journal_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / '.agent-state/observations'
            folder.mkdir(parents=True)
            path = folder / 'feedback.jsonl'
            for text in ('broken', '{"id":"old"}'):
                path.write_text(text)
                with self.assertRaises(ValueError):
                    observe.append(root, DATA)
                self.assertEqual(path.read_text(), text)
