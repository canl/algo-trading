import logging
import queue
import threading

from src.event import TickEvent
from src.pricing.stream import StreamingPrices

logger = logging.getLogger(__name__)


class StreamPriceEvent:
    def __init__(self, instruments: list, events: queue.Queue, max_rec: int = None, account: str = 'mt4'):
        self.instruments = instruments
        self.events = events
        self.max_rec = max_rec
        self.account = account

    def start(self):
        sp = StreamingPrices(self.instruments, self.stream_to_queue, max_rec=self.max_rec, account=self.account)
        sp.run()

    def stream_to_queue(self, price: dict):
        if price['type'] == 'PRICE':
            tick = TickEvent(price['instrument'], price['time'], price['closeoutBid'], price['closeoutAsk'])
            self.events.put(tick)


if __name__ == '__main__':
    # For testing
    qe = queue.Queue()
    spe = StreamPriceEvent(['GBP_USD', 'GBP_AUD', 'EUR_GBP', 'EUR_USD'], qe, 50)
    price_thread = threading.Thread(target=spe.start)
    price_thread.start()

    while True:
        try:
            event = qe.get()
        except qe.empty():
            print('nothing in the queue!')
        else:
            print(f"Event received: {event}")
