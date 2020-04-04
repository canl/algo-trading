from datetime import datetime, timedelta

import matplotlib.pyplot as plt
import numpy as np

from src.common import read_price_df

# Rules: Simple MA cross over strategy, can also be replaced with EMA
#   1. Define short and long window
#   2. Buy: when short window cross over long window from bottom
#   3. Sell: when short window cross over long window from top


short_window = 20
long_window = 50

last_date = datetime.today() - timedelta(days=1)
start_date = last_date - timedelta(days=500)


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


if __name__ == '__main__':
    df_prices = generate_signals()
    plot(df_prices)
