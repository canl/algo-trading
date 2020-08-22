import queue
from datetime import datetime, timedelta

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.db.ohlc_to_db import connect_to_db
from src.finta.ta import TA
from src.indicators import average_true_range, exponential_moving_average
from src.pricer import read_price_df
from src.orders.order import Order, OrderStatus


# Tested with real tick data
# Rules: Simple MA cross over strategy, can be used in either 1 hour or 1 day timeframe
# Maximum one oder allowed
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


# short_window = 100
# long_window = 350
#
# last_date = datetime.today() - timedelta(days=1)
# start_date = last_date - timedelta(days=3000)


# 1. Read 1 hour price with standard atr
# 2. Generate buy/sell signal when crossover
# 3. Simulate ticking price and placing orders

def generate_signals(instrument: str = "GBP_USD", short_win: int = 16, long_win: int = 64,
                     start_date: datetime = datetime(2019, 1, 1, 0, 0, 0), end_date: datetime = datetime(2020, 1, 1, 0, 0, 0)) -> pd.DataFrame:
    df = read_price_df(instrument=instrument, granularity='H1', start=start_date, end=end_date)
    df['ema_short'] = exponential_moving_average(df, short_win)
    df['ema_long'] = exponential_moving_average(df, long_win)
    df['atr'] = average_true_range(df, 14)
    df['signal'] = 0.0
    # Create a 'signal' (invested or not invested) when the short moving average crosses the long
    # moving average, but only for the period greater than the shortest moving average window
    df['signal'][short_win:] = np.where(df['ema_short'][short_win:] > df['ema_long'][short_win:], 1.0, 0.0)
    # Take the difference of the signals in order to generate actual trading orders
    df['positions'] = df['signal'].diff()
    return df


def retrieve_price():
    import os
    basedir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(basedir + "/../db", 'db.sqlite')
    conn = connect_to_db(db_path)
    cur = conn.cursor()
    cur.execute("select * from gbp_ohlc where date(time) between '2020-01-01' and '2020-07-31'")

    for row in cur.fetchall():
        yield row


price_events = queue.Queue()

if __name__ == '__main__':
    signals = generate_signals(start_date=datetime(2020, 1, 1, 0, 0, 0), end_date=datetime(2020, 7, 31, 0, 0, 0))
    # signals.to_csv(r"C:\temp\signals-2.csv")
    print(signals[signals.positions != 0])

    for ohlc in retrieve_price():
        price_events.put(ohlc)
