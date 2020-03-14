import json
import logging

import oandapyV20.endpoints.orders as orders
from oandapyV20.contrib.requests import MITOrderRequest, TakeProfitDetails, StopLossDetails
from oandapyV20.exceptions import V20Error

from src.env import PRACTICE_ENV

logging.basicConfig(level=logging.DEBUG)
env = PRACTICE_ENV
api = PRACTICE_ENV.api()
account = PRACTICE_ENV.account()


def placing_order(instrument, side, units, price, tp, sl):
    mktOrder = MITOrderRequest(
        instrument=instrument,
        units=units if side == 'buy' else units * -1,
        price=price,
        takeProfitOnFill=TakeProfitDetails(price=tp).data,
        stopLossOnFill=StopLossDetails(price=sl).data)

    print(json.dumps(mktOrder.data, indent=4))
    r = orders.OrderCreate(account.mt4, data=mktOrder.data)
    try:
        # create the OrderCreate request
        rv = api.request(r)
    except V20Error as err:
        logging.error(r.status_code, err)
    else:
        logging.info(json.dumps(rv, indent=2))


def cancel_order(order_id):
    logging.info(f'Cancelling order id: {order_id}')
    r = orders.OrderCancel(accountID=account.mt4, orderID=order_id)
    api.request(r)
    logging.info(r.response)


def get_pending_orders():
    r = orders.OrdersPending(account.mt4)
    try:
        # create the OrderCreate request
        rv = api.request(r)
    except V20Error as err:
        logging.error(r.status_code, err)
    else:
        logging.info(json.dumps(rv, indent=2))
        return rv.get('orders')


if __name__ == "__main__":
    pending_orders = get_pending_orders()
    if pending_orders:
        cancel_order(pending_orders[0].get('id'))

    # price = 1.3050
    # TAKE_PROFIT = 1.31
    # STOP_LOSS = 1.3
    # placing_order(instrument='GBP_USD', side='buy', units=10000, price=price, tp=TAKE_PROFIT, sl=STOP_LOSS)
