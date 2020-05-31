import json
import logging
import time

from oandapyV20 import V20Error
from oandapyV20.endpoints.pricing import PricingStream
from oandapyV20.exceptions import StreamTerminated

from src.env import RUNNING_ENV

logger = logging.getLogger(__name__)
env = RUNNING_ENV
account = env.account()
api = env.api()


class StreamingPrices:
    def __init__(self, instruments, callback, max_rec=None):
        self.instruments = instruments
        self.max_rec = max_rec
        self.callback = callback

    def run(self):
        c = 0
        r = PricingStream(accountID=account.mt4, params={"instruments": ",".join(self.instruments)})
        try:
            for ticks in api.request(r):
                self.callback(ticks)
                c += 1
                if self.max_rec and c >= self.max_rec:
                    r.terminate(f"Maximum heartbeats received: {c}")
        except V20Error as e:
            # catch API related errors that may occur
            logger.error(f"V20Error: {e}")

        except ConnectionError as e:
            logger.error(f"ConnectionError: {e}")
            time.sleep(2)

        except StreamTerminated as e:
            logger.error(f"StreamTerminated: {e}")

        except Exception as e:
            logger.error(f"Some exception: {e}")


if __name__ == '__main__':
    def print_data(message):
        print(json.dumps(message, indent=4), ",")


    sp = StreamingPrices(['GBP_USD', 'EUR_USD'], print_data, max_rec=10)
    sp.run()
