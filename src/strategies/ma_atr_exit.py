from datetime import datetime
from functools import partial

import pandas as pd
from matplotlib import pyplot as plt

from src.backtester import BackTester
from src.pricer import read_price_df
from src.finta.ta import TA
from src.orders.order import Order, OrderStatus, OrderSide


# Strategy rules:
#   Buy signal:
#       1. close price cross 50 EMA from the bottom
#       2. Price above 200 EMA
#       3. SL 1.5 * ATR
#       4. TP 3 * ATR
#   sell signal:
#       1. close price cross 50 EMA from the bottom
#       2. Price above 200 EMA
#       3. SL 1.5 * ATR
#       4. TP 3 * ATR


def signal(short_win, long_win, row):
    if row[f'smma_{long_win}'] < row[f'smma_{short_win}'] < row['close'] and row['open'] < row[f'smma_{short_win}']:
        return 1

    if row[f'smma_{long_win}'] > row[f'smma_{short_win}'] > row['close'] and row['open'] > row[f'smma_{short_win}']:
        return -1

    return 0


def plot(df):
    fig = plt.figure()
    ax1 = fig.add_subplot(111, ylabel='Price in $')

    df['close'].plot(ax=ax1, color='r', lw=2.)

    df[['ema_50', 'ema_200']].plot(ax=ax1, lw=2.)

    ax1.plot(df.loc[df.signal == 1.0].index, df.ema_50[df.signal == 1.0], '^', markersize=10, color='m')
    ax1.plot(df.loc[df.signal == -1.0].index, df.ema_50[df.signal == -1.0], 'v', markersize=10, color='k')

    plt.show()


def sample_data(instrument: str, start: datetime, end: datetime, short_window: int = 100, long_window: int = 350) -> pd.DataFrame:
    price_feed = read_price_df(instrument=instrument, granularity='D', start=start, end=end)
    price_feed[f'smma_{short_window}'] = TA.SMMA(price_feed, period=short_window, adjust=False)
    price_feed[f'smma_{long_window}'] = TA.SMMA(price_feed, period=long_window, adjust=False)
    price_feed['atr'] = TA.ATR(price_feed[['high', 'low', 'close']])
    price_feed['signal'] = price_feed.apply(partial(signal, short_window, long_window), axis=1)
    return price_feed


def create_orders(ohlc: pd.DataFrame, sl_multiplier: float, tp_multiplier: float) -> list:
    price_data = ohlc.reset_index().to_dict('records')
    orders = []
    next_buy = False
    next_sell = False
    for el in price_data:
        if next_buy:
            orders.append(
                Order(order_date=el['time'], side=OrderSide.LONG, entry=el['open'], sl=el['open'] - el['atr'] * sl_multiplier,
                      tp=el['open'] + el['atr'] * tp_multiplier, status=OrderStatus.FILLED))
            next_buy = False
        elif next_sell:
            orders.append(
                Order(order_date=el['time'], side=OrderSide.SHORT, entry=el['open'], sl=el['open'] + el['atr'] * sl_multiplier,
                      tp=el['open'] - el['atr'] * tp_multiplier, status=OrderStatus.FILLED))
            next_sell = False

        if el['signal'] == 1:
            next_buy = True
        elif el['signal'] == -1:
            next_sell = True

    return orders


if __name__ == '__main__':
    dfs = []
    instruments = [('XAU_USD', 100), ('GBP_USD', 10000), ('EUR_USD', 10000), ('GBP_AUD', 10000),
                   ('USD_JPY', 1000), ('AUD_USD', 10000), ('USD_SGD', 10000)]
    back_tester = BackTester(strategy='MA with ATR exit')
    for instrument, lot_size in instruments:
        df = sample_data(instrument=instrument, start=datetime(2005, 1, 1), end=datetime(2020, 3, 31), short_window=50, long_window=200)
        orders = create_orders(df, 1.5, 3)
        back_tester.lot_size = lot_size
        print(f"{'-' * 10} {instrument} {'-' * 10}")
        p = back_tester.run(df, orders, suffix=f'_{instrument}')
        dfs.append(p)
    back_tester.plot_chart(dfs)
