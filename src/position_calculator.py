import logging
from functools import lru_cache

from src.pricer import api_request

logger = logging.getLogger(__name__)


def pos_size(account_balance: float, risk_pct: float, sl_pips: float, instrument: str = 'GBP_USD', account_ccy: str = 'GBP') -> float:
    """
    Calculate standard lots of currency units to buy or sell to control our maximum risk per position.
    :param account_balance:
    :param risk_pct: percentage in float. if it's 20%, then 0.2
    :param sl_pips: stop loss in pips
    :param instrument: currency pair, e.g EUR_USD
    :param account_ccy: default to GBP
    :return: standard lots
    """
    special_instruments = ('XAU', 'JPY', 'BCO')  # special_instruments' pip is the second place after the decimal (0.01) rather than the fourth (0.0001).
    multiplier = 0.01 if any(inst in instrument for inst in special_instruments) else 0.0001
    pip_value = 100000 * multiplier  # standard lot size * pip, i.e 100000 * 0.0001
    close = get_fx_rate(account_ccy, instrument)
    risk_amt = account_balance * risk_pct
    return round(risk_amt / (sl_pips * pip_value) * float(close), 4)


@lru_cache(1000)
def get_fx_rate(account_ccy: str, instrument: str):
    """
    Get latest fx rates against USD
    :param account_ccy: GBP, EUR
    :param instrument: currency pair, e.g. EUR_USD
    :return:
    """
    counter_ccy = instrument.split('_')[-1]
    if account_ccy == counter_ccy:
        return 1.0

    p = {
        "count": 1,
        "granularity": "M1"
    }
    resp = api_request(f'{account_ccy}_{counter_ccy}', p)
    close = resp['candles'][0]['mid']['c']
    logger.info(f'Close fx rate is: {close}')
    return close


if __name__ == '__main__':
    print(pos_size(10000, 0.02, 50, 'GBP_NZD'))
    print(pos_size(10000, 0.02, 50, 'EUR_JPY'))
    print(pos_size(10000, 0.02, 50, 'XAU_USD'))
    print(pos_size(10000, 0.02, 50, 'USD_JPY'))
    print(pos_size(10000, 0.02, 50, 'AUD_JPY', 'EUR'))
    print(pos_size(10000, 0.02, 50, 'EUR_AUD'))
    print(pos_size(10000, 0.02, 50, 'BCO_USD'))
