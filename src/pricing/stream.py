import json
import logging

import oandapyV20.endpoints.pricing as pricing

from src.env import PRACTICE_ENV

logger = logging.getLogger(__name__)
account = PRACTICE_ENV.account()
env = PRACTICE_ENV
api = PRACTICE_ENV.api()

logger.info('hello')

params = {
    "instruments": "EUR_USD,EUR_JPY,GBP_USD"
}

max_recs = 100
r = pricing.PricingStream(accountID=account.mt4, params=params)
rv = api.request(r)

# print(r.response)
maxrecs = 100
for tick in rv:
    print(json.dumps(r, indent=4), ",")
    if maxrecs == 0:
        r.terminate("maxrecs records received")
