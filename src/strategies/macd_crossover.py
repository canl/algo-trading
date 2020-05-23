"""
Trading strategy using MACD line crossover
    Setup:
        MACD (12, 26, 9)
        EMA 200
        ATR 14

    Rules:
        Entry:
            1. Placing a long order When:
                1) macd line cross over signal line from bottom
                2) crossover happens below 0
                3) price is above 200 EMA
            2. Placing a short order when:
                1) macd line cross over signal line from top
                2) crossover happens above 0
                3) price is below 200 EMA

        Stop loss:
            long: entry - 14 days ATR
            short: entry + 14 days ATR

        Take profit:
            long: entry + 14 days ATR * 1.5
            short: entry - 14 days ATR * 1.5

        Position size:
            2% risk
"""
from functools import partial

from src.common import read_price_df
from datetime import datetime

from src.finta.ta import TA


def enrich(pd_d, row):
    d = pd_d[pd_d.index <= row.time]
    row['day_atr'] = d['atr'][-1]
    return row


if __name__ == '__main__':
    s = datetime(2005, 1, 1)
    e = datetime(2020, 4, 30)
    pd_h1 = read_price_df(instrument='GBP_USD', granularity='H1', start=s, end=e)
    pd_d = read_price_df(instrument='GBP_USD', granularity='D', start=s, end=e)
    pd_h1[['macd', 'signal']] = TA.MACD(pd_h1)
    pd_h1['ema_200'] = TA.EMA(pd_h1, period=200)
    pd_d['atr'] = TA.ATR(pd_d)

    pd_h1.reset_index(level=0, inplace=True)
    pd_h1 = pd_h1.apply(partial(enrich, pd_d), axis=1).set_index('time')

    print(pd_h1)
    pd_h1.to_csv(f'c:/temp/gbp_usd_macd.csv')
