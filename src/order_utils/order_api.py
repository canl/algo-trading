import json
import logging

from oandapyV20.contrib.requests import TakeProfitDetails, StopLossDetails, StopOrderRequest
from oandapyV20.endpoints import orders, positions, trades, transactions
from oandapyV20.exceptions import V20Error

from src.env import RUNNING_ENV

logging.basicConfig(level=logging.DEBUG)


class OrderType:
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    MARKET_IF_TOUCHED = "mit",
    TAKE_PROFIT = "tp"
    STOP_LOSS = "sl"
    TRAILING_STOP_LOSS = "trailing_sl",
    FIXED_PRICE = "fixed"


def placing_order(order_type, instrument, side, units, price, tp, sl):
    """
    Placing order
    :param order_type:
            "MARKET": "A Market Order",
            "LIMIT": "A Limit Order",
            "STOP": "A Stop Order",
            "MARKET_IF_TOUCHED": "A Market-if-touched Order",
            "TAKE_PROFIT": "A Take Profit Order",
            "STOP_LOSS": "A Stop Loss Order",
            "TRAILING_STOP_LOSS": "A Trailing Stop Loss Order",
            "FIXED_PRICE": "A Fixed Price Order"
    :param instrument: A string containing the base currency and quote currency delimited by a “_”.
    :param side: long/buy or short/sell
    :param units: units size
    :param price: price
    :param tp: take profit
    :param sl: stop loss
    :return:
    """
    if order_type == OrderType.STOP:
        order_request = StopOrderRequest(
            instrument=instrument,
            units=units if side == 'buy' else units * -1,
            price=price,
            takeProfitOnFill=TakeProfitDetails(price=tp).data,
            stopLossOnFill=StopLossDetails(price=sl).data
        )
    else:
        raise NotImplemented(f'{order_type} is not supported yet')

    print(json.dumps(order_request.data, indent=4))
    r = orders.OrderCreate(RUNNING_ENV.account.mt4, data=order_request.data)
    try:
        # create the OrderCreate request
        rv = RUNNING_ENV.api.request(r)
    except V20Error as err:
        logging.error(r.status_code, err)
    else:
        logging.info(json.dumps(rv, indent=2))


def cancel_order(order_id):
    logging.info(f'Cancelling order id: {order_id}')
    r = orders.OrderCancel(accountID=RUNNING_ENV.account.mt4, orderID=order_id)
    RUNNING_ENV.api.request(r)
    logging.info(r.response)


def get_pending_orders():
    print("Running " + RUNNING_ENV.env)
    r = orders.OrdersPending(RUNNING_ENV.account.mt4)
    try:
        # create the OrderCreate request
        rv = RUNNING_ENV.api.request(r)
    except V20Error as err:
        logging.error(r.status_code, err)
    else:
        logging.info(json.dumps(rv, indent=2))
        return rv.get('orders')


def get_positions():
    r = positions.PositionList(RUNNING_ENV.account.mt4)
    try:
        rv = RUNNING_ENV.api.request(r)
    except V20Error as err:
        logging.error(r.status_code, err)
    else:
        logging.info(json.dumps(rv, indent=2))
        return rv.get('positions')


def get_open_trades():
    r = trades.OpenTrades(RUNNING_ENV.account.mt4)
    try:
        rv = RUNNING_ENV.api.request(r)
    except V20Error as err:
        logging.error(r.status_code, err)
    else:
        logging.info(json.dumps(rv, indent=2))
        return rv.get('trades')


def get_trans(trans_size=100):
    last_trans_id = int(RUNNING_ENV.api.request(transactions.TransactionList(RUNNING_ENV.account.mt4)).get('lastTransactionID'))
    since_id = last_trans_id - trans_size if last_trans_id - trans_size > 0 else 0
    params = {
        "id": since_id
    }
    r = transactions.TransactionsSinceID(RUNNING_ENV.account.mt4, params)
    try:
        rv = RUNNING_ENV.api.request(r)
    except V20Error as err:
        logging.error(r.status_code, err)
    else:
        logging.debug(json.dumps(rv, indent=2))
        return rv.get('transactions')


def get_trades(instruments, return_size=100):
    params = {
        "instrument": ",".join(instruments),
        "state": "ALL"
    }
    r = trades.TradesList(RUNNING_ENV.account.mt4, params=params)
    try:
        rv = RUNNING_ENV.api.request(r)
    except V20Error as err:
        logging.error(r.status_code, err)
    else:
        logging.info(json.dumps(rv, indent=2))
        res = rv.get('trades')[:return_size]
        return sorted(res, key=lambda x: int(x['id']))


if __name__ == "__main__":
    # pass
    trans = get_trades(["GBP_USD"], 4)
    trans = [{'id': t.get('id'), 'state': t.get('state'), 'pl': t.get('realizedPL')} for t in trans]
    print(trans)
    #
    # pending_orders = get_pending_orders()
    # if pending_orders:
    #     cancel_order(pending_orders[0].get('id'))
