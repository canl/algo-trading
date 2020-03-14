import oandapyV20.endpoints.accounts as v20accounts
import oandapyV20.endpoints.instruments as v20instruments
from dateutil import parser

from src.env import PRACTICE_ENV

env = PRACTICE_ENV

api = env.api()
account = env.account()


def read_price_data(instrument, granularity, from_dt=None, to_dt=None, count=50):
    params = {
        'from': from_dt,
        'to': to_dt,
        "granularity": granularity
    }
    try:
        r = v20instruments.InstrumentsCandles(instrument=instrument, params=params)
        resp = api.request(r)
        return resp['candles']
    except Exception as err:
        print("Error: {}".format(err))
        exit(2)


def transform(raw_data):
    return [
        {
            'time': parser.parse(el.get('time')),
            'open': float(el['mid']['o']),
            'high': float(el['mid']['h']),
            'low': float(el['mid']['l']),
            'close': float(el['mid']['c'])
        } for el in raw_data
    ]


def get_account_info():
    print(account.mt4)
    r = v20accounts.AccountDetails(account.mt4)
    resp = api.request(r)
    return resp


if __name__ == '__main__':
    print(get_account_info())
