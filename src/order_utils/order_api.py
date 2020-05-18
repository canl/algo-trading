import json
import logging

from oandapyV20.endpoints import orders, positions, trades, transactions
from oandapyV20.contrib.requests import MITOrderRequest, TakeProfitDetails, StopLossDetails
from oandapyV20.exceptions import V20Error

from src.env import PRACTICE_ENV

logging.basicConfig(level=logging.DEBUG)
env = PRACTICE_ENV
api = PRACTICE_ENV.api()
account = PRACTICE_ENV.account()


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
    if order_type == OrderType.MARKET_IF_TOUCHED:
        order_request = MITOrderRequest(
            instrument=instrument,
            units=units if side == 'buy' else units * -1,
            price=price,
            takeProfitOnFill=TakeProfitDetails(price=tp).data,
            stopLossOnFill=StopLossDetails(price=sl).data
        )
    else:
        raise NotImplemented(f'{order_type} is not supported yet')

    print(json.dumps(order_request.data, indent=4))
    r = orders.OrderCreate(account.mt4, data=order_request.data)
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


def get_positions():
    r = positions.PositionList(account.mt4)
    try:
        rv = api.request(r)
    except V20Error as err:
        logging.error(r.status_code, err)
    else:
        logging.info(json.dumps(rv, indent=2))
        return rv.get('positions')


def get_trades():
    r = trades.TradesList(account.mt4)
    try:
        rv = api.request(r)
    except V20Error as err:
        logging.error(r.status_code, err)
    else:
        logging.info(json.dumps(rv, indent=2))
        return rv.get('trades')


def get_trans(trans_size=100):
    last_trans_id = int(api.request(transactions.TransactionList(account.mt4)).get('lastTransactionID'))
    since_id = last_trans_id - trans_size if last_trans_id - trans_size > 0 else 0
    params = {
        "id": since_id
    }
    r = transactions.TransactionsSinceID(account.mt4, params)
    try:
        rv = api.request(r)
    except V20Error as err:
        logging.error(r.status_code, err)
    else:
        logging.info(json.dumps(rv, indent=2))
        return rv.get('transactions')


if __name__ == "__main__":
    pass
    # trans = get_trans(100)
    # trans = [{'id': t.get('id'), 'pl': t.get('pl')} for t in trans if t.get('pl') and t.get('pl') != '0.0000']
    # print(trans)

    # pending_orders = get_pending_orders()
    # if pending_orders:
    #     cancel_order(pending_orders[0].get('id'))

    # price = 1.3050
    # TAKE_PROFIT = 1.31
    # STOP_LOSS = 1.3
    # placing_order(instrument='GBP_USD', side='buy', units=10000, price=price, tp=TAKE_PROFIT, sl=STOP_LOSS)
