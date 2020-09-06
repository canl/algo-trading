import json
import logging

import oandapyV20.endpoints.accounts as v20accounts
from oandapyV20 import V20Error

from src.env import RUNNING_ENV

logger = logging.getLogger(__name__)


class AccountManager:
    def __init__(self, account):
        self.account_id = RUNNING_ENV.get_account(account)
        self.account_info = {}
        self.get_info()

    @property
    def info(self):
        return self.account_info

    @property
    def nav(self):
        return float(self.account_info['NAV'])

    @property
    def currency(self):
        return self.account_info['currency']

    @property
    def pl(self):
        return float(self.account_info['pl'])

    @property
    def unrealized_pl(self):
        return float(self.account_info['unrealizedPL'])

    @property
    def balance(self):
        return float(self.account_info['balance'])

    @property
    def financing(self):
        return float(self.account_info['financing'])

    @property
    def initial_balance(self):
        return self.balance - (self.pl + self.financing)

    def get_info(self):
        try:
            r = v20accounts.AccountSummary(self.account_id)
            resp = RUNNING_ENV.api.request(r)
        except V20Error as err:
            logging.error(r.status_code, err)
        else:
            logging.info(json.dumps(resp['account'], indent=2))
            self.account_info = resp['account']
            return self.account_info


if __name__ == '__main__':
    RUNNING_ENV.load_config('live')
    am = AccountManager('mt4')
    print(am.nav)
