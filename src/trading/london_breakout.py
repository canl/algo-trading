import argparse
import logging
from datetime import datetime
import pandas as pd

from src.common import api_request, transform
from src.notifier import notify
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
from src.position_calculator import pos_size


def cancel_pending_orders():
    pending_orders = get_pending_orders()
    if pending_orders:
        for o in pending_orders:
            # We do not want to cancel TAKE_PROFIT and STOP_LOSS pending orders
            if o.get('type') == 'MARKET_IF_TOUCHED':
                cancel_order(o.get('id'))


def send_alert(last_high, last_low, diff, position_size, adj):
    contents = {
        'last 8 hours high': last_high,
        'last 8 hours low': last_low,
        'diff': round(diff, 4),
        'position size': position_size,
        'adjustment': f'{adj} pips',
        'buy instruction': f'Buy {position_size} lot at Entry Price: {last_high}, SL: {last_low}, TP: {last_high + diff + adj / 10000}',
        'sell instruction': f'Sell {position_size} lot at Entry Price: {last_low}, SL: {last_high}, TP: {last_low - diff - adj / 10000}'
    }
    css = """
    <style>
        table {
          border-collapse: collapse;
          width: 100%;
        }

        th, td {
          text-align: left;
          padding: 8px;
        }

        tr:nth-child(even) {background-color: #f2f2f2;}
    </style>
    """
    html = '<table border=1><tbody>'
    for name, value in contents.items():
        html += f'<tr><td>{name}</td><td>{value}</td></tr>'
    html += "</tbody></table>"
    notify(f"Trading instructions on {datetime.today().strftime('%Y-%m-%d')}", css + html)


def run(live_run=False):
    # 5 pips adjustment for TP
    adj = 5 / 10000
    param = {
        "count": 8,
        "granularity": "H1"
    }
    resp = api_request(instrument='GBP_USD', p=param)
    df = pd.DataFrame(transform(resp['candles'])).set_index('time')
    logging.info(df)
    last_high = df['high'].max()
    last_low = df['low'].min()
    diff = last_high - last_low
    logging.info(f'Calculating position size for sl pips {diff}')
    position_size = pos_size(account_balance=10000, risk_pct=0.025, sl_pips=diff * 10000, instrument='GBP_USD')

    logging.info(f'Placing {position_size} lot buy order. Price: {last_high}, TP: {last_high + diff + adj}, SL: {last_low}')
    logging.info(f'Placing {position_size} lot sell order. Price: {last_low}, TP: {last_low - diff - adj}, SL: {last_high}')

    send_alert(last_high, last_low, diff, position_size, 5)

    if live_run:
        cancel_pending_orders()
        placing_order(instrument='GBP_USD', side='buy', units=100000 * position_size, price=last_high, tp=last_high + diff, sl=last_low)
        placing_order(instrument='GBP_USD', side='sell', units=100000 * position_size, price=last_low, tp=last_low - diff, sl=last_high)
    else:
        logging.info('Dry run only for testing.')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="London Breakout Strategy")
    parser.add_argument("--liveRun", help="Flag to indicate dry or live run", action='store_true', default=False)
    args = parser.parse_args()
    run(args.liveRun)
