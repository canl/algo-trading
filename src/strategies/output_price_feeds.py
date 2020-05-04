import logging
from datetime import datetime
from functools import partial

import pandas as pd

from src.common import read_price_df
from src.finta.ta import TA

logger = logging.getLogger(__name__)


def output_feeds(instrument: str, st: datetime, et: datetime, short_win: int, long_win: int, ema_period: int, save_dir: str) -> pd.DataFrame:
    """
    Output ohlc price feeds to csv for strategy back testing
    :param instrument: ccy_pair
    :param st: start date
    :param et: end date
    :param short_win:
    :param long_win:
    :param ema_period:
    :param save_dir:
    :return:
    """
    pd_h1 = read_price_df(instrument=instrument, granularity='H1', start=st, end=et)
    pd_h1[f'last_{long_win}_high'] = pd_h1['high'].rolling(window=long_win * 24).max()
    pd_h1[f'last_{short_win}_high'] = pd_h1['high'].rolling(window=short_win * 24).max()
    pd_h1[f'last_{long_win}_low'] = pd_h1['low'].rolling(window=long_win * 24).min()
    pd_h1[f'last_{short_win}_low'] = pd_h1['low'].rolling(window=short_win * 24).min()

    pd_h1.to_csv(f'{save_dir}/{instrument.lower()}_h1_{long_win}_{short_win}.csv')

    pd_d = read_price_df(instrument=instrument, granularity='D', start=st, end=et)
    pd_d[f'last_{long_win}_high'] = pd_d['high'].rolling(window=long_win).max()
    pd_d[f'last_{short_win}_high'] = pd_d['high'].rolling(window=short_win).max()
    pd_d[f'last_{long_win}_low'] = pd_d['low'].rolling(window=long_win).min()
    pd_d[f'last_{short_win}_low'] = pd_d['low'].rolling(window=short_win).min()
    pd_d['atr_20'] = TA.ATR(pd_d, period=20)
    pd_d[f'ema_{ema_period}'] = TA.EMA(pd_d, period=ema_period)

    pd_d.to_csv(f'{save_dir}/{instrument.lower()}_d_{long_win}_{short_win}.csv')

    pd_h1 = pd.read_csv(f'{save_dir}/{instrument.lower()}_h1_{long_win}_{short_win}.csv')

    pd_h1 = pd_h1.apply(partial(enrich, pd_d, ema_period), axis=1).set_index('time')
    logger.info(pd_h1.info())
    pd_h1.to_csv(f"{save_dir}/{instrument.lower()}_h1_enrich_{long_win}_{short_win}.csv")
    logger.info(f'output feeds complete for [{instrument}]!')
    return pd_h1


def enrich(pd_d, ema_period, row):
    d = pd_d[pd_d.index <= row.time]
    row['day_close'] = d['close'][-1]
    row['day_atr_20'] = d['atr_20'][-1]
    row[f'day_ema_{ema_period}'] = d[f'ema_{ema_period}'][-1]
    return row


if __name__ == '__main__':
    popular_pairs = (
        'GBP_USD', 'EUR_USD', 'AUD_USD', 'USD_SGD', 'USD_JPY',
        'GBP_AUD', 'USD_CAD', 'USD_KRW', 'EUR_GBP', 'USD_CHF'
    )
    for inst in popular_pairs:
        output_feeds(instrument=inst, st=datetime(2005, 1, 1), et=datetime(2020, 4, 30), short_win=20, long_win=10, ema_period=55, save_dir='c:/temp')
