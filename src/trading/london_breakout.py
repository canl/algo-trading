import logging
from datetime import timedelta, datetime

import pandas as pd
from src.common import read_price_data, transform
from src.order_utils.order_api import placing_order

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


logging.basicConfig(level=logging.DEBUG)

if __name__ == "__main__":
    to_date = datetime.today() + timedelta(days=1)
    from_date = to_date - timedelta(days=3)
    logging.info(f'Reading date between {from_date} and {to_date}')
    raw_response = read_price_data('GBP_USD', 'H1', from_dt=from_date.strftime("%Y-%m-%d"))
    df = pd.DataFrame(transform(raw_response)).set_index('time')
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

    dry_run = True

    if not dry_run:
        placing_order(instrument='GBP_USD', side='buy', units=100000, price=last_high, tp=last_high + last_diff, sl=last_low)
        placing_order(instrument='GBP_USD', side='sell', units=100000, price=last_low, tp=last_low - last_diff, sl=last_high)
