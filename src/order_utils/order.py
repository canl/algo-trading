class OrderStatus(object):
    PENDING = 'pending'
    FILLED = 'filled'
    EXPIRED = 'expired'
    CLOSED = 'closed'


class Order(object):
    def __init__(self, order_date, side, price, sl=None, tp=None, pnl=0, status=OrderStatus.PENDING):
        self.order_date = order_date
        self.side = side
        self.price = price
        self.sl = sl
        self.tp = tp
        self.pnl = pnl
        self.status = status

    def __repr__(self):
        additional_info = f' with stop loss {self.sl} / take profit {self.tp}' if self.sl or self.tp else ''
        return f'{self.order_date}: {self.side} at {self.price}{additional_info}. Current status is {self.status} with pnl {self.pnl}'
