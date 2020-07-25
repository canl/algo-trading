from unittest import TestCase

from src.account.account_manager import AccountManager
from src.order_utils.order_manager import OrderManager
from src.trading.london_breakout import LondonBreakout


class TestLondonBreakout(TestCase):
    def setUp(self) -> None:
        om = OrderManager(account='mt4')
        am = AccountManager(account='mt4')
        self.trader = LondonBreakout(om, am)

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
            self.assertEqual(expect, self.trader.get_risk_pct(trans))
