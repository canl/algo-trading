import argparse
import logging
import time

import numpy as np
import pandas as pd

from src.account.account_manager import AccountManager
from src.env import RUNNING_ENV
from src.finta.ta import TA
from src.orders.order import OrderSide
from src.orders.order_manager import OrderManager
from src.position_calculator import pos_size
from src.pricer import api_request, transform

logger = logging.getLogger(__name__)


class MaTrader:
    """
    Simple MA cross over strategy, can be used in either 1 hour or 1 day timeframe

    Rules:
        Maximum one oder allowed
          Define short and long window

          Long condition:
              when short window cross over long window from bottom
          TP:
              5 * atr
          Exit:
              when short window cross over long window from top

          Short condition:
              when short window cross over long window from top
          TP:
              5 * atr
          Exit:
              when short window cross over long window from bottom
    """

    def __init__(self, account: str, instruments: list, short_win: int = 16, long_win: int = 64, sl_pips: int = 50, wait_seconds: int = 0, live_run: bool = False):
        """
        Moving average cross over strategy
        :param account: account id
        :param instruments: trading instruments
        :param short_win: define short moving average
        :param long_win: define long moving average
        :param sl_pips: stop loss pips for calculating position size. Default to 50.
        :param wait_seconds: sleep for a number of seconds before run
        :param live_run: live or dry run, default to false
        """
        self.am = AccountManager(account)
        self.om = OrderManager(account)
        self.instruments = instruments
        self.short_win = short_win
        self.long_win = long_win
        self.sl_pips = sl_pips
        self.wait_seconds = wait_seconds
        self.live_run = live_run
        self.adjustment = 0  # 0 pips, no adjustment

    def run(self):
        # Wait for a few seconds, as in Python anywhere we can only schedule the job by minute
        logger.info(f"Waiting for {self.wait_seconds} seconds")
        time.sleep(self.wait_seconds)
        for instrument in self.instruments:
            logger.info(f"Reading {instrument} hourly OHLC feed for last 10 days")
            df = self.check_for_signals(instrument=instrument)
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', 200)
            logger.info(f"\n{df.tail(10)}")

            last_pos = df['position'].iloc[-1]
            if last_pos == 0:
                logger.info(f"No signal detected for instrument: {instrument}!")
            else:
                if self.live_run:
                    logger.info(f"Closing open trade for {instrument}...")
                    matched_orders = self.om.get_open_trades()
                    matched_instrument = [o for o in matched_orders if o.get('instrument') == instrument]
                    for trade in matched_instrument:
                        logger.info(f"Closing order {trade['id']} due to crossover")
                        self.om.close_trade(trade['id'])

                    pending_orders = self.om.get_pending_orders()
                    matched_instrument = [o for o in pending_orders if o.get('instrument') == instrument]
                    for trade in matched_instrument:
                        logger.info(f"Cancelling order {trade['id']} due to crossover")
                        self.om.cancel_order(trade['id'])

                    last_atr = df['atr'].iloc[-1]
                    last_close = df['close'].iloc[-1]
                    units = self.get_pos_size(instrument=instrument)
                    one_lot = 100000

                    logger.info(f"Placing {'long' if last_pos == 1 else 'short'} limit order for {instrument} @ {last_close - self.adjustment * last_pos}")
                    self.om.place_limit_order(
                        instrument=instrument,
                        side=OrderSide.LONG if last_pos == 1 else OrderSide.SHORT,
                        units=units * one_lot,
                        price=last_close - self.adjustment * last_pos,
                        sl=last_close - (3 * last_atr) * last_pos,
                        tp=last_close + (5 * last_atr) * last_pos
                    )
                else:
                    logger.info("Dry run only, no order will be placed")

    def get_pos_size(self, instrument):
        nav = int(self.am.nav)
        # Default sl pips to 30
        return pos_size(account_balance=nav, risk_pct=0.02, sl_pips=self.sl_pips, instrument=instrument, account_ccy=self.am.currency)

    def check_for_signals(self, instrument: str) -> pd.DataFrame:
        param = {
            "count": 240,
            "granularity": "H1"
        }
        resp = api_request(instrument=instrument, p=param)
        df = pd.DataFrame(transform(resp['candles'])).set_index('time')
        df['ema_short'] = TA.EMA(df, period=self.short_win)
        df['ema_long'] = TA.EMA(df, period=self.long_win)
        df['atr'] = TA.ATR(df, 14)
        df['signal'] = 0.0
        # Create a 'signal' (invested or not invested) when the short moving average crosses the long
        # moving average, but only for the period greater than the shortest moving average window
        df['signal'][self.short_win:] = np.where(df['ema_short'][self.short_win:] > df['ema_long'][self.short_win:], 1.0, 0.0)
        # Take the difference of the signals in order to generate actual trading orders
        df['position'] = df['signal'].diff()

        # df.to_csv(r'C:\temp\signals.csv')
        return df


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Moving Average Crossover Trading Strategy")
    parser.add_argument('--instruments', help="specify trading instruments", action='store', type=str)
    parser.add_argument('--waitSeconds', help="Wait for a number of seconds before run", action='store', type=int, default=0)
    parser.add_argument('--liveRun', help="Flag to indicate dry or live run", action='store_true', default=False)
    parser.add_argument('--env', action="store", dest="env", default='practice')
    parser.add_argument('--accountName', action="store", dest='accountName', default='primary')

    args = parser.parse_args()
    if not args.instruments:
        raise ValueError("Missing instruments argument")

    if args.env == 'live':
        RUNNING_ENV.load_config('live')

    traded_instruments = args.instruments.split(',')

    trader = MaTrader(account='primary', instruments=traded_instruments, sl_pips=30, wait_seconds=args.waitSeconds, live_run=args.liveRun)
    trader.run()
