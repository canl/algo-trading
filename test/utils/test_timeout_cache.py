from unittest import TestCase
import time

from src.order_utils.order_manager import OrderManager
from src.trading.london_breakout import LondonBreakout
from src.utils.timeout_cache import cache


class TestLondonBreakout(TestCase):
    def test_cache(self):
        count = 0

        @cache(seconds=1)
        def foo():
            nonlocal count
            count += 1
            return count

        assert foo() == 1, "Function should be called the first time we invoke it"
        assert foo() == 1, "Function should not be called because it is already cached"

        # Let's now wait for the cache to expire
        time.sleep(1)

        assert foo() == 2, "Function should be called because the cache already expired"
