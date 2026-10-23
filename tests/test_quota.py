import importlib.util
from pathlib import Path
import unittest
from datetime import datetime, timedelta, timezone

spec = importlib.util.spec_from_file_location('quota', Path(__file__).resolve().parents[1] / 'scripts/agent/quota.py')
quota = importlib.util.module_from_spec(spec)
spec.loader.exec_module(quota)


class SchedulingTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)

    def account(self, session, week):
        return {window: {'remaining': remaining, 'observed_at': self.now.isoformat(),
                         'resets_at': (self.now + timedelta(hours=2)).isoformat()}
                for window, remaining in [('session', session), ('week', week)]}

    def select(self, data, candidates=('codex', 'claude')):
        return quota.choose(data, candidates, self.now, 60, 10)

    def test_bottleneck_not_session_only(self):
        result = self.select({'codex': self.account(90, 15), 'claude': self.account(50, 70)})
        self.assertEqual(result['recommendation'], 'claude')

    def test_only_qualified_candidates(self):
        result = self.select({'codex': self.account(30, 30), 'claude': self.account(90, 90)}, ['codex'])
        self.assertEqual(result['recommendation'], 'codex')

    def test_missing_unknown_and_reserve_wait(self):
        for data in [{}, {'codex': {'session': self.account(80, 80)['session']}},
                     {'codex': self.account(10, 90)}]:
            self.assertIsNone(self.select(data)['recommendation'])

    def test_expired_stale_future_never_assume_refill(self):
        for field, delta in [('resets_at', -1), ('observed_at', -7200), ('observed_at', 60)]:
            account = self.account(90, 90)
            account['week'][field] = (self.now + timedelta(seconds=delta)).isoformat()
            self.assertIsNone(self.select({'codex': account})['recommendation'])

    def test_percent_validation(self):
        for value in ['nan', 'inf', '-1', '101']:
            with self.assertRaises(Exception):
                quota.percent(value)


if __name__ == '__main__':
    unittest.main()
