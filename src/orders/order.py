import random


class OrderStatus:
    PENDING = 'pending'
    FILLED = 'filled'
    EXPIRED = 'expired'
    CLOSED = 'closed'
    CANCELLED = 'cancelled'


class OrderSide:
    LONG = 'long'
    SHORT = 'short'


class Order(object):
    def __init__(self, order_date, side, entry, sl=None, tp=None, pnl=0, status=OrderStatus.PENDING, last_update=None, units=100000):
        """
        Order for execution
        :param order_date: Datetime
        :param side: Long or Short
        :param entry: float
        :param sl: float
        :param tp: float
        :param pnl: float
        :param status: OrderStatus
        :param last_update: Datetime
        :param units: default 1 standard lot, 100,000 units
        """
        self.id = ''.join(random.choice('0123456789ABCDEF') for i in range(6))  # not unique but should be good enough
        self.order_date = order_date
        self.side = side
        self.entry = entry
        self.sl = sl
        self.tp = tp
        self.pnl = pnl
        self.status = status
        self.last_update = last_update or self.order_date
        self.units = units

    @property
    def outcome(self):
        if self.pnl > 0:
            return 'win'
        if self.pnl < 0:
            return 'loss'
        return 'tie'

    @property
    def is_long(self):
        return self.side == OrderSide.LONG

    @property
    def is_short(self):
        return self.side == OrderSide.SHORT

    @property
    def is_open(self):
        return self.status == OrderStatus.PENDING or self.status == OrderStatus.FILLED

    @property
    def is_pending(self):
        return self.status == OrderStatus.PENDING

    @property
    def is_filled(self):
        return self.status == OrderStatus.FILLED

    @property
    def is_cancelled(self):
        return self.status == OrderStatus.CANCELLED

    def fill(self, fill_time, filled_price=None):
        if filled_price:
            self.entry = filled_price
        self.status = OrderStatus.FILLED
        self.last_update = fill_time

    def cancel(self, cancel_time):
        self.status = OrderStatus.CANCELLED
        self.last_update = cancel_time

    def close_with_win(self, close_time, close_price=None):
        if close_price:
            self.tp = close_price
        self._close_order(close_time, close_price or self.tp)

    def close_with_loss(self, close_time, close_price=None):
        if close_price:
            self.sl = close_price
        self._close_order(close_time, close_price or self.sl)

    def _close_order(self, close_time, close_price):
        self.status = OrderStatus.CLOSED
        self.last_update = close_time
        multiplier = 1 if self.side == OrderSide.LONG else -1
        self.pnl = (close_price - self.entry) * multiplier

    def __bool__(self):
        return bool(self.entry or self.sl or self.tp)

    def __repr__(self):
        additional_info = f' with stop loss {self.sl} / take profit {self.tp}' if self.sl or self.tp else ''
        return f'<{self.id}: ' \
               f'{self.order_date} {self.side} {self.units} units @ {self.entry}{additional_info}. ' \
               f'Status is {self.status} with pnl {self.pnl}. Last updated @ {self.last_update}>'

    __str__ = __repr__
