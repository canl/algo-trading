from unittest import TestCase

from src.orders.order_manager import OrderManager


class TestOrderManager(TestCase):
    def setUp(self):
        self.om = OrderManager('mt4')

    def test_adjust_decimals(self):
        test_cases = [
            (('USD_JPY', 123.34567), 123.346),
            (('USD_XAU', 1350.34567), 1350.346),
            (('BCO_USD', 43.34567), 43.346),
            (('EUR_USD', 1.123456), 1.12346),
        ]
        for args, expect in test_cases:
            self.assertEqual(expect, self.om._adjust_decimals(instrument=args[0], price=args[1]))
