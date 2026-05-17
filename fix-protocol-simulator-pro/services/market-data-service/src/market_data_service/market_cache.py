from datetime import datetime


class MarketCache:

    def __init__(self):

        self.best_bid = None

        self.best_ask = None

        self.last_trade_price = None

    def update_trade(self, trade):

        self.last_trade_price = trade["price"]

    def update_order_book(self, book):

        self.best_bid = book["best_bid"]

        self.best_ask = book["best_ask"]

    def snapshot(self):

        mid = None

        if self.best_bid and self.best_ask:

            mid = (self.best_bid + self.best_ask) / 2

        return {
            "best_bid": self.best_bid,
            "best_ask": self.best_ask,
            "mid_price": mid,
            "last_trade_price": self.last_trade_price,
            "timestamp": datetime.utcnow().isoformat(),
        }
