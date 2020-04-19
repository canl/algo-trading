from unittest import TestCase, mock
import numpy as np
from src.position_calculator import pos_size


class TestCommon(TestCase):
    def setUp(self) -> None:
        self.patcher = mock.patch('src.position_calculator.get_fx_rate')
        self.mock_get_fx_rate = self.patcher.start()
        self.mock_get_fx_rate.side_effect = lambda *x: {
            ('GBP', 'GBP_USD'): 1.25,
            ('GBP', 'EUR_USD'): 1.25,
            ('GBP', 'EUR_AUD'): 1.96537,
            ('GBP', 'EUR_JPY'): 134.502,
            ('GBP', 'AUD_SGD'): 1.77757,
            ('GBP', 'XAU_USD'): 1.25,
            ('GBP', 'GBP_NZD'): 2.07264,
        }[x]

    def test_position_calculator(self):
        test_cases = [
            ('GBP_USD', 0.5),
            ('EUR_USD', 0.5),
            ('EUR_AUD', 0.7861),
            ('EUR_JPY', 0.538),
            ('AUD_SGD', 0.711),
            ('XAU_USD', 0.005),
            ('GBP_NZD', 0.8291)
        ]

        for instrument, expect in test_cases:
            self.assertTrue(np.isclose(
                expect,
                pos_size(account_balance=10000, risk_pct=0.02, sl_pips=50, instrument=instrument, account_ccy='GBP'))
            )
