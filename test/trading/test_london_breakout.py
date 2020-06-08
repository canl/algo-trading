from unittest import TestCase

from src.trading.london_breakout import get_risk_pct


class TestLondonBreakout(TestCase):
    def test_get_risk_pct(self):
        test_cases = [
            (0.03, [{'id': 1, 'realized_pl': 100}]),
            (0.02, [{'id': 1, 'realized_pl': 100}, {'id': 2, 'realized_pl': 100}]),
            (0.04, [{'id': 1, 'realized_pl': 100}, {'id': 2, 'realized_pl': 100}, {'id': 3, 'realized_pl': 100}]),
            (0.01, [{'id': 3, 'realized_pl': 100}, {'id': 4, 'realized_pl': -100}]),
            (0.01, [{'id': 1, 'realized_pl': 100}, {'id': 2, 'realized_pl': 100}, {'id': 3, 'realized_pl': 100}, {'id': 4, 'realized_pl': -100}]),
            (0.03, [{'id': 1, 'realized_pl': 100}, {'id': 2, 'realized_pl': 100}, {'id': 3, 'realized_pl': -100}, {'id': 4, 'realized_pl': 100}]),
            (0.02, [{'id': 1, 'realized_pl': 100}, {'id': 2, 'realized_pl': -100}, {'id': 3, 'realized_pl': 100}, {'id': 4, 'realized_pl': 100}]),
            (0.01, [{'id': 1, 'realized_pl': 100}, {'id': 2, 'realized_pl': 100}, {'id': 3, 'realized_pl': 100}, {'id': 4, 'realized_pl': 100}]),
            (0.03, [{'id': 1, 'realized_pl': 100}, {'id': 2, 'realized_pl': 100}, {'id': 3, 'realized_pl': 100}, {'id': 4, 'realized_pl': -100}, {'id': 4, 'realized_pl': 100}]),
            (0.01, [{'id': 1, 'realized_pl': 100}, {'id': 2, 'realized_pl': 100}, {'id': 3, 'realized_pl': 100}, {'id': 4, 'state': 'OPEN', 'realized_pl': -100}, {'id': 4, 'realized_pl': 100}]),
        ]
        for expect, trans in test_cases:
            self.assertEqual(expect, get_risk_pct(trans))
