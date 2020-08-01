import logging
import json

import oandapyV20.endpoints.accounts as v20accounts
from oandapyV20 import V20Error

from src.env import RUNNING_ENV
from src.utils.timeout_cache import cache

logger = logging.getLogger(__name__)


class AccountManager:
    def __init__(self, account):
        self.account_id = RUNNING_ENV.get_account(account)

    @property
    def nav(self):
        return float(self.get_info()['NAV'])

    @property
    def pl(self):
        return float(self.get_info()['pl'])

    @property
    def unrealized_pl(self):
        return float(self.get_info()['unrealizedPL'])

    @property
    def balance(self):
        return float(self.get_info()['balance'])

    @property
    def financing(self):
        return float(self.get_info()['financing'])

    @property
    def initial_balance(self):
        return self.balance - (self.pl + self.financing)

    @cache(seconds=3600)
    def get_info(self):
        try:
            r = v20accounts.AccountSummary(self.account_id)
            resp = RUNNING_ENV.api.request(r)
        except V20Error as err:
            logging.error(r.status_code, err)
        else:
            logging.info(json.dumps(resp['account'], indent=2))
            return resp['account']


if __name__ == '__main__':
    am = AccountManager('mt4')
    am.get_info()
    print(am.nav)
