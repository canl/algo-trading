from datetime import datetime, timedelta

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.pricer import read_price_df
from src.orders.order import Order, OrderStatus

# Tested with real tick data
# Rules: Simple MA cross over strategy, can also be replaced with EMA
#   Define short and long window
#   Long condition:
#       when short window cross over long window from bottom
#   TP:
#       5 * atr
#   Exit:
#       when short window cross over long window from top
#
#   Short condition:
#       when short window cross over long window from top
#   TP:
#       5 * atr
#   Exit:
#       when short window cross over long window from bottom


short_window = 100
long_window = 350

last_date = datetime.today() - timedelta(days=1)
start_date = last_date - timedelta(days=3000)


def generate_signals():
    df = read_price_df(instrument='GBP_USD', granularity='D', start=start_date, end=last_date)

    df['long_short'] = 0
    df['short_mavg'] = df['close'].rolling(window=short_window, min_periods=1, center=False).mean()
    df['long_mavg'] = df['close'].rolling(window=long_window, min_periods=1, center=False).mean()
    df['long_short'][short_window:] = np.where(df['short_mavg'][short_window:] >= df['long_mavg'][short_window:], 1, 0)

    df['signal'] = df['long_short'].diff()
    print(df[['open', 'close', 'short_mavg', 'long_mavg', 'signal', 'long_short']])
    df.to_csv(r'C:\temp\prices.csv')
    return df


def plot(df):
    fig = plt.figure()
    ax1 = fig.add_subplot(111, ylabel='Price in $')

    df['close'].plot(ax=ax1, color='r', lw=2.)

    df[['short_mavg', 'long_mavg']].plot(ax=ax1, lw=2.)

    ax1.plot(df.loc[df.signal == 1.0].index, df.short_mavg[df.signal == 1.0], '^', markersize=10, color='m')
    ax1.plot(df.loc[df.signal == -1.0].index, df.short_mavg[df.signal == -1.0], 'v', markersize=10, color='k')

    plt.show()


def back_test():
    df = generate_signals()
    price_data = df.reset_index().to_dict('records')

    next_move = None
    orders = []
    for p in price_data:
        if not np.isnan(p.get('signal')) and p.get('signal') != 0:
            next_move = 'buy' if p.get('signal') == 1 else 'sell'
            continue

        if next_move:
            if orders:
                orders[-1] = Order(orders[-1].order_date, orders[-1].side, orders[-1].entry, status=OrderStatus.CLOSED,
                                   pnl=(p.get('close') - orders[-1].entry) * (1 if orders[-1].side == 'buy' else -1) * 10000)
            orders.append(Order(pd.to_datetime(p.get('time')), next_move, p.get('open'), status=OrderStatus.FILLED))
            next_move = None

    # plot(df)
    return orders


if __name__ == '__main__':
    orders = back_test()
    test_result = pd.DataFrame(
        {
            'date': [o.order_date for o in orders],
            'pnl': [o.pnl for o in orders],
        }
    ).set_index('date')
    test_result['cumsum'] = test_result['pnl'].cumsum()
    print(test_result)
    test_result['cumsum'].plot()
    plt.show()
