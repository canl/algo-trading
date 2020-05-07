"""
A simple mean reversion strategy wit back testing result. The strategy only works when market is ranging,
which is around 70% of the time.

Rules:

    Entry:
        1. Place a long limit order if price breaks 20 days low with entry price as: 20 days low - 5pips adj
        2. Place a short limit order if price breaks 20 days high with entry price as: 20 days high + 5pips adj
        3. Cancel the order if it cannot be filled in 3 hours
        4. Maximum 4 orders allowed for each long or short direction. Do not want to against the trend

    SL:
        long: entry - 20 days ATR
        Short: entry + 20 days ATR

    TP:
        Long: entry + 20 days ATR
        Short: entry - 20 days ATR

    Position Size:
        %2 risk

"""

import logging
from datetime import timedelta

import pandas as pd
from matplotlib import pyplot as plt

from src.backtester import BackTester
from src.order_utils.order import Order, OrderSide, OrderStatus

logger = logging.getLogger(__name__)


def process_pending(order, ohlc):
    # If the order cannot be filled within next 3 hours, cancel it
    if pd.to_datetime(ohlc['time']) - pd.to_datetime(order.order_date) <= timedelta(hours=3):
        if (order.is_long and ohlc['low'] <= order.entry) or \
                (order.is_short and ohlc['high'] >= order.entry):
            logger.debug(pd.to_datetime(ohlc['time']) - pd.to_datetime(order.order_date))
            logger.info(f"Fill {order.side} order [{order.id}] @ {order.entry} @ {ohlc['time']} [order date: {order.order_date}]")
            order.fill(ohlc['time'])
    else:
        order.cancel(ohlc['time'])


def process_filled(order, ohlc):
    if order.is_long:
        if ohlc['low'] <= order.sl:
            order.close_with_loss(ohlc['time'])
        elif ohlc['high'] >= order.tp:
            order.close_with_win(ohlc['time'])
    else:
        if ohlc['high'] >= order.sl:
            order.close_with_loss(ohlc['time'])
        elif ohlc['low'] <= order.tp:
            order.close_with_win(ohlc['time'])


def run(instrument: str, window: int, max_orders: int, entry_adj: float, tp_adj: float, start_date: str = None, end_date: str = None):
    price_df = pd.read_csv(f'c:/temp/{instrument.lower()}_h1_enrich_10_20.csv')
    '''
         #   Column        Non-Null Count  Dtype  
        ---  ------        --------------  -----  
         0   time          65770 non-null  object 
         1   open          65770 non-null  float64
         2   high          65770 non-null  float64
         3   low           65770 non-null  float64
         4   close         65770 non-null  float64
         5   last_10_high  65770 non-null  float64
         6   last_20_high  65770 non-null  float64
         7   last_10_low   65770 non-null  float64
         8   last_20_low   65770 non-null  float64
         9   day_close     65770 non-null  float64
         10  day_atr_20    65770 non-null  float64
         11  day_ema_55    65770 non-null  float64
    '''

    if start_date and end_date:
        price_df = price_df[(price_df['time'] >= start_date) & (price_df['time'] < end_date)]

    orders = []
    for idx, ohlc in enumerate(price_df.to_dict('records')):
        [process_pending(o, ohlc) for o in orders if o.is_pending]
        [process_filled(o, ohlc) for o in orders if o.is_filled]

        open_long = [o for o in orders if o.is_long and o.is_open]
        open_short = [o for o in orders if o.is_short and o.is_open]
        atr = ohlc['day_atr_20']
        if ohlc['high'] == ohlc[f'last_{window}_high'] and len(open_short) < max_orders:
            # Place a short limit order
            entry = ohlc['high']
            orders.append(
                Order(order_date=ohlc['time'], side=OrderSide.SHORT, entry=entry + entry_adj, sl=entry + atr, tp=entry - atr - tp_adj, status=OrderStatus.PENDING)
            )
        elif ohlc['low'] == ohlc[f'last_{window}_low'] and len(open_long) < max_orders:
            # Place a long limit order
            entry = ohlc['low']
            orders.append(
                Order(order_date=ohlc['time'], side=OrderSide.LONG, entry=entry - entry_adj, sl=entry - atr, tp=entry + atr + tp_adj, status=OrderStatus.PENDING)
            )

    return orders


if __name__ == '__main__':
    # TODO: refactoring to support multiple currencies
    ccy_pair = 'EUR_USD'
    test_orders = run(instrument=ccy_pair, window=20, max_orders=4, entry_adj=0.0005, tp_adj=0, start_date='2014-01-01', end_date='2015-04-30')
    back_tester = BackTester(strategy='mean reversion', lot_size=10000)
    back_tester.print_stats(test_orders)

    df = pd.DataFrame([{'time': o.order_date, 'pnl': o.pnl * 10000} for o in test_orders])
    df['time'] = pd.to_datetime(df['time'])
    df = df.set_index('time')

    df[f'cumsum_{ccy_pair.lower()}'] = df['pnl'].cumsum()
    df[[f'cumsum_{ccy_pair.lower()}']].plot()
    plt.show()
