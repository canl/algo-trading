import argparse
import logging
import queue
import threading
import time
from datetime import datetime, timezone, timedelta
import json
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
            4. Maximum 4 orders allowed for each long or short direction. 10pips between orders (Do not want to against the trend)

        SL:
            long: entry - 14 days ATR
            Short: entry + 14 days ATR

        TP:
            Long: entry + 14 days ATR
            Short: entry - 14 days ATR

        Position Size:
            %2 risk

    """

    SPECIAL_INSTRUMENTS = ('XAU', 'JPY', 'BCO')  # special_instruments' pip is the second place after the decimal (0.01) rather than the fourth (0.0001).

    def __init__(self, events: queue.Queue, instruments: list, feeds_loc: str, max_orders: int = 4, account: str = 'mt4',
                 entry_adj: float = 0.0005, adj_btw_orders: float = 0.001, expiry_hours: int = 3, risk_pct: float = 0.02,
                 live_run: bool = False, heartbeat: int = 1):

        """
        Mean reversion auto trader
        :param events: Tick price event queue
        :param instruments: list of currency pairs
        :param feeds_loc: Location to read daily price feed
        :param max_orders: maximum order allowed for LONG or SHORT
        :param account: Oanda account name: primary or mt4
        :param entry_adj: entry adjustment, default to 5 pips
        :param adj_btw_orders: entry adjustment between orders, default to 10 pips
        :param expiry_hours: expiry hours for GTD trades (Good Till Date)
        :param risk_pct: risk percentage for each trade
        :param live_run: live or dry run, default to false
        """
        self.events = events
        self.instruments = instruments
        self.feeds_loc = feeds_loc
        self.max_orders = max_orders
        self.account_id = RUNNING_ENV.get_account(account)
        self.entry_adj = entry_adj
        self.adj_btw_orders = adj_btw_orders
        self.expiry_hours = expiry_hours
        self.risk_pct = risk_pct
        self.om = OrderManager(account)
        self.am = AccountManager(account)
        self.live_run = live_run
        self.heartbeat = heartbeat
        # Order stats initialization
        self.cache = self.initialize_cache()

    def initialize_cache(self) -> dict:
        logger.info("Initialize cache db ...")
        matched_orders = self.om.get_open_trades()
        pending_orders = self.om.get_pending_orders()

        res = {}
        for instrument in self.instruments:
            matched_instruments = [o for o in matched_orders if o.get('instrument') == instrument]
            pending_instruments = [o for o in pending_orders if o.get('instrument') == instrument and o.get('type') not in ('TAKE_PROFIT', 'STOP_LOSS')]

            matched_long = len([o for o in matched_instruments if int(float(o.get('initialUnits'))) > 0]) if matched_instruments else 0
            matched_short = len([o for o in matched_instruments if int(float(o.get('initialUnits'))) < 0]) if matched_instruments else 0

            pending_long = len([o for o in pending_instruments if int(float(o.get('units'))) > 0]) if pending_instruments else 0
            pending_short = len([o for o in pending_instruments if int(float(o.get('units'))) < 0]) if pending_instruments else 0

            res[instrument] = {
                OrderSide.LONG: matched_long + pending_long,
                OrderSide.SHORT: matched_short + pending_short,
                'last_buy': None,
                'last_sell': None
            }

        logging.info(f"Complete Cache DB initialization:\n{json.dumps(res, indent=2)}")
        return res

    def run(self):
        """
            Carries out an infinite while loop that polls the
            events queue and directs each event to either the
            strategy component of the execution handler. The
            loop will then pause for "heartbeat" seconds and
            continue.
        """
        while True:
            e = self.events.get()
            self.calculate_signals(event=e)
            time.sleep(self.heartbeat)

    def calculate_signals(self, event: TickEvent):
        logger.info(f'Received event: {event}')
        df = self.read_daily_price_feed(event.instrument)
        last_20_high = df.iloc[-1]['last_20_high']
        last_20_low = df.iloc[-1]['last_20_low']
        rsi = df.iloc[-1]['rsi']
        atr = df.iloc[-1]['atr']
        logger.info(f"last high: {last_20_high}, last low: {last_20_low}, rsi: {rsi}, atr: {atr}")

        last_buy = self.cache[event.instrument]['last_buy']
        last_sell = self.cache[event.instrument]['last_sell']
        buy_threshold = last_buy - self.adj_btw_orders if last_buy else last_20_low
        sell_threshold = last_sell + self.adj_btw_orders if last_sell else last_20_high

        buy_signal = float(event.ask) <= buy_threshold and 30 <= rsi <= 70
        sell_signal = float(event.bid) >= sell_threshold and 30 <= rsi <= 70

        if buy_signal or sell_signal:
            side = OrderSide.LONG if buy_signal else OrderSide.SHORT
            logger.info(f"{side} signal detected for instrument [{event.instrument}]!")
            logging.info(f"Cache DB state:\n{json.dumps(self.cache[event.instrument], indent=2)}")
            if side == OrderSide.LONG:
                logger.info(f"algo trading criteria: ask price {event.ask} <= buy_threshold {buy_threshold}, rsi {rsi} between 30 and 70")
            else:
                logger.info(f"algo trading criteria: bid price {event.bid} >= sell_threshold {sell_threshold}, rsi {rsi} between 30 and 70")

            if self.live_run:
                if self.exceed_maximum_orders(instrument=event.instrument, side=side):
                    logger.warning(f"Exceeded maximum allowed order side: [{self.max_orders}]!")
                    return
                try:
                    self.place_order(event.instrument, side, float(event.bid), float(event.ask), atr)
                    self.cache[event.instrument][side] += 1
                    if side == OrderSide.LONG:
                        self.cache[event.instrument]['last_buy'] = float(event.bid)
                    else:
                        self.cache[event.instrument]['last_sell'] = float(event.ask)
                except Exception as ex:
                    logger.error(f'Failed to place order for instrument: {event.instrument} with error {ex}')
            else:
                logger.info("Dry run for testing only, not doing anything!")

    @cache(seconds=3600)
    def read_daily_price_feed(self, instrument):
        return pd.read_csv(f'{self.feeds_loc}/{instrument.lower()}_d.csv').set_index('time')

    def place_order(self, instrument: str, side: str, bid: float, ask: float, atr: float):
        price_precision = 3 if self._has_special_instrument(instrument) else 5
        logger.info(f"Placing [{side}] order for instrument: [{instrument}]")
        is_long = side == OrderSide.LONG
        multiplier = 100 if self._has_special_instrument(instrument) else 1
        entry = bid - self.entry_adj * multiplier if is_long else ask + self.entry_adj * multiplier
        sl = entry - atr if is_long else entry + atr
        tp = entry + atr if is_long else entry - atr

        now_utc = datetime.now(timezone.utc)
        expiry_time = (now_utc + timedelta(hours=self.expiry_hours)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        units = self.calculate_position_size(instrument=instrument, atr=atr)
        one_lot = 100000
        self.om.place_limit_order(
            instrument=instrument,
            side=side,
            units=one_lot * units,
            price=round(entry, price_precision),
            tp=round(tp, price_precision),
            sl=round(sl, price_precision),
            expiry=expiry_time
        )
        logger.info("Order successfully placed")

    def calculate_position_size(self, instrument, atr):
        nav = int(float(self.am.nav))
        sl_pips = atr * (100 if self._has_special_instrument(instrument) else 10000)
        return pos_size(account_balance=nav, risk_pct=self.risk_pct, sl_pips=sl_pips, instrument=instrument, account_ccy='GBP')

    def exceed_maximum_orders(self, instrument: str, side: str) -> bool:
        return self.cache[instrument][side] >= self.max_orders

    def _has_special_instrument(self, instrument):
        return any(inst in instrument for inst in self.SPECIAL_INSTRUMENTS)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Mean Reversion Trading Strategy")
    parser.add_argument('--liveRun', help="Flag to indicate dry or live run", action='store_true', default=False)
    parser.add_argument('--env', action="store", dest="env", default='practice')
    parser.add_argument('--accountName', action="store", dest='accountName', default='mt4')
    parser.add_argument('--priceDir', action="store", dest="priceDir", default='c:/temp/prices')
    args = parser.parse_args()

    price_events = queue.Queue()
    TRADED_INSTRUMENTS = [
        'GBP_USD', 'EUR_USD', 'AUD_USD', 'USD_SGD', 'USD_JPY',
        'GBP_AUD', 'USD_CAD', 'EUR_GBP', 'USD_CHF', 'BCO_USD'
    ]

    t = MeanReversionTrader(events=price_events, instruments=TRADED_INSTRUMENTS, feeds_loc=args.priceDir, account=args.accountName, live_run=args.liveRun)
    spe = StreamPriceEvent(TRADED_INSTRUMENTS, price_events)
    price_thread = threading.Thread(target=spe.start)
    price_thread.start()

    t.run()
