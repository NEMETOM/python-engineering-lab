# fix-protocol-simulator/src/fix_simulator/exchange/order_book.py

import logging

logger = logging.getLogger(__name__)


class OrderBook:

    def __init__(self):

        self.bids = []
        self.asks = []

    def add_order(self, order):

        logger.info(f"Adding order {order}")

        if order.side == "BUY":
            self.bids.append(order)

        else:
            self.asks.append(order)

    def best_bid(self):

        if not self.bids:
            return None

        return max(self.bids, key=lambda o: o.price)

    def best_ask(self):

        if not self.asks:
            return None

        return min(self.asks, key=lambda o: o.price)
