import logging
import configparser
from collections import namedtuple
import os

from oandapyV20 import API

Account = namedtuple('account', 'primary mt4')
logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


class Env(object):
    """
    Manage environment for practice and live account
    """

    def __init__(self, env: str):
        logger.info(f"Running in {env} environment!")
        self.env = env
        self.config = configparser.ConfigParser()
        self.config.read(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'conf', f'oanda-{self.env}.cfg'))

    def api(self):
        return API(environment=self.env, access_token=self.config['oanda']['access_token'])

    def account(self):
        # Oanda by default have 2 accounts: primary and mt4
        oanda_cfg = self.config['oanda']
        return Account(primary=oanda_cfg['account_id_primary'], mt4=oanda_cfg['account_id_mt4'])

    def __repr__(self):
        return f'Current in {self.env} environment'


RUNNING_ENV = Env('practice')

if __name__ == '__main__':
    print(RUNNING_ENV)
    print(RUNNING_ENV.account())
