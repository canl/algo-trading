import json
import logging
from typing import Union

from oandapyV20 import V20Error
from oandapyV20.contrib.requests import StopOrderRequest, TakeProfitDetails, StopLossDetails, LimitOrderRequest
from oandapyV20.endpoints import orders, trades

from src.env import RUNNING_ENV
from src.order_utils.order import OrderSide

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


class OrderManager:
    def __init__(self, account):
        self.account_id = RUNNING_ENV.get_account(account)

    def place_limit_order(self, instrument: str, side: str, units: Union[float, int], price: float, tp: float, sl: float, expiry: str = None):
        order_request = LimitOrderRequest(
            instrument=instrument,
            units=units * (1 if side == OrderSide.LONG else -1),
            price=price,
            takeProfitOnFill=TakeProfitDetails(price=tp).data,
            stopLossOnFill=StopLossDetails(price=sl).data,
            timeInForce='GTD' if expiry else 'GTC',
            gtdTime=expiry
        )
        self._submit_order_request(order_request, self.account_id)

    def place_stop_order(self, instrument: str, side: str, units: Union[float, int], price: float, tp: float, sl: float, expiry: str = None):
        order_request = StopOrderRequest(
            instrument=instrument,
            units=units * (1 if side == OrderSide.LONG else -1),
            price=price,
            takeProfitOnFill=TakeProfitDetails(price=tp).data,
            stopLossOnFill=StopLossDetails(price=sl).data,
            timeInForce='GTD' if expiry else 'GTC',
            gtdTime=expiry
        )
        self._submit_order_request(order_request, self.account_id)

    @staticmethod
    def _submit_order_request(request, account_id):
        logging.info(json.dumps(request.data, indent=4))
        r = orders.OrderCreate(account_id, data=request.data)
        try:
            # create the OrderCreate request
            rv = RUNNING_ENV.api.request(r)
        except V20Error as err:
            logging.error(r.status_code, err)
        else:
            logging.info(json.dumps(rv, indent=2))

    def cancel_order(self, order_id):
        logging.info(f'Cancelling order id: {order_id}')
        r = orders.OrderCancel(accountID=self.account_id, orderID=order_id)
        RUNNING_ENV.api.request(r)
        logging.info(r.response)

    def get_pending_orders(self):
        r = orders.OrdersPending(self.account_id)
        try:
            # create the OrderCreate request
            rv = RUNNING_ENV.api.request(r)
        except V20Error as err:
            logging.error(r.status_code, err)
        else:
            logging.info(json.dumps(rv, indent=2))
            return rv.get('orders')

    def get_open_trades(self):
        r = trades.OpenTrades(self.account_id)
        try:
            rv = RUNNING_ENV.api.request(r)
        except V20Error as err:
            logging.error(r.status_code, err)
        else:
            logging.info(json.dumps(rv, indent=2))
            return rv.get('trades')

    def get_trades(self, instruments: list = None, state: str = 'ALL', start_from: int = 0):
        params = {
            "instrument": ",".join(instruments) if instruments else [],
            "state": state,
            "count": 500
        }
        r = trades.TradesList(self.account_id, params=params)
        try:
            rv = RUNNING_ENV.api.request(r)
        except V20Error as err:
            logging.error(r.status_code, err)
        else:
            res = [el for el in rv.get('trades') if int(el['id']) >= start_from]
            logging.debug(json.dumps(res, indent=2))
            return sorted(res, key=lambda x: int(x['id']))


if __name__ == '__main__':
    from datetime import datetime, timezone, timedelta

    manager = OrderManager('mt4')

    print(manager.get_trades())
    print(manager.get_open_trades())

    now_utc = datetime.now(timezone.utc)
    expiry_time = (now_utc + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    manager.place_limit_order('GBP_USD', OrderSide.LONG, 100, 1.20, 1.25, 1.15, expiry=expiry_time)
    manager.place_limit_order('GBP_USD', OrderSide.SHORT, 100, 1.30, 1.35, 1.25, expiry=expiry_time)

    for o in manager.get_pending_orders():
        manager.cancel_order(order_id=o.get('id'))
