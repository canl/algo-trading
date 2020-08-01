from http import HTTPStatus

from flask import Blueprint, request
from typing import List

from src.account.account_manager import AccountManager
from src.env import RUNNING_ENV
from src.order_utils.order import OrderSide
from src.order_utils.order_manager import OrderManager

api = Blueprint('api', __name__)


@api.route('/<env>/account/<name>', methods=['GET'])
def account(env: str, name: str) -> dict:
    valid_env(env)

    am = AccountManager(account=name)
    res = am.get_info()
    return {
        'status': HTTPStatus.OK,
        'data': {
            'id': res['id'],
            'name': res['alias'],
            'initial_balance': am.initial_balance,
            'balance': am.balance,
            'currency': res['currency'],
            'financing': am.financing,
            'pl': am.pl,
            'nav': am.nav,
            'unrealized_pl': am.unrealized_pl,
            "open_position_count": res['openPositionCount'],
            "open_trade_count": res['openTradeCount'],
            "pending_order_count": res['pendingOrderCount'],
            'last_transaction_id': float(res['lastTransactionID']),
            'created_time': res['createdTime']
        }
    }


@api.route('/<env>/account/<name>/orders', methods=['GET'])
def order(env: str, name: str) -> dict:
    trades = get_trades(env, name)
    return {
        'status': HTTPStatus.OK,
        'data': [
            {
                'id': el['id'],
                'side': OrderSide.LONG.upper() if float(el['initialUnits']) > 0 else OrderSide.SHORT.upper(),
                'instrument': el['instrument'],
                'units': abs(int(float(el['initialUnits']))),
                'entryPrice': float(el['price']),
                'tp': float(el.get('takeProfitOrder').get('price')) if el.get('takeProfitOrder') else None,
                'sl': float(el.get('stopLossOrder').get('price')) if el.get('stopLossOrder') else None,
                'exitPrice': float(el['averageClosePrice']) if el['state'] == 'CLOSED' else None,
                'financing': round(float(el['financing']), 2),
                'pl': round(float(el['unrealizedPL']), 2) if el['state'] == 'OPEN' else round(float(el['realizedPL']), 2),
                'state': el['state'],
                'openTime': el['openTime'][:19].replace("T", " "),
                'closeTime': el['closeTime'][:19].replace("T", " ") if el['state'] == 'CLOSED' else None
            }
            for el in trades
        ]
    }


@api.route('/<env>/account/<name>/stats', methods=['GET'])
def account_stats(env: str, name: str):
    valid_env(env)

    am = AccountManager(account=name)
    trades = [el for el in get_trades(env, name) if el['state'] == 'CLOSED']
    no_of_trades = len(trades)
    no_of_buys = len([el for el in trades if float(el['initialUnits']) > 0])
    no_of_sells = len([el for el in trades if float(el['initialUnits']) < 0])
    no_of_wins = len([el for el in trades if float(el['realizedPL']) > 0])
    no_of_losses = len([el for el in trades if float(el['realizedPL']) < 0])
    win_pips = round(sum([abs(float(el['price']) - float(el['averageClosePrice'])) for el in trades if float(el['initialUnits']) > 0]) * 10000, 0)
    loss_pips = round(sum([abs(float(el['price']) - float(el['averageClosePrice'])) for el in trades if float(el['initialUnits']) < 0]) * 10000, 0)
    avg_win_pips = win_pips / no_of_wins if no_of_wins else 0
    avg_loss_pips = loss_pips / no_of_losses if no_of_losses else 0
    pl_pips = win_pips - loss_pips
    profit_factor = win_pips / loss_pips if loss_pips else 0
    return {
        'status': HTTPStatus.OK,
        'data': {
            'nav': am.nav,
            'initial_balance': am.initial_balance,
            'pl': am.pl + am.financing,
            'unrealized_pL': am.unrealized_pl,
            'pl_pct': (am.pl + am.financing) / am.initial_balance,
            'pl_pips': pl_pips,
            'no_of_trades': no_of_trades,
            'no_of_buys': no_of_buys,
            'no_of_sells': no_of_sells,
            'no_of_wins': no_of_wins,
            'no_of_losses': no_of_losses,
            'win_percent': round(no_of_wins / no_of_trades, 4) if no_of_trades else 0,
            'loss_percent': round(no_of_losses / no_of_trades, 4) if no_of_trades else 0,
            'win_pips': win_pips,
            'loss_pips': loss_pips,
            'avg_win_pips': round(avg_win_pips, 0),
            'avg_loss_pips': round(avg_loss_pips, 0),
            'profit_factor': round(profit_factor, 2)
        }
    }


def get_trades(env: str, name: str) -> List[dict]:
    valid_env(env)
    om = OrderManager(account=name)
    start_from = request.args.get('start_from', default=0, type=int)
    state = request.args.get('state', default='ALL', type=str)
    return om.get_trades(state=state, start_from=start_from)


def valid_env(env):
    if env == 'live':
        RUNNING_ENV.load_config('live')
    else:
        RUNNING_ENV.load_config('practice')

    if env not in ('practice', 'live'):
        return {
                   'error': f'Invalid env {env}! Env mush be either practice or live'
               }, HTTPStatus.BAD_REQUEST
