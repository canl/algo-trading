from datetime import datetime, timedelta
import re
import logging
import numpy as np
import pandas as pd
import oandapyV20.endpoints.accounts as v20accounts
import oandapyV20.endpoints.instruments as v20instruments
from dateutil import parser

from src.env import PRACTICE_ENV

env = PRACTICE_ENV
OANDA_DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S'

api = env.api()
account = env.account()
logger = logging.getLogger(__name__)


def read_price_df(instrument: str, granularity: str, start: datetime, end: datetime = None, max_count: int = 4000) -> pd.DataFrame:
    """
    Read raw price data into Pandas DataFrame

    """
    prices = transform(read_price_data(instrument, granularity, start, end, max_count))
    return pd.DataFrame(prices).drop_duplicates().set_index('time').sort_index()


def read_price_data(instrument, granularity, start=None, end=None, max_count=4000):
    """
    :return List of dictionaries
    :param instrument: A string containing the base currency and quote currency delimited by a “_”.
    :param granularity:
        Value	Description
        S5	5 second candlesticks, minute alignment
        S10	10 second candlesticks, minute alignment
        S15	15 second candlesticks, minute alignment
        S30	30 second candlesticks, minute alignment
        M1	1 minute candlesticks, minute alignment
        M2	2 minute candlesticks, hour alignment
        M4	4 minute candlesticks, hour alignment
        M5	5 minute candlesticks, hour alignment
        M10	10 minute candlesticks, hour alignment
        M15	15 minute candlesticks, hour alignment
        M30	30 minute candlesticks, hour alignment
        H1	1 hour candlesticks, hour alignment
        H2	2 hour candlesticks, day alignment
        H3	3 hour candlesticks, day alignment
        H4	4 hour candlesticks, day alignment
        H6	6 hour candlesticks, day alignment
        H8	8 hour candlesticks, day alignment
        H12	12 hour candlesticks, day alignment
        D	1 day candlesticks, day alignment
        W	1 week candlesticks, aligned to start of week
        M	1 month candlesticks, aligned to first day of the month
    :param start: datetime object
    :param end:  datetime object
    :param max_count: number of expected return counts, Oanda has maximum return count as 5000
    :return: list of dictionaries
    """
    params = build_params(granularity=granularity, start=start, end=end, max_count=max_count)
    final_response = []
    for p in params:
        try:
            logger.info(f'Reading price data for {instrument}\n{params}')
            r = v20instruments.InstrumentsCandles(instrument=instrument, params=p)
            resp = api.request(r)
            final_response.extend(resp['candles'])
        except Exception as err:
            print("Error: {}".format(err))
            exit(2)

    return final_response


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


def build_params(granularity: str, start: datetime, end: datetime = None, max_count: int = 4000):
    """
    Compose params for querying Oanda
    :param granularity:
        Value	Description
        S5	5 second candlesticks, minute alignment
        S10	10 second candlesticks, minute alignment
        S15	15 second candlesticks, minute alignment
        S30	30 second candlesticks, minute alignment
        M1	1 minute candlesticks, minute alignment
        M2	2 minute candlesticks, hour alignment
        M4	4 minute candlesticks, hour alignment
        M5	5 minute candlesticks, hour alignment
        M10	10 minute candlesticks, hour alignment
        M15	15 minute candlesticks, hour alignment
        M30	30 minute candlesticks, hour alignment
        H1	1 hour candlesticks, hour alignment
        H2	2 hour candlesticks, day alignment
        H3	3 hour candlesticks, day alignment
        H4	4 hour candlesticks, day alignment
        H6	6 hour candlesticks, day alignment
        H8	8 hour candlesticks, day alignment
        H12	12 hour candlesticks, day alignment
        D	1 day candlesticks, day alignment
        W	1 week candlesticks, aligned to start of week
        M	1 month candlesticks, aligned to first day of the month
    :param start: datetime
    :param end: datetime
    :param max_count: int
    :return: list of dictionaries in the format of:
        {
             'from': start.strftime(OANDA_DATETIME_FORMAT),
             'to': end.strftime(OANDA_DATETIME_FORMAT),
             "granularity": granularity
        }
    """
    if not end:
        return [
            {
                'from': start.strftime(OANDA_DATETIME_FORMAT),
                "granularity": granularity
            }
        ]
    if granularity in ('M', 'W'):
        return [
            {
                'from': start.strftime(OANDA_DATETIME_FORMAT),
                'to': end.strftime(OANDA_DATETIME_FORMAT),
                "granularity": granularity
            }
        ]
    candlesticks = get_candlesticks(start=start, end=end, granularity=granularity)

    multiplier = 1

    if granularity == 'W':
        multiplier = 7 * 24 * 60 * 60
    elif granularity == 'M':
        multiplier = 30 * 24 * 60 * 60
    elif granularity == 'D':
        multiplier = 24 * 60 * 60
    else:
        nums = int(re.compile(r"\d+$").search(granularity)[0])
        if granularity.startswith('H'):
            multiplier = 60 * 60 * nums

        if granularity.startswith('M'):
            multiplier = 60 * nums

        if granularity.startswith('S'):
            multiplier = nums

    params = []
    no_of_requests = int(np.ceil(candlesticks / max_count))
    for idx in range(no_of_requests):
        e = end - timedelta(seconds=idx * multiplier * max_count)
        s = start if idx == no_of_requests - 1 else e - timedelta(seconds=(candlesticks if candlesticks < max_count else max_count) * multiplier)
        params.append(
            {
                'from': s.strftime(OANDA_DATETIME_FORMAT),
                'to': e.strftime(OANDA_DATETIME_FORMAT),
                "granularity": granularity
            }
        )

    return params


def get_account_info():
    print(account.mt4)
    r = v20accounts.AccountDetails(account.mt4)
    resp = api.request(r)
    return resp


def get_candlesticks(start, end, granularity):
    """
    Get # of candlesticks
    :param start: datetime
    :param end: datetime
    :param granularity: string
    :return: int
    """

    seconds = (end - start).total_seconds()

    if granularity == 'D':
        return int(np.ceil(seconds / (24 * 60 * 60)))

    if granularity == 'W':
        return int(np.ceil(seconds / (7 * 24 * 60 * 60)))

    if granularity == 'M':
        return int(np.ceil(seconds / (30 * 24 * 60 * 60)))

    nums = int(re.compile(r"\d+$").search(granularity)[0])
    if granularity.startswith('H'):
        return int(np.ceil(seconds / (60 * 60) / nums))

    if granularity.startswith('M'):
        return int(np.ceil(seconds / 60 / nums))

    if granularity.startswith('S'):
        return int(np.ceil(seconds / nums))


if __name__ == '__main__':
    pass
    # start = datetime.now() - timedelta(100)
    # to = datetime.now() - timedelta(1)
    # price_df = read_price_df(instrument='EUR_USD', granularity='H4', start=start, end=to, max_count=20)
    # print(price_df)
