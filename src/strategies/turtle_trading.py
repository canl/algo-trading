"""
The strategy is inspired and derived from Turtle Trading System
Rules:

Entries:

    Turtles entered positions when the price exceeded by a single tick the
    high or low of the preceding 20 days. If the price exceeded the 20-day high, then the
    Turtles would buy one Unit to initiate a long position in the corresponding
    commodity. If the price dropped one tick below the low of the last 20-days, the Turtles
    would sell one Unit to initiate a short position.

Adding units:

    Turtles entered single Unit long positions at the breakouts and added to those
    positions at ½ N intervals following their initial entry. This ½ N interval was based on
    the actual fill price of the previous order

SL

    The Turtles placed their stops based on position risk. No trade could incur more than
    2% risk. Turtle stops were set at 2N (ATR) below the entry for long positions,
    and 2N (ATR) above the entry for short positions.

    For example:
        Crude Oil
        ATR = 1.20
        55 day breakout = 28.30
            First unit:
            |Units       |Entry Price|Stop  |
            |First Unit  |      28.30| 25.90|

            second unit:
            |Units       |Entry Price|Stop  |
            |First Unit  |      28.30| 26.50|
            |First Unit  |      28.90| 26.50|

            third unit:
            |Units       |Entry Price|Stop  |
            |First Unit  |      28.30| 27.10|
            |First Unit  |      28.90| 27.10|
            |First Unit  |      29.50| 27.10|

            fourth unit:
            |Units       |Entry Price|Stop  |
            |First Unit  |      28.30| 27.70|
            |Second Unit |      28.90| 27.70|
            |Third Unit  |      29.50| 27.70|
            |Fourth Unit |      30.10| 27.70|

        Case where fourth unit was added at a higher price because the market opened gapping up to 30.80:

            |Units       |Entry Price|Stop  |
            |First Unit  |      28.30| 27.70|
            |Second Unit |      28.90| 27.70|
            |Third Unit  |      29.50| 27.70|
            |Fourth Unit |      30.80| 28.40|

Exit

    The System 1 exit was a 10 day low for long positions and a 10 day high for short
    positions. All the Units in the position would be exited if the price went against the
    position for a 10 day breakout.

Position Size:

    %2 risk

"""
import logging

import pandas as pd

from src.backtester import BackTester
from src.orders.order import Order, OrderSide, OrderStatus
from src.position_calculator import pos_size

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    price_df = pd.read_csv('c:/temp/gbp_usd_h1_enrich.csv')
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

    price_df = price_df[(price_df['time'] > '2010-01-01') & (price_df['time'] < '2020-12-01')]

    initial_capital = 10000
    risk_pct = 0.02
    max_orders = 1
    orders = []
    for price in price_df.to_dict('records'):
        # Checking open orders
        open_orders = [o for o in orders if o.is_open]
        for o in open_orders:
            if o.is_long:
                if price['low'] <= o.sl:
                    o.close_with_loss(price['time'])

                elif price['low'] <= price['last_10_low']:
                    if o.entry <= price['last_10_low']:
                        o.close_with_win(price['time'], price['last_10_low'])
                    elif o.entry > price['last_10_low']:
                        o.close_with_loss(price['time'], price['last_10_low'])
            else:
                if price['high'] >= o.sl:
                    o.close_with_loss(price['time'])

                elif price['high'] >= price['last_10_high']:
                    if o.entry >= price['last_10_high']:
                        o.close_with_win(price['time'], price['last_10_high'])
                    elif o.entry < price['last_10_high']:
                        o.close_with_loss(price['time'], price['last_10_high'])

        open_longs = [o for o in orders if o.is_open and o.is_long]
        open_shorts = [o for o in orders if o.is_open and o.is_short]

        if len(open_longs) < max_orders:
            if len(open_longs) == 0:
                if price['high'] >= price['last_20_high'] and price['close'] > price['day_ema_55'] and (price['day_rsi'] >= 70 or price['day_rsi'] <= 30):
                    sl = price['close'] - price['day_atr'] * 2
                    lots = pos_size(account_balance=initial_capital, risk_pct=risk_pct, sl_pips=price['day_atr'] * 2 * 10000, instrument='GBP_USD')
                    orders.append(Order(price['time'], OrderSide.LONG, entry=price['close'], sl=sl, status=OrderStatus.FILLED, units=100000 * lots))
            else:
                previous_entry = open_longs[-1].entry
                atr = price['day_atr']
                if price['high'] >= previous_entry + atr / 2:
                    initial_units = open_longs[0].units
                    new_entry = previous_entry + atr / 2
                    new_sl = new_entry - atr * 2
                    logger.info('Adding buy units ...')
                    orders.append(Order(price['time'], OrderSide.LONG, entry=new_entry, status=OrderStatus.FILLED, units=initial_units))
                    for o in orders:
                        if o.is_open and o.is_long:
                            o.sl = new_sl

        if len(open_shorts) < max_orders:
            if len(open_shorts) == 0:
                if price['low'] <= price['last_20_low'] and price['close'] < price['day_ema_55'] and (price['day_rsi'] >= 70 or price['day_rsi'] <= 30):
                    sl = price['close'] + price['day_atr'] * 2
                    lots = pos_size(account_balance=initial_capital, risk_pct=risk_pct, sl_pips=price['day_atr'] * 2 * 10000, instrument='GBP_USD')
                    orders.append(Order(price['time'], OrderSide.SHORT, entry=price['close'], sl=sl, status=OrderStatus.FILLED, units=100000 * lots))
            else:
                previous_entry = open_shorts[-1].entry
                atr = price['day_atr']
                if price['low'] <= previous_entry - atr / 2:
                    initial_units = open_shorts[0].units
                    new_entry = previous_entry - atr / 2
                    new_sl = new_entry + atr * 2
                    logger.info('Adding sell units ...')
                    orders.append(Order(price['time'], OrderSide.SHORT, entry=new_entry, status=OrderStatus.FILLED, units=initial_units))
                    for o in orders:
                        if o.is_open and o.is_short:
                            o.sl = new_sl

    back_tester = BackTester(strategy='turtle trading')
    back_tester.lot_size = 10000
    back_tester.print_stats(orders)
