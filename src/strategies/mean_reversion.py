"""
A simple mean reversion strategy with back testing result. The strategy only works when market is ranging,
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

import logging
from datetime import timedelta

import pandas as pd

from src.backtester import BackTester
from src.order_utils.order import Order, OrderSide, OrderStatus

logger = logging.getLogger(__name__)


def process_pending(order, ohlc):
    # If the order cannot be filled within next 3 hours, cancel it
    if pd.to_datetime(ohlc['time']) - pd.to_datetime(order.order_date) <= timedelta(hours=3):
        if (order.is_long and ohlc['low'] <= order.entry) or \
                (order.is_short and ohlc['high'] >= order.entry):
            logger.debug(pd.to_datetime(ohlc['time']) - pd.to_datetime(order.order_date))
            logger.info(f"Fill {order.side} order [{order.id}] @ {order.entry} @ {ohlc['time']} [order date: {order.order_date}]")
            order.fill(ohlc['time'])
    else:
        order.cancel(ohlc['time'])


def process_filled(order, ohlc):
    if order.is_long:
        if ohlc['low'] <= order.sl:
            order.close_with_loss(ohlc['time'])
        elif ohlc['high'] >= order.tp:
            order.close_with_win(ohlc['time'])
    else:
        if ohlc['high'] >= order.sl:
            order.close_with_loss(ohlc['time'])
        elif ohlc['low'] <= order.tp:
            order.close_with_win(ohlc['time'])


def run(instrument: str, window: int, max_orders: int, entry_adj: float, tp_adj: float, start_date: str = None, end_date: str = None, output_result: bool = False):
    """
    Back testing the strategy
    :param instrument: ccy pair, eg. EUR_USD
    :param window: period of high or low
    :param max_orders: max orders allowed in the same direction
    :param entry_adj: entry price adj
    :param tp_adj: tp adj
    :param start_date: str
    :param end_date: str
    :param output_result: output to csv for investigations
    :return:
        list of tested orders
    """
    price_df = pd.read_csv(f'c:/temp/{instrument.lower()}_h1_enrich.csv')
    '''
         #   Column        Non-Null Count  Dtype
        ---  ------        --------------  -----
         0   time          65770 non-null  object
         1   open          65770 non-null  float64
         2   high          65770 non-null  float64
         3   low           65770 non-null  float64
         4   close         65770 non-null  float64
         5   last_10_high  65770 non-null  float64
         6   last_20_high  65770 non-null  float64
         7   last_10_low   65770 non-null  float64
         8   last_20_low   65770 non-null  float64
         9   day_close     65770 non-null  float64
         10  day_atr       65770 non-null  float64
         11  day_rsi       65770 non-null  float64
         12  day_ema_55    65770 non-null  float64
    '''

    if start_date and end_date:
        price_df = price_df[(price_df['time'] >= start_date) & (price_df['time'] < end_date)]

    orders = []
    for idx, ohlc in enumerate(price_df.to_dict('records')):
        [process_pending(o, ohlc) for o in orders if o.is_pending]
        [process_filled(o, ohlc) for o in orders if o.is_filled]

        open_long = [o for o in orders if o.is_long and o.is_open]
        open_short = [o for o in orders if o.is_short and o.is_open]
        atr = ohlc['day_atr']
        if ohlc['high'] == ohlc[f'last_{window}_high'] and len(open_short) < max_orders and 30 <= ohlc['day_rsi'] <= 70:
            # Place a short limit order
            entry = ohlc['high'] + entry_adj
            orders.append(
                Order(order_date=ohlc['time'], side=OrderSide.SHORT, entry=entry, sl=entry + atr, tp=entry - atr - tp_adj, status=OrderStatus.PENDING)
            )
        elif ohlc['low'] == ohlc[f'last_{window}_low'] and len(open_long) < max_orders and 30 <= ohlc['day_rsi'] <= 70:
            # Place a long limit order
            entry = ohlc['low'] - entry_adj
            orders.append(
                Order(order_date=ohlc['time'], side=OrderSide.LONG, entry=entry, sl=entry - atr, tp=entry + atr + tp_adj, status=OrderStatus.PENDING)
            )

    if output_result:
        output_csv(instrument, price_df, orders)
    return orders


def output_csv(instrument: str, price_feed: pd.DataFrame, orders: list):
    price_feed = price_feed.set_index('time')
    order_df = pd.DataFrame([
        {
            'time': o.order_date,
            'create_date': o.order_date,
            'side': o.side,
            'entry': o.entry,
            'sl': o.sl,
            'tp': o.tp,
            'pnl_in_pips': o.pnl * lot_size,
            'outcome': o.outcome,
            'close_date': o.last_update,
            'is_cancelled': o.is_cancelled,
        } for o in orders]).set_index('time')
    merged = price_feed.join(order_df, how="left")
    print(merged)
    merged.to_csv(f'C:/temp/{instrument.lower()}_back_test.csv')


if __name__ == '__main__':
    instruments = [
        ('EUR_USD', 10000), ('USD_CHF', 10000), ('USD_CAD', 10000), ('EUR_GBP', 10000), ('USD_SGD', 10000), ('GBP_NZD', 10000),
        ('AUD_USD', 10000), ('GBP_AUD', 10000), ('GBP_USD', 10000), ('USD_JPY', 100), ('XAU_USD', 1), ('BCO_USD', 100)
    ]
    dfs = []
    back_tester = BackTester(strategy='Mean Reversion')
    for ccy_pair, lot_size in instruments:
        test_orders = run(instrument=ccy_pair, window=20, max_orders=4, entry_adj=0.0005, tp_adj=0, start_date='2010-01-01', end_date='2020-06-30', output_result=False)
        back_tester.lot_size = lot_size
        print(f"{'*' * 30} {ccy_pair} {'*' * 30}")
        back_tester.print_stats(test_orders)

        df = pd.DataFrame([{'time': o.order_date, 'pnl': o.pnl * lot_size} for o in test_orders])
        df['time'] = pd.to_datetime(df['time'])
        df = df.resample('D', on='time')['pnl'].sum().to_frame()

        df[f'cumsum_{ccy_pair.lower()}'] = df['pnl'].cumsum()
        dfs.append(df[[f'cumsum_{ccy_pair.lower()}']])

    back_tester.plot_chart(dfs)
