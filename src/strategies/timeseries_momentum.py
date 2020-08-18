from datetime import datetime
import numpy as np
from matplotlib import pyplot as plt
from src.pricer import read_price_df


# we formalize the momentum strategy by telling Python to take the mean log return over the
# last 15, 30, 60, and 120 minute bars to derive the position in the instrument.
# For example,
#     the mean log return for the last 15 minute bars gives the average value of the last 15 return observations.
#         1. If this value is positive, we go/stay long the traded instrument;
#         2. if it is negative we go/stay short.

if __name__ == '__main__':
    from_dt = datetime(2015, 1, 1)
    end_dt = datetime(2020, 3, 31)
    df = read_price_df(instrument='GBP_USD', granularity='D', start=from_dt, end=end_dt)
    print(df)
    df['returns'] = np.log(df['close'] / df['close'].shift(1))

    cols = []

    for momentum in [15, 30, 60, 120]:
        col = 'position_%s' % momentum
        df[col] = np.sign(df['returns'].rolling(momentum).mean())
        cols.append(col)

    strats = ['returns']

    for col in cols:
        strat = 'strategy_%s' % col.split('_')[1]
        df[strat] = df[col].shift(1) * df['returns']
        strats.append(strat)  # 23

    df[strats].dropna().cumsum().apply(np.exp).plot()
    plt.show()
