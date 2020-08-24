import logging
import queue
import threading
from collections import namedtuple
from datetime import datetime, date

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.backtester import BackTester
from src.db.ohlc_to_db import connect_to_db
from src.indicators import average_true_range, exponential_moving_average
from src.orders.order import Order, OrderStatus, OrderSide
from src.pricer import read_price_df

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


# 1. Read 1 hour price with 14days atr
# 2. Generate buy/sell signal when crossover
# 3. Simulate ticking price and placing/closing orders

logger = logging.getLogger(__name__)

OHLC = namedtuple("OHLC", "time open high low close")


def generate_signals(instrument: str = "GBP_USD", granularity: str = "H1", short_win: int = 16, long_win: int = 64,
                     start_date: datetime = datetime(2019, 1, 1, 0, 0, 0), end_date: datetime = datetime(2020, 1, 1, 0, 0, 0)) -> pd.DataFrame:
    df = read_price_df(instrument=instrument, granularity=granularity, start=start_date, end=end_date)
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


def retrieve_price(start_date: [datetime, date], end_date: [date, datetime]):
    import os
    basedir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(basedir + "/../db", 'db.sqlite')
    conn = connect_to_db(db_path)
    cur = conn.cursor()
    s = start_date.strftime('%Y-%m-%d')
    e = end_date.strftime('%Y-%m-%d')
    cur.execute("select * from gbpusd_ohlc where date(time) between ? and ?", (s, e))

    for row in cur.fetchall():
        yield row


class MaTrader:
    def __init__(self, events: queue.Queue, signals: list, running: bool = False):
        self.events = events
        self.orders = []
        self.signals = signals
        self.process_index = 0
        self.running = running

    def run(self):
        while self.running:
            try:
                item = self.events.get(timeout=0.01)
                if item is None:
                    continue

                try:
                    self.process_event(item)
                finally:
                    self.events.task_done()

            except queue.Empty:
                pass
            except Exception as ex:
                logger.exception(f'Error while processing item: [{ex}]')

    def process_event(self, ohlc):
        if self.process_index < len(self.signals) and ohlc.time > self.signals[self.process_index]['time']:
            filled_order = next((o for o in self.orders if o.is_open), None)
            if filled_order:
                if filled_order.is_long:
                    # close long filled order
                    if ohlc.open >= filled_order.entry:
                        logger.info(f"Closing long order when crossover with profit: {(ohlc.open - filled_order.entry) * 10000} pips at [{ohlc.time}]")
                        filled_order.close_with_win(ohlc.time, ohlc.open)
                    else:
                        logger.info(f"Closing long order when crossover with loss: {(ohlc.open - filled_order.entry) * 10000} pips at [{ohlc.time}]")
                        filled_order.close_with_loss(ohlc.time, ohlc.open)
                else:
                    # close short filled order
                    if ohlc.open <= filled_order.entry:
                        logger.info(f"Closing short order when crossover with profit: {(filled_order.entry - ohlc.open) * 10000} pips at [{ohlc.time}]")
                        filled_order.close_with_win(ohlc.time, ohlc.open)
                    else:
                        logger.info(f"Closing short order when crossover with loss: {(filled_order.entry - ohlc.open) * 10000} pips at [{ohlc.time}]")
                        filled_order.close_with_loss(ohlc.time, ohlc.open)

            is_long = self.signals[self.process_index]['positions'] == 1
            self.orders.append(Order(
                order_date=ohlc.time,
                side=OrderSide.LONG if is_long else OrderSide.SHORT,
                entry=ohlc.open,
                tp=ohlc.open + crossover_signals[self.process_index]['atr'] * 5 * (1 if is_long else -1),  # 5 times ATR
                status=OrderStatus.FILLED
            ))
            self.process_index += 1

        filled_order = next((o for o in self.orders if o.is_open), None)
        if filled_order:
            if filled_order.is_long:
                # buy order, low >= tp
                if ohlc.low >= filled_order.tp:
                    logger.info(f"Closing long order when profit target met: {(filled_order.tp - filled_order.entry) * 10000} pips at [{ohlc.time}]")
                    filled_order.close_with_win(ohlc[0], filled_order.tp)
            else:
                # sell order, high >= tp
                if ohlc.high <= filled_order.tp:
                    logger.info(f"Closing short order when profit target met: {(filled_order.entry - filled_order.tp) * 10000} pips at [{ohlc.time}]")
                    filled_order.close_with_win(ohlc[0], filled_order.tp)


if __name__ == '__main__':
    start = datetime(2010, 1, 1, 0, 0, 0)
    end = datetime(2020, 7, 31, 0, 0, 0)
    signals = generate_signals(start_date=start, end_date=end)
    signals.index = signals.index.strftime('%Y-%m-%d %H:%M:%S')
    signals.reset_index(level=0, inplace=True)

    crossover_signals = signals[signals.positions.isin([-1, 1])].to_dict('records')
    print(crossover_signals)

    events = queue.Queue()
    ma = MaTrader(events=events, signals=crossover_signals, running=True)

    for p in retrieve_price(start_date=start, end_date=end):
        events.put(OHLC(p[0], p[1], p[2], p[3], p[4]))

    threading.Thread(target=ma.run).start()

    events.join()

    ma.running = False

    BackTester().print_stats(ma.orders)

    stats = [
        {
            'open_time': o.order_date,
            'side': o.side,
            'entry': o.entry,
            'sl': o.sl,
            'tp': o.tp,
            'pnl': o.pnl * 10000,
            'close_time': o.last_update,
        }
        for o in ma.orders
    ]
    df = pd.DataFrame(stats)

    df.to_csv(r'C:\temp\stats.csv')
    plt.style.use('ggplot')
    chart_df = df[["open_time", "pnl"]]
    chart_df = chart_df.set_index('open_time')
    chart_df.cumsum().plot()
    plt.xticks(rotation=45)
    plt.subplots_adjust(bottom=0.2)
    plt.show()
