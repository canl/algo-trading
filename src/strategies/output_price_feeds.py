import logging
from datetime import datetime
from functools import partial

import pandas as pd

from src.common import read_price_df
from src.finta.ta import TA

logger = logging.getLogger(__name__)


def output_feeds(instrument: str, st: datetime, et: datetime, base_path: str, short_win: int, long_win: int) -> pd.DataFrame:
    pd_h1 = read_price_df(instrument=instrument, granularity='H1', start=st, end=et)
    pd_h1[f'last_{long_win}_high'] = pd_h1['high'].rolling(window=long_win * 24).max()
    pd_h1[f'last_{short_win}_high'] = pd_h1['high'].rolling(window=short_win * 24).max()
    pd_h1[f'last_{long_win}_low'] = pd_h1['low'].rolling(window=long_win * 24).min()
    pd_h1[f'last_{short_win}_low'] = pd_h1['low'].rolling(window=short_win * 24).min()

    pd_h1.to_csv(f'{base_path}/{instrument.lower()}_h1_{long_win}_{short_win}.csv')

    pd_d = read_price_df(instrument=instrument, granularity='D', start=st, end=et)
    pd_d[f'last_{long_win}_high'] = pd_d['high'].rolling(window=long_win).max()
    pd_d[f'last_{short_win}_high'] = pd_d['high'].rolling(window=short_win).max()
    pd_d[f'last_{long_win}_low'] = pd_d['low'].rolling(window=long_win).min()
    pd_d[f'last_{short_win}_low'] = pd_d['low'].rolling(window=short_win).min()
    pd_d['atr_20'] = TA.ATR(pd_d, period=20)

    pd_d.to_csv(f'{base_path}/{instrument.lower()}_d_{long_win}_{short_win}.csv')

    pd_h1 = pd.read_csv(f'{base_path}/{instrument.lower()}_h1_{long_win}_{short_win}.csv')

    pd_h1 = pd_h1.apply(partial(enrich, pd_d), axis=1).set_index('time')
    logger.info(pd_h1.info())
    pd_h1.to_csv(f"{base_path}/{instrument.lower()}_h1_enrich_{long_win}_{short_win}.csv")
    logger.info('output feeds complete!')
    return pd_h1


def enrich(pd_d, row):
    d = pd_d[pd_d.index <= row.time]
    row['day_close'] = d['close'][-1]
    row['day_atr_20'] = d['atr_20'][-1]
    return row


if __name__ == '__main__':
    output_feeds(instrument='EUR_USD', st=datetime(2005, 1, 1), et=datetime(2020, 4, 30), base_path='c:/temp', short_win=20, long_win=10)
