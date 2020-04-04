import logging
import math
from datetime import timedelta, datetime

import pandas as pd
from matplotlib import pyplot as plt

from src.common import read_price_df
from src.order_utils.order import OrderStatus, Order

# Rules:
#   1. Find the high and low between 00:00 to 08:00 UTC
#   2. Place a buy stop order 2 pips above high with stop loss
#       Buy Stop:
#       At: (Maximum Price + 2 pips)
#       T/P: (Maximum Price + (Maximum Price - Minimum Price))
#       S/L: (Minimum Price - 2 pips)
#   3. Place a sell stop order 2 pips below low
#       Sell Stop:
#       At (Minimum Price - 2 pips)
#       T/P (Minimum Price - (Maximum Price - Minimum Price))
#       S/L (Maximum Price + 2 pips)
#   4. Inactive pending orders will expire next trading day at 08:00 AM (GMT).


plt.style.use('ggplot')


def plot_performance(strats: list, tp_adjustments: tuple):
    df = pd.DataFrame({'date': [el.order_date for el in strats[0]]}).set_index('date')
    for idx, adj in enumerate(tp_adjustments):
        df[f'pnl_{adj}'] = [round(el.pnl, 4) for el in strats[idx]]

    grp_by = df.groupby(['date']).sum()
    for adj in tp_adjustments:
        grp_by[f'cumsum_{adj}'] = grp_by[f'pnl_{adj}'].cumsum()

    logging.info(grp_by)
    grp_by[[header for header in grp_by.columns if header.startswith('cumsum')]].plot()
    plt.show()


def backtest(price_data, adj=0.0):
    """
    params: price_data, list of dictionaries
    params: adj: float, to adjust the TP
    return: list of orders
    """
    orders = []

    for k, v in price_data.items():
        print('{}: [{}]'.format(k.hour, v))
        # x - (y - x) = 2x - y
        if math.isnan(v['last_8_high']):
            continue

        if k.hour == 8:
            for order in [el for el in orders if el.status == OrderStatus.PENDING]:
                order.status = OrderStatus.EXPIRED

            buy_tp = round(v['last_8_high'] * 2 - v['last_8_low'] + adj, 5)
            buy_sl = v['last_8_low']
            sell_tp = round(v['last_8_low'] * 2 - v['last_8_high'] - adj, 5)
            sell_sl = v['last_8_high']
            orders.append(Order(k.date(), 'buy', v['last_8_high'], buy_sl, buy_tp, 0, OrderStatus.PENDING))
            orders.append(Order(k.date(), 'sell', v['last_8_low'], sell_sl, sell_tp, 0, OrderStatus.PENDING))
            continue

        for order in [el for el in orders if el.status in (OrderStatus.PENDING, OrderStatus.FILLED)]:
            # Pending orders
            if order.status == OrderStatus.PENDING:
                if order.side == 'buy':
                    if v['high'] > order.price:  # buy order filled
                        order.status = OrderStatus.FILLED
                elif order.side == 'sell':
                    if v['low'] < order.price:  # sell order filled
                        order.status = OrderStatus.FILLED
            # Filled orders
            if order.status == OrderStatus.FILLED:
                if order.side == 'buy':
                    if v['low'] < order.sl:
                        order.status = OrderStatus.CLOSED
                        order.pnl = -1 * (order.price - order.sl) * 10000
                    elif v['high'] > order.tp:
                        order.status = OrderStatus.CLOSED
                        order.pnl = (order.tp - order.price) * 10000

                elif order.side == 'sell':
                    if v['high'] > order.sl:
                        order.status = OrderStatus.CLOSED
                        order.pnl = -1 * (order.sl - order.price) * 10000
                    elif v['low'] < order.tp:
                        order.status = OrderStatus.CLOSED
                        order.pnl = (order.price - order.tp) * 10000

    logging.info(orders)
    logging.info('Total PNL is: {}'.format(sum(el.pnl for el in orders)))
    return orders


if __name__ == "__main__":
    no_of_days = 7300
    raw_response = []
    last_date = datetime.today() - timedelta(days=1)
    from_date = last_date - timedelta(days=no_of_days)

    logging.info(f'Reading date between {from_date} and {last_date}')
    df = read_price_df(instrument='GBP_USD', granularity='H1', start=from_date, end=last_date)
    print(type(df.index.dtype))
    df['last_8_high'] = df['high'].rolling(8).max()
    df['last_8_low'] = df['low'].rolling(8).min()
    df['diff_pips'] = (df['last_8_high'] - df['last_8_low']) * 10000

    logging.info(df[['open', 'high', 'low', 'close', 'last_8_high', 'last_8_low', 'diff_pips']])
    # df_08 = df.at_time('8:00')
    # print(df.info())
    strats = []
    price_data = df.to_dict('index')
    tp_adjustments = (0, 5,)
    for adj in tp_adjustments:
        test_trades = backtest(price_data, adj / 10000)
        strats.append(test_trades)

    print(
        '{} orders placed.\nbuy orders: {}\nsell orders: {}\nfilled order: {}\nexpired order: {}\nwin Orders: {}\nloss orders: {}\nwin/loss ratio: {}%\noverall pnl: {}'.format(
            len(strats[0]), len([el for el in strats[0] if el.side == 'buy']),
            len([el for el in strats[0] if el.side == 'sell']),
            len([el for el in strats[0] if el.status == OrderStatus.CLOSED]),
            len([el for el in strats[0] if el.status == OrderStatus.EXPIRED]),
            len([el for el in strats[0] if el.pnl > 0]), len([el for el in strats[0] if el.pnl < 0]),
            round((len([el for el in strats[0] if el.pnl > 0]) / (len([el for el in strats[0] if el.pnl > 0]) + len([el for el in strats[0] if el.pnl < 0]))) * 100, 2),
            round(sum(el.pnl for el in strats[0]), 4)
        ))

    plot_performance(strats, tp_adjustments)
