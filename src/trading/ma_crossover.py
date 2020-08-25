from datetime import datetime, timedelta
import logging
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.account.account_manager import AccountManager
from src.indicators import exponential_moving_average, average_true_range
from src.orders.order_manager import OrderManager
from src.pricer import read_price_df, api_request, transform

# Rules: Simple MA cross over strategy, can also be replaced with EMA
#   1. Define short and long window
#   2. Buy: when short window cross over long window from bottom
#   3. Sell: when short window cross over long window from top
from src.strategies.ma_crossover import generate_signals

logger = logging.getLogger(__name__)


class MaTrader:
    def __init__(self, account: str, short_win: int = 16, long_win: int = 64):
        self.am = AccountManager(account)
        self.om = OrderManager(account)
        self.short_win = short_win
        self.long_win = long_win
        self.cache_db = self.initialize_cache()

    def initialize_cache(self) -> dict:
        pass

    def check_for_signals(self):
        param = {
            "count": 240,
            "granularity": "H1"
        }
        resp = api_request(instrument='GBP_USD', p=param)
        df = pd.DataFrame(transform(resp['candles'])).set_index('time')
        df['ema_short'] = exponential_moving_average(df, self.short_win)
        df['ema_long'] = exponential_moving_average(df, self.long_win)
        df['atr'] = average_true_range(df, 14)
        df['signal'] = 0.0
        # Create a 'signal' (invested or not invested) when the short moving average crosses the long
        # moving average, but only for the period greater than the shortest moving average window
        df['signal'][self.short_win:] = np.where(df['ema_short'][self.short_win:] > df['ema_long'][self.short_win:], 1.0, 0.0)
        # Take the difference of the signals in order to generate actual trading orders
        df['positions'] = df['signal'].diff()

        df.to_csv(r'C:\temp\signals.csv')

        print(df)


if __name__ == '__main__':
    trader = MaTrader('primary')
    trader.check_for_signals()
