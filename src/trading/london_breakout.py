import argparse
import logging
from datetime import timedelta, datetime

from src.common import read_price_df
from src.order_utils.order_api import placing_order, get_pending_orders, cancel_order


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


def cancel_pending_orders():
    pending_orders = get_pending_orders()
    if pending_orders:
        for o in pending_orders:
            cancel_order(o.get('id'))


def run(live_run=False):
    from_date = datetime.today() - timedelta(days=3)
    logging.info(f'Reading date from {from_date} to now')
    df = read_price_df('GBP_USD', 'H1', start=from_date)
    df['last_8_high'] = df['high'].rolling(8).max()
    df['last_8_low'] = df['low'].rolling(8).min()
    df['diff_pips'] = (df['last_8_high'] - df['last_8_low']) * 10000

    df_08 = df.at_time('8:00')
    logging.info(df_08)

    last_high = df_08['last_8_high'][-1]
    last_low = df_08['last_8_low'][-1]
    last_diff = df_08['diff_pips'][-1] / 10000

    logging.info(f'Placing buy order. Price: {last_high}, TP: {last_high + last_diff}, SL: {last_low}')
    logging.info(f'Placing sell order. Price: {last_low}, TP: {last_low - last_diff}, SL: {last_high}')

    if live_run:
        cancel_pending_orders()
        placing_order(instrument='GBP_USD', side='buy', units=100000, price=last_high, tp=last_high + last_diff, sl=last_low)
        placing_order(instrument='GBP_USD', side='sell', units=100000, price=last_low, tp=last_low - last_diff, sl=last_high)
    else:
        logging.info('Dry run only for testing.')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="London Breakout Strategy")
    parser.add_argument("--liveRun", help="Flag to indicate dry or live run", action='store_true', default=False)
    args = parser.parse_args()
    run(args.liveRun)
