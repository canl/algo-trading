import logging
import queue
import threading
import time

import oandapyV20.endpoints.pricing as pricing
from typing import List

from src.env import RUNNING_ENV
from src.event import TickEvent

logger = logging.getLogger(__name__)


class PollPriceEvent:
    def __init__(self, instruments: list, events: queue.Queue, heartbeat: int = 10, account: str = 'mt4'):
        """

        :param instruments: instrument list: ['GBP_USD', 'GBP_AUD', 'EUR_GBP', 'EUR_USD']
        :param events: shared event queue for processing the events
        :param heartbeat: frequency in seconds between polling
        :param account: trading account
        """
        self.instruments = instruments
        self.events = events
        self.heartbeat = heartbeat
        self.account_id = RUNNING_ENV.get_account(account)

    def start(self):
        """
        Polling price events with frequency in heartbeat seconds
        :return:
        """
        while True:
            for e in self.poll():
                self.events.put(e)
            time.sleep(self.heartbeat)

    def poll(self) -> List[TickEvent]:
        tick_events = []
        params = {"instruments": ",".join(self.instruments)}
        req = pricing.PricingInfo(accountID=self.account_id, params=params)
        resp = RUNNING_ENV.api.request(req)
        if resp:
            for price in resp['prices']:
                try:
                    tick_events.append(
                        TickEvent(price['instrument'], price['time'], price['bids'][0]['price'], price['asks'][0]['price'])
                    )
                except Exception as ex:
                    logger.error(f"Failed to read the price with error: {ex}")
        return tick_events


if __name__ == '__main__':
    # For testing
    qe = queue.Queue()
    ppe = PollPriceEvent(['GBP_USD', 'GBP_AUD', 'EUR_GBP', 'EUR_USD'], qe, 10)
    # ppe.start()
    price_thread = threading.Thread(target=ppe.start)
    price_thread.start()

    while True:
        try:
            event = qe.get()
        except qe.empty():
            print('nothing in the queue!')
        else:
            print(f"Event received: {event}")
