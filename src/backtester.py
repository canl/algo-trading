from functools import reduce

import pandas as pd
from matplotlib import pyplot as plt

from src.orders.order import OrderStatus


class BackTester:
    """
    Purpose: Backtesting and output performance report
    """

    def __init__(self, strategy: str = '', initial_cash: float = 10000, commission: float = .0, lot_size: float = 100000):
        self.strategy = strategy
        self.initial_cash = initial_cash
        self.commission = commission
        self.lot_size = lot_size

    def run(self, price_feed: pd.DataFrame, orders: list, print_stats=True, output_csv=False, suffix='') -> pd.DataFrame:
        """
        bask testing strategies
        :param price_feed: Price feed DataFrame
        :param orders: list of Orders
        :param print_stats: bool, printout stats
        :param output_csv: bool, output csv
        :param suffix: used for chart plotting in order to differentiate strategy with different parameters
        :return: pd.DataFrame
        """
        price_dict = price_feed.to_dict('index')
        performance = []
        for time, ohlc in price_dict.items():
            for o in orders:
                should_take_action = o.is_open and time >= o.last_update
                if should_take_action:
                    # Fill pending orders
                    if o.is_pending:
                        if o.is_long:
                            if ohlc['high'] > o.entry:  # buy order filled
                                o.fill(time)
                        elif o.is_short:
                            if ohlc['low'] < o.entry:  # sell order filled
                                o.fill(time)
                    # Close filled orders
                    if o.is_filled:
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

            position = sum(o.pnl for o in orders) * self.lot_size + self.initial_cash  # 1 standard lot = 100,000
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
    def print_stats(orders) -> dict:
        pip_size = 10000
        no_of_wins = len([o for o in orders if o.outcome == 'win'])
        no_of_losses = len([o for o in orders if o.outcome == 'loss'])
        avg_win = sum(o.pnl for o in orders if o.outcome == 'win') / no_of_wins if no_of_wins else 0
        avg_loss = sum(o.pnl for o in orders if o.outcome == 'loss') / no_of_losses if no_of_losses else 0
        total_pips = sum(o.pnl for o in orders) * pip_size
        win_percent = 0 if no_of_wins == 0 else round(no_of_wins / (no_of_wins + no_of_losses), 4)
        win_loss_ratio = abs(round(avg_win / avg_loss, 2)) if avg_loss else 0
        expectancy = round(win_percent * win_loss_ratio - (1 - win_percent), 4)

        stats = {
            'total orders placed': len(orders),
            'buys': len([el for el in orders if el.is_long]),
            'sells': len([el for el in orders if el.is_short]),
            'closed': len([el for el in orders if el.status == OrderStatus.CLOSED]),
            'cancelled': len([el for el in orders if el.status == OrderStatus.CANCELLED]),
            'wins': no_of_wins,
            'losses': no_of_losses,
            'average win': f'{round(avg_win * pip_size, 2)} pips',
            'average loss': f'{round(avg_loss * pip_size, 2)} pips',
            'win rate': 0 if no_of_wins == 0 else f'{round((no_of_wins / (no_of_wins + no_of_losses) * 100), 2)}%',
            'win / loss ratio': abs(round(avg_win / avg_loss, 2)) if avg_loss else 0,
            'total pnl': round(total_pips, 4),
            'expectancy': expectancy
        }

        for k, v in stats.items():
            print(f'{k}: {v}')

        return stats

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

    def plot_chart(self, dfs: list):
        """
        plot based on the back testing result
        :param dfs: lis of pd.DataFrame
        """
        plt.style.use('ggplot')

        df_final = reduce(lambda left, right: pd.merge(left, right, on='time'), dfs)
        df_final.plot()

        plt.xlabel('Time')
        plt.ylabel('Performance')
        plt.title(f'Performance of {self.strategy}')
        plt.legend()
        plt.show()
