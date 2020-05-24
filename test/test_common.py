from unittest import TestCase

from datetime import datetime, timedelta

from src.common import get_candlesticks, build_params


class TestCommon(TestCase):
    def test_get_candlesticks(self):
        no_of_days = 500
        test_cases = [
            (500, 'D'),
            (72, 'W'),
            (17, 'M'),
            (500 * 24, 'H1'),
            (500 * 24 / 4, 'H4'),
            (500 * 24 * 60 / 5, 'M5'),
            (500 * 24 * 60 / 10, 'M10'),
        ]
        end = datetime(2020, 3, 31, 21, 0, 0)
        start = datetime(2020, 3, 31, 21, 0, 0) - timedelta(days=no_of_days)
        for expect, granularity in test_cases:
            self.assertEqual(expect, get_candlesticks(start, end, granularity))

    def test_get_params(self):
        look_back_no = 10
        end = datetime(2020, 3, 20, 21, 0, 0)
        start = end - timedelta(days=look_back_no)
        self.assertEqual([
            {
                'from': '2020-03-10T21:00:00',
                'to': '2020-03-20T21:00:00',
                "granularity": 'D'
            }
        ], build_params(granularity='D', start=start, end=end, max_count=1000))

        self.assertTrue(equal_ignore_order([
            {
                'from': '2020-03-10T21:00:00',
                'to': '2020-03-15T21:00:00',
                "granularity": 'D'
            },
            {
                'from': '2020-03-15T21:00:00',
                'to': '2020-03-20T21:00:00',
                "granularity": 'D'
            }
        ], build_params(granularity='D', start=start, end=end, max_count=5)))

    def test_get_param_hours(self):
        end = datetime(2020, 3, 20, 21, 0, 0)
        start = end - timedelta(days=2)
        self.assertTrue(equal_ignore_order([
            {
                'from': '2020-03-20T01:00:00',
                'to': '2020-03-20T21:00:00',
                'granularity': 'H4'
            },
            {
                'from': '2020-03-19T05:00:00',
                'to': '2020-03-20T01:00:00',
                'granularity': 'H4'
            },
            {
                'from': '2020-03-18T21:00:00',
                'to': '2020-03-19T05:00:00',
                'granularity': 'H4'
            }
        ], build_params(granularity='H4', start=start, end=end, max_count=5)))

    def test_get_param_minutes(self):
        end = datetime(2020, 3, 20, 21, 0, 0)
        start = end - timedelta(days=2)
        self.assertTrue(equal_ignore_order([
            {
                'from': '2020-03-20T16:00:00',
                'to': '2020-03-20T21:00:00',
                'granularity': 'M30'
            },
            {
                'from': '2020-03-20T11:00:00',
                'to': '2020-03-20T16:00:00',
                'granularity': 'M30'
            },
            {
                'from': '2020-03-20T06:00:00',
                'to': '2020-03-20T11:00:00',
                'granularity': 'M30'
            },
            {
                'from': '2020-03-20T01:00:00',
                'to': '2020-03-20T06:00:00',
                'granularity': 'M30'
            },
            {
                'from': '2020-03-19T20:00:00',
                'to': '2020-03-20T01:00:00',
                'granularity': 'M30'
            },
            {
                'from': '2020-03-19T15:00:00',
                'to': '2020-03-19T20:00:00',
                'granularity': 'M30'
            },
            {
                'from': '2020-03-19T10:00:00',
                'to': '2020-03-19T15:00:00',
                'granularity': 'M30'
            },
            {
                'from': '2020-03-19T05:00:00',
                'to': '2020-03-19T10:00:00',
                'granularity': 'M30'
            },
            {
                'from': '2020-03-19T00:00:00',
                'to': '2020-03-19T05:00:00',
                'granularity': 'M30'
            },
            {
                'from': '2020-03-18T21:00:00',
                'to': '2020-03-19T00:00:00',
                'granularity': 'M30'
            }
        ], build_params(granularity='M30', start=start, end=end, max_count=10)))


def equal_ignore_order(a, b):
    """ Use only when elements are neither hashable nor sortable! """
    unmatched = list(b)
    for element in a:
        try:
            unmatched.remove(element)
        except ValueError:
            return False
    return not unmatched
