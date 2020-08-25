import logging

import numpy as np
import pandas as pd

from src.account.account_manager import AccountManager
from src.indicators import exponential_moving_average, average_true_range
from src.orders.order import OrderSide
from src.orders.order_manager import OrderManager
from src.pricer import api_request, transform

# Rules: Simple MA cross over strategy, can be used in either 1 hour or 1 day timeframe
# Maximum one oder allowed
#   Define short and long window
#
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

logger = logging.getLogger(__name__)


class MaTrader:
    def __init__(self, account: str, instruments: list, short_win: int = 16, long_win: int = 64):
        """
        Moving average cross over strategy
        :param account: account id
        :param instruments: trading instruments
        :param short_win: define short moving average
        :param long_win:  define long moving average
        """
        self.am = AccountManager(account)
        self.om = OrderManager(account)
        self.instruments = instruments
        self.short_win = short_win
        self.long_win = long_win

    def run(self):
        for instrument in self.instruments:
            logger.info(f"Reading hourly OHLC feed for last 10 days")
            df = self.check_for_signals(instrument=instrument)
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', 200)
            logger.info(df.tail(10))

            last_pos = df['position'].iloc[-1]
            if last_pos == 0:
                logger.info("No signal detected!")
                return

            logger.info(f"Closing open trade for {instrument}...")
            matched_orders = self.om.get_open_trades()
            matched_instrument = [o for o in matched_orders if o.get('instrument') == instrument]
            for trade in matched_instrument:
                self.om.close_trade(trade['id'])

            last_atr = df['atr'].iloc[-1]
            last_close = df['close'].iloc[-1]
            if last_pos == 1:
                logger.info(f"Placing long market order for {instrument}")
                self.om.place_market_order(instrument=instrument, side=OrderSide.LONG, units=100000, tp=last_close + 5 * last_atr)
            else:
                logger.info(f"Placing short market order for {instrument}")
                self.om.place_market_order(instrument=instrument, side=OrderSide.SHORT, units=100000, tp=last_close - 5 * last_atr)

    def check_for_signals(self, instrument: str) -> pd.DataFrame:
        param = {
            "count": 240,
            "granularity": "H1"
        }
        resp = api_request(instrument=instrument, p=param)
        df = pd.DataFrame(transform(resp['candles'])).set_index('time')
        df['ema_short'] = exponential_moving_average(df, self.short_win)
        df['ema_long'] = exponential_moving_average(df, self.long_win)
        df['atr'] = average_true_range(df, 14)
        df['signal'] = 0.0
        # Create a 'signal' (invested or not invested) when the short moving average crosses the long
        # moving average, but only for the period greater than the shortest moving average window
        df['signal'][self.short_win:] = np.where(df['ema_short'][self.short_win:] > df['ema_long'][self.short_win:], 1.0, 0.0)
        # Take the difference of the signals in order to generate actual trading orders
        df['position'] = df['signal'].diff()

        # df.to_csv(r'C:\temp\signals.csv')
        return df


if __name__ == '__main__':
    trader = MaTrader(account='primary', instruments=['GBP_USD'])
    trader.check_for_signals(instrument='GBP_USD')
    trader.run()
