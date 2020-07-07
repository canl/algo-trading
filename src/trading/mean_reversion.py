import argparse
import logging
import queue
import threading
from datetime import datetime, timezone, timedelta
import pandas as pd

from src.account.account_manager import AccountManager
from src.env import RUNNING_ENV
from src.event import TickEvent
from src.order_utils.order import OrderSide
from src.order_utils.order_manager import OrderManager
from src.position_calculator import pos_size
from src.pricing.stream_price_event import StreamPriceEvent
from src.utils.timeout_cache import cache

logger = logging.getLogger(__name__)


class MeanReversionTrader:
    """
    A simple mean reversion strategy implementation
    which is around 70% of the time.

    Rules:

        Entry:
            1. Place a long limit order if:
                1) price breaks 20 days low
                2) RSI between 30 to 70
                3) with entry price as: 20 days low - 5pips adj
            2. Place a short limit order if:
                1) price breaks 20 days high
                2) RSI between 30 to 70
                3) with entry price as: 20 days high + 5pips adj
            3. Cancel the order if it cannot be filled in 3 hours
            4. Maximum 4 orders allowed for each long or short direction. Do not want to against the trend

        SL:
            long: entry - 14 days ATR
            Short: entry + 14 days ATR

        TP:
            Long: entry + 14 days ATR
            Short: entry - 14 days ATR

        Position Size:
            %2 risk

    """

    def __init__(self, events: queue.Queue, feeds_loc: str, max_orders: int = 4, account: str = 'mt4',
                 entry_adj: float = 0.0005, expiry_hours: int = 3, risk_pct: float = 0.02, live_run: bool = False):

        """
        Mean reversion auto trader
        :param events: Tick price event queue
        :param feeds_loc: Location to read daily price feed
        :param max_orders: maximum order allowed for LONG or SHORT
        :param account: Oanda account name: primary or mt4
        :param entry_adj: entry adjustment, default to 5 pips
        :param expiry_hours: expiry hours for GTD trades (Good Till Date)
        :param risk_pct: risk percentage for each trade
        :param live_run: live or dry run, default to false
        """
        self.events = events
        self.feeds_loc = feeds_loc
        self.max_orders = max_orders
        self.account_id = RUNNING_ENV.get_account(account)
        self.entry_adj = entry_adj
        self.expiry_hours = expiry_hours
        self.risk_pct = risk_pct
        self.om = OrderManager(account)
        self.am = AccountManager(account)
        self.live_run = live_run

    def run(self):
        while True:
            e = self.events.get()
            self.calculate_signals(event=e)

    def calculate_signals(self, event: TickEvent):
        logger.info(f'Received event: {event}')
        df = self.read_daily_price_feed(event.instrument)
        last_20_high = df.iloc[-1]['last_20_high']
        last_20_low = df.iloc[-1]['last_20_low']
        rsi = df.iloc[-1]['rsi']
        atr = df.iloc[-1]['atr']
        logger.info(f"last high: {last_20_high}, last low: {last_20_low}, rsi: {rsi}, atr: {atr}")

        buy_signal = float(event.ask) <= last_20_low and 30 <= rsi <= 70
        sell_signal = float(event.bid) >= last_20_high and 30 <= rsi <= 70

        if buy_signal or sell_signal:
            side = OrderSide.LONG if buy_signal else OrderSide.SHORT
            logger.info(f"{side} signal detected!")
            if self.live_run:
                if self.exceed_maximum_orders(instrument=event.instrument, side=side):
                    logger.warning(f"Exceeded maximum allowed order side: [{self.max_orders}]!")
                    return
                try:
                    self.place_order(event.instrument, side, last_20_high, last_20_low, atr)
                except Exception as ex:
                    logger.error(f'Failed to place order for instrument: {event.instrument} with error {ex}')
            else:
                logger.info("Dry run for testing only, not doing anything!")

    @cache(seconds=3600)
    def read_daily_price_feed(self, instrument):
        return pd.read_csv(f'{self.feeds_loc}/{instrument.lower()}_d.csv').set_index('time')

    def get_open_trades(self, instrument: str, side: str) -> list:
        """
        Retrieve open trades by currency pair and order side
        :param instrument: OrderType
        :param side: OrderSide
        :return: list
        """
        open_trades = self.om.get_open_trades()
        return [
            o for o in open_trades if o.get('instrument') == instrument and (int(o.get('initialUnits')) > 0 if side == OrderSide.LONG else int(o.get('initialUnits')) < 0)
        ]

    def place_order(self, instrument: str, side: str, last_20_high: float, last_20_low: float, atr: float):
        logger.info(f"Placing [{side}] order for instrument: [{instrument}]")
        is_long = side == OrderSide.LONG
        entry = last_20_low - self.entry_adj if is_long else last_20_high + self.entry_adj
        sl = entry - atr if is_long else entry + atr
        tp = entry + atr if is_long else entry - atr

        now_utc = datetime.now(timezone.utc)
        expiry_time = (now_utc + timedelta(hours=self.expiry_hours)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        units = self.calculate_position_size(instrument=instrument, atr=atr)
        one_lot = 100000
        self.om.place_limit_order(instrument=instrument, side=side, units=one_lot * units, price=entry, tp=tp, sl=sl, expiry=expiry_time)
        logger.info("Order successfully placed")

    def calculate_position_size(self, instrument, atr):
        nav = self.am.nav
        special_instruments = ('XAU', 'JPY', 'BCO')  # special_instruments' pip is the second place after the decimal (0.01) rather than the fourth (0.0001).
        sl_pips = atr * (10000 if any(inst in instrument for inst in special_instruments) else 100)
        return pos_size(account_balance=nav, risk_pct=self.risk_pct, sl_pips=sl_pips, instrument=instrument, account_ccy='GBP')

    def exceed_maximum_orders(self, instrument: str, side: str) -> bool:
        opens = self.get_open_trades(instrument, side)
        return len(opens) >= self.max_orders


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Mean Reversion Trading Strategy")
    parser.add_argument('--liveRun', help="Flag to indicate dry or live run", action='store_true', default=False)
    parser.add_argument('--env', action="store", dest="env", default='practice')
    parser.add_argument('--accountName', action="store", dest='accountName', default='mt4')
    parser.add_argument('--priceDir', action="store", dest="priceDir", default='c:/temp/prices')
    args = parser.parse_args()

    price_events = queue.Queue()
    t = MeanReversionTrader(events=price_events, feeds_loc=args.priceDir, account=args.accountName, live_run=args.liveRun)

    instruments = [
        'GBP_USD', 'EUR_USD', 'AUD_USD', 'USD_SGD', 'USD_JPY',
        'GBP_AUD', 'USD_CAD', 'EUR_GBP', 'USD_CHF', 'BCO_USD'
    ]
    spe = StreamPriceEvent(instruments, price_events)
    price_thread = threading.Thread(target=spe.start)
    price_thread.start()

    t.run()
