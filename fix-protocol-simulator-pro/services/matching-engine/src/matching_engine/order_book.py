class OrderBook:

    def __init__(self):

        self.buys = []
        self.sells = []

    def add_order(self, order):

        if order.side == "BUY":

            self.buys.append(order)

            self.buys.sort(key=lambda x: -x.price)

        else:

            self.sells.append(order)

            self.sells.sort(key=lambda x: x.price)

    def best_bid(self):

        return self.buys[0] if self.buys else None

    def best_ask(self):

        return self.sells[0] if self.sells else None
