import pandas as pd
from matplotlib import pyplot as plt
from functools import reduce
from src.order_utils.order import Order, OrderStatus

plt.style.use('ggplot')


class BackTester:
    """
    Purpose: Backtesting and output performance report
    """

    def __init__(self, initial_cash: float = 10000, commission: float = .0, lot_size: float = 0.1):
        self.initial_cash = initial_cash
        self.commission = commission
        self.lot_size = lot_size

    def run(self, price_feed: pd.DataFrame, orders: list, print_stats=True, output_csv=False, suffix=''):
        """
        bask testing strategies
        :param price_feed: Price feed DataFrame
        :param orders: list of Orders
        :param print_stats: bool, printout stats
        :param output_csv: bool, output csv
        :param suffix: used for chart plotting in order to differentiate strategy with different parameters
        :return:
        """
        price_dict = price_feed.to_dict('index')
        performance = []
        for time, ohlc in price_dict.items():
            for o in orders:
                should_take_action = o.is_filled and time >= o.last_update
                if should_take_action:
                    if o.is_long:
                        if ohlc['low'] <= o.sl:
                            o.close_with_loss(time)
                        elif ohlc['high'] > o.tp:
                            o.close_with_win(time)
                    elif o.is_short:
                        if ohlc['high'] >= o.sl:
                            o.close_with_loss(time)
                        elif ohlc['low'] < o.tp:
                            o.close_with_win(time)

            position = sum(o.pnl for o in orders) * self.lot_size * 100000 + self.initial_cash  # 1 standard lot = 100,000
            performance.append({
                'time': time,
                f'pnl{suffix}': position
            })

        if print_stats:
            self.print_stats(orders)

        if output_csv:
            self.output_csv(orders)

        return pd.DataFrame(performance).set_index('time')

    @staticmethod
    def print_stats(orders):
        no_of_wins = len([o for o in orders if o.outcome == 'win'])
        no_of_losses = len([o for o in orders if o.outcome == 'loss'])
        avg_win = sum(o.pnl for o in orders if o.outcome == 'win') / no_of_wins if no_of_wins else 0
        avg_loss = sum(o.pnl for o in orders if o.outcome == 'loss') / no_of_losses if no_of_losses else 0
        total_pips = sum(o.pnl for o in orders) * 10000
        win_percent = round(no_of_wins / (no_of_wins + no_of_losses), 4)
        win_loss_ratio = abs(round(avg_win / avg_loss, 2)) if avg_loss else 0
        expectancy = round(win_percent * win_loss_ratio - (1 - win_percent), 4)
        print(
            '{} orders placed.\nbuy orders: {}\nsell orders: {}\nclosed orders: {}\ncancelled orders: {}\nwin Orders: {}\nloss orders: {}\n'
            'avg_win: {} pips\navg_loss: {} pips\nwin%: {}%\nwin/loss ratio: {}\ntotal pnl: {}\nexpectancy: {}'.format(
                len(orders),
                len([el for el in orders if el.is_long]),
                len([el for el in orders if el.is_short]),
                len([el for el in orders if el.status == OrderStatus.CLOSED]),
                len([el for el in orders if el.status == OrderStatus.CANCELLED]),
                no_of_wins,
                no_of_losses,
                round(avg_win * 10000, 2),
                round(avg_loss * 10000, 2),
                round((no_of_wins / (no_of_wins + no_of_losses) * 100), 2),
                abs(round(avg_win / avg_loss, 2)) if avg_loss else 0,
                round(total_pips, 4),
                expectancy
            ))

    @staticmethod
    def output_csv(orders: list, path=r'C:\temp\order_performs.csv'):
        to_csv = [{
            'id': o.id,
            'side': o.side,
            'created': o.order_date,
            'entry': o.entry,
            'stop_loss': o.sl,
            'take_profit': o.tp,
            'outcome': o.outcome,
            'pnl': o.pnl,
            'updated': o.last_update
        } for o in orders]

        df = pd.DataFrame(to_csv)
        df.to_csv(path)

    @staticmethod
    def plot_chart(dfs: list):
        """
        plot based on the back testing result
        :param dfs: lis of pd.DataFrame
        """
        df_final = reduce(lambda left, right: pd.merge(left, right, on='time'), dfs)
        df_final.plot()
        plt.show()
