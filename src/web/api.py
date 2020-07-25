from http import HTTPStatus

from flask import Blueprint

from src.account.account_manager import AccountManager
from src.env import RUNNING_ENV
from src.order_utils.order import OrderSide
from src.order_utils.order_manager import OrderManager

api = Blueprint('api', __name__)


@api.route('/<env>/account/<name>', methods=['GET'])
def account(env: str, name: str):
    valid_env(env)

    am = AccountManager(account=name)
    res = am.get_info()
    return {
        'status': HTTPStatus.OK,
        'data': {
            'id': res['id'],
            'name': res['alias'],
            'balance': float(res['balance']),
            'currency': res['currency'],
            'financing': res['financing'],
            'pl': float(res['pl']),
            'nav': float(res['NAV']),
            'unrealizedPL': float(res['unrealizedPL']),
            "openPositionCount": res['openPositionCount'],
            "openTradeCount": res['openTradeCount'],
            "pendingOrderCount": res['pendingOrderCount'],
            'lastTransactionID': float(res['lastTransactionID']),
            'createdTime': res['createdTime']
        }
    }


@api.route('/<env>/account/<name>/orders', methods=['GET'])
def order(env: str, name: str):
    valid_env(env)
    om = OrderManager(account=name)
    res = om.get_all_trades()
    return {
        'status': HTTPStatus.OK,
        'data': [
            {
                'id': el['id'],
                'side': OrderSide.LONG if float(el['initialUnits']) > 0 else OrderSide.SHORT,
                'instrument': el['instrument'],
                'units': abs(int(float(el['initialUnits']))),
                'entryPrice': float(el['price']),
                'exitPrice': float((el['takeProfitOrder' if float(el['realizedPL']) > 0 else 'stopLossOrder']['price'])) if el['state'] == 'CLOSED' else None,
                'financing': el['financing'],
                'pl': el['unrealizedPL'] if el['state'] == 'OPEN' else el['realizedPL'],
                'state': el['state'],
                'openTime': el['openTime'],
                'closeTime': el['closeTime'] if el['state'] == 'CLOSED' else None
            }
            for el in res
        ]
    }


def valid_env(env):
    if env == 'live':
        if env == 'live':
            RUNNING_ENV.load_config('live')

    if env not in ('practice', 'live'):
        return {
                   'error': f'Invalid env {env}! Env mush be either practice or live'
               }, HTTPStatus.BAD_REQUEST
