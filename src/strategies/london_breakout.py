import logging
import math
from datetime import datetime

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from src.backtester import BackTester
from src.pricer import read_price_df
from src.finta.utils import trending_up, trending_down
from src.indicators import wma
from src.orders.order import OrderStatus, Order

# Rules:
#   1. Find the high and low between 00:00 to 08:00 UTC
#   2. Place a buy stop order 2 pips above high with stop loss
#       Buy Stop:
#       At: (Maximum Price + 2 pips)
#       T/P: (Maximum Price + (Maximum Price - Minimum Price))
#       S/L: (Minimum Price - 2 pips)
#   3. Place a sell stop order 2 pips below low
#       Sell Stop:
#       At (Minimum Price - 2 pips)
#       T/P (Minimum Price - (Maximum Price - Minimum Price))
#       S/L (Maximum Price + 2 pips)
#   4. Inactive pending orders will expire next trading day at 08:00 AM (GMT).


plt.style.use('ggplot')


def plot_performance(strats: list, tp_adjustments: tuple):
    df = pd.DataFrame({'date': [el.order_date for el in strats[0]]}).set_index('date')
    for idx, adj in enumerate(tp_adjustments):
        df[f'pnl_{adj}'] = [round(el.pnl, 4) for el in strats[idx]]

    grp_by = df.groupby(['date']).sum()
    for adj in tp_adjustments:
        grp_by[f'cumsum_{adj}'] = grp_by[f'pnl_{adj}'].cumsum()

    logging.info(grp_by)
    grp_by[[header for header in grp_by.columns if header.startswith('cumsum')]].plot()
    plt.show()


def create_orders(price_df: pd.DataFrame, adj: float = 0.0, verify_ema: bool = False, momentum_signal: bool = False):
    """
    create and fill limit orders
    :param price_df: ohlc pd.DataFrame
    :param adj: float, parameters to adjust the SL or TP
    :param verify_ema: bool flag, confirm with EMA indicator
    :param momentum_signal: bool flag, confirm with momentum indicator
    :return:
    """
    orders = []
    for time, ohlc in price_df.to_dict('index').items():
        # x - (y - x) = 2x - y
        buy_entry = ohlc['last_8_high']
        sell_entry = ohlc['last_8_low']
        if math.isnan(buy_entry):
            continue

        if time.hour == 8:
            for order in [el for el in orders if el.status == OrderStatus.PENDING]:
                order.status = OrderStatus.CANCELLED

            buy_tp = round(buy_entry * 2 - sell_entry + adj, 5)
            buy_sl = sell_entry
            sell_tp = round(sell_entry * 2 - buy_entry - adj, 5)
            sell_sl = buy_entry

            if momentum_signal:
                if ohlc['trend'] == 'up':
                    orders.append(Order(time, 'long', buy_entry, buy_sl, buy_tp, 0, OrderStatus.PENDING))
                elif ohlc['trend'] == 'down':
                    orders.append(Order(time, 'short', sell_entry, sell_sl, sell_tp, 0, OrderStatus.PENDING))

            elif verify_ema:
                if ohlc['low'] >= ohlc['ema']:
                    orders.append(Order(time, 'long', buy_entry, buy_sl, buy_tp, 0, OrderStatus.PENDING))
                elif ohlc['high'] <= ohlc['ema']:
                    orders.append(Order(time, 'short', sell_entry, sell_sl, sell_tp, 0, OrderStatus.PENDING))
            else:
                orders.append(Order(time, 'long', buy_entry, buy_sl, buy_tp, 0, OrderStatus.PENDING))
                orders.append(Order(time, 'short', sell_entry, sell_sl, sell_tp, 0, OrderStatus.PENDING))

        for order in orders:
            # Try to fill pending orders
            if order.status == OrderStatus.PENDING:
                if order.is_long:
                    if ohlc['high'] > order.entry:  # buy order filled
                        order.fill(time)
                elif order.is_short:
                    if ohlc['low'] < order.entry:  # sell order filled
                        order.fill(time)

    logging.info(f'{len(orders)} orders created.')
    return orders


if __name__ == "__main__":
    from_date = datetime(2016, 1, 1)
    last_date = datetime(2020, 8, 14)

    logging.info(f'Reading date between {from_date} and {last_date}')
    ohlc = read_price_df(instrument='GBP_USD', granularity='H1', start=from_date, end=last_date)

    ohlc['last_8_high'] = ohlc['high'].rolling(8).max()
    ohlc['last_8_low'] = ohlc['low'].rolling(8).min()
    ohlc['diff_pips'] = (ohlc['last_8_high'] - ohlc['last_8_low']) * 10000
    # ohlc['returns'] = np.log(ohlc['close'] / ohlc['close'].shift(1))

    logging.info(ohlc[['open', 'high', 'low', 'close', 'last_8_high', 'last_8_low', 'diff_pips']])
    back_tester = BackTester(strategy='London Breakout')
    dfs = []
    for adj in (0, 5, 10,):
        orders = create_orders(ohlc, adj=adj / 10000)
        dfs.append(back_tester.run(ohlc, orders, print_stats=True, suffix=f'_{adj}'))

    for period in (14, 28, 50):
        ohlc['ema'] = wma(ohlc['close'], period)
        orders = create_orders(ohlc, adj=5 / 10000, verify_ema=True)
        dfs.append(back_tester.run(ohlc, orders, print_stats=True, suffix=f'_ema_{period}'))

    for period in (30, 60, 120):
        ohlc['trend_up'] = trending_up(ohlc['close'], period)
        ohlc['trend_down'] = trending_down(ohlc['close'], period)

        conditions = [
            ohlc['trend_up'] & ~ohlc['trend_down'],
            ~ohlc['trend_up'] & ohlc['trend_down'],
            ~ohlc['trend_up'] & ~ohlc['trend_down'],
        ]
        choices = ['up', 'down', 'no trend']

        ohlc['trend'] = np.select(conditions, choices, default='no trend')

        # ohlc['momentum_signal'] = np.sign(ohlc['returns'].rolling(period).mean())
        orders = create_orders(ohlc, adj=5 / 10000, momentum_signal=True)
        dfs.append(back_tester.run(ohlc, orders, print_stats=True, suffix=f'_momentum_{period}'))

    back_tester.plot_chart(dfs)
