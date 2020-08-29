import os
from unittest import TestCase

import pandas as pd

from src.backtester import BackTester
from src.orders.order import Order, OrderStatus, OrderSide


class TestBackTester(TestCase):
    def setUp(self):
        pass

    def test_run(self):
        df = pd.read_csv(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'sample_price.csv')).set_index('time')
        orders = create_dummy_orders(df)
        back_tester = BackTester()
        back_tester.run(df, orders)
        self.assertAlmostEqual(0.1, sum(o.pnl for o in orders))
        self.assertAlmostEqual(39, len([o for o in orders if o.outcome == 'win']))
        self.assertAlmostEqual(68, len([o for o in orders if o.outcome == 'loss']))


def create_dummy_orders(df):
    df['ma_12'] = df.close.rolling(12).mean()
    df['ma_50'] = df.close.rolling(50).mean()
    ccy_pair = 'GBP_USD'
    orders = []
    for time, ohlc in df.to_dict('index').items():
        if ohlc['open'] < ohlc['ma_12'] < ohlc['close'] and ohlc['low'] > ohlc['ma_50']:
            orders.append(Order(time, OrderSide.LONG, ccy_pair, ohlc['close'], sl=ohlc['close'] - 0.01, tp=ohlc['close'] + 0.02, status=OrderStatus.FILLED))
        elif ohlc['close'] < ohlc['ma_12'] < ohlc['open'] and ohlc['high'] < ohlc['ma_50']:
            orders.append(Order(time, OrderSide.SHORT, ccy_pair, ohlc['close'], sl=ohlc['close'] + 0.01, tp=ohlc['close'] - 0.02, status=OrderStatus.FILLED))

    return orders


def equal_ignore_order(a, b):
    """ Use only when elements are neither hashable nor sortable! """
    unmatched = list(b)
    for element in a:
        try:
            unmatched.remove(element)
        except ValueError:
            return False
    return not unmatched
