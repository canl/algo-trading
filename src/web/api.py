from http import HTTPStatus
from typing import List

from flask import Blueprint, request

from src.account.account_manager import AccountManager
from src.env import RUNNING_ENV
from src.orders.order import OrderSide
from src.orders.order_manager import OrderManager
from src.pricer import get_spot_rate
from src.utils.common import has_special_instrument

api = Blueprint('api', __name__)

SPECIAL_INSTRUMENTS = ('XAU', 'JPY', 'BCO')


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
    res = []
    for el in trades:
        state = el['state']
        ccy_pair = el['instrument']
        common = {
            'id': el['id'],
            'side': OrderSide.LONG.upper() if float(el['initialUnits']) > 0 else OrderSide.SHORT.upper(),
            'instrument': ccy_pair,
            'units': abs(int(float(el['initialUnits']))),
            'entryPrice': float(el['price']),
            'tp': float(el.get('takeProfitOrder').get('price')) if el.get('takeProfitOrder') else None,
            'sl': float(el.get('stopLossOrder').get('price')) if el.get('stopLossOrder') else None,
            'exitPrice': float(el['averageClosePrice']) if state == 'CLOSED' else None,
            'financing': round(float(el['financing']), 2),
            'pl': round(float(el['unrealizedPL']), 2) if state == 'OPEN' else round(float(el['realizedPL']), 2),
            'state': state,
            'openTime': el['openTime'][:19].replace("T", " "),
            'closeTime': el['closeTime'][:19].replace("T", " ") if state == 'CLOSED' else None
        }
        if state == 'OPEN':
            spot_rate = round(get_spot_rate(ccy_pair), 5)
            multiplier = 100 if has_special_instrument(ccy_pair) else 10000
            common.update({
                'spotRate': spot_rate,
                'pips': ((spot_rate - float(el['price'])) * multiplier) if float(el['initialUnits']) > 0 else ((float(el['price']) - spot_rate) * multiplier)
            })
        res.append(common)
    return {
        'status': HTTPStatus.OK,
        'data': res
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
    win_pips = round(sum([abs(float(el['price']) - float(el['averageClosePrice'])) * (100 if _has_special_instrument(el['instrument']) else 10000)
                          for el in trades if float(el['realizedPL']) > 0]), 0)
    loss_pips = round(sum([abs(float(el['price']) - float(el['averageClosePrice'])) * (100 if _has_special_instrument(el['instrument']) else 10000)
                           for el in trades if float(el['realizedPL']) < 0]), 0)
    avg_win_pips = win_pips / no_of_wins if no_of_wins else 0
    avg_loss_pips = loss_pips / no_of_losses if no_of_losses else 0
    pl_pips = win_pips - loss_pips
    gross_profit = sum([float(el['realizedPL']) for el in trades if float(el['realizedPL']) > 0])
    gross_loss = sum([float(el['realizedPL']) for el in trades if float(el['realizedPL']) < 0])

    profit_factor = abs(gross_profit / gross_loss) if loss_pips else 0
    return {
        'status': HTTPStatus.OK,
        'data': {
            'nav': am.nav,
            'initial_balance': am.initial_balance,
            'pl': gross_profit + gross_loss,
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


@api.route('/<env>/account/<name>/trend', methods=['GET'])
def daily_trend(env: str, name: str):
    valid_env(env)
    am = AccountManager(account=name)
    res = []
    init_balance = am.initial_balance
    for el in get_trades(env, name):
        close_date = el.get('closeTime') or el.get('openTime')
        close_date = close_date[:10]
        pl = float(el['unrealizedPL']) if el['state'] == 'OPEN' else float(el['realizedPL'])
        if res:
            if res[-1]['date'] == close_date:
                res[-1]['pl'] += pl
            else:
                res.append({'date': close_date, 'pl': res[-1]['pl'] + pl})
        else:
            res.append({'date': close_date, 'pl': init_balance + pl})
    return {
        'status': HTTPStatus.OK,
        'data': [{'date': el['date'], 'pl': round(el['pl'], 2)} for el in res]
    }


def _has_special_instrument(instrument):
    return any(inst in instrument for inst in SPECIAL_INSTRUMENTS)


def get_trades(env: str, name: str) -> List[dict]:
    valid_env(env)
    om = OrderManager(account=name)
    start_from = request.args.get('start_from', default=0, type=int)
    state = request.args.get('state', default='ALL', type=str)
    return om.get_trades(state=state, start_from=start_from)


def valid_env(env):
    if env == 'live':
        if RUNNING_ENV.is_practice():
            RUNNING_ENV.load_config('live')
    elif env == 'practice':
        if RUNNING_ENV.is_live():
            RUNNING_ENV.load_config('practice')
    else:
        return {
                   'error': f'Invalid env {env}! Env mush be either practice or live'
               }, HTTPStatus.BAD_REQUEST
