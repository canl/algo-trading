import argparse
import logging
from datetime import datetime

import pandas as pd

from src.common import read_price_df
from src.finta.ta import TA

logger = logging.getLogger(__name__)


def output_feeds(instrument: str, short_win: int, long_win: int, ema_period: int, save_dir: str, st: datetime, et: datetime = None) -> pd.DataFrame:
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

    pd_d = read_price_df(instrument=instrument, granularity='D', start=st, end=et)
    pd_d[f'last_{long_win}_high'] = pd_d['high'].rolling(window=long_win).max()
    pd_d[f'last_{short_win}_high'] = pd_d['high'].rolling(window=short_win).max()
    pd_d[f'last_{long_win}_low'] = pd_d['low'].rolling(window=long_win).min()
    pd_d[f'last_{short_win}_low'] = pd_d['low'].rolling(window=short_win).min()
    pd_d['atr'] = TA.ATR(pd_d, period=14)
    pd_d['adx'] = TA.ADX(pd_d, period=14)
    pd_d['rsi'] = TA.RSI(pd_d, period=14)
    pd_d[f'ema_{ema_period}'] = TA.EMA(pd_d, period=ema_period)

    pd_d.to_csv(f'{save_dir}/{instrument.lower()}_d.csv')
    logger.info(f'output feeds complete for [{instrument}]!')
    return pd_d


def run(save_dir):
    popular_pairs = (
        'GBP_USD', 'EUR_USD', 'AUD_USD', 'USD_SGD', 'USD_JPY',
        'GBP_AUD', 'USD_CAD', 'EUR_GBP', 'USD_CHF', 'BCO_USD'
    )
    for inst in popular_pairs:
        output_feeds(instrument=inst, st=datetime(2019, 1, 1), et=None, short_win=20, long_win=10, ema_period=55, save_dir=save_dir)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="London Breakout Strategy")
    parser.add_argument('--saveDir', action="store", dest="saveDir", default='c:/temp/prices')
    args = parser.parse_args()
    run(args.saveDir)
