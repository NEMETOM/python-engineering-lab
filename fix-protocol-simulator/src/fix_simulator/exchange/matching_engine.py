#fix-protocol-simulator/src/fix_simulator/exchange/matching_engine.py

import logging

logger = logging.getLogger(__name__)


class MatchingEngine:

    def __init__(self, order_book):

        self.order_book = order_book

    def process_order(self, order):

        logger.info(f"Processing order {order.order_id}")

        if order.side == "BUY":

            best_ask = self.order_book.best_ask()

            if best_ask and order.price >= best_ask.price:

                return self.execute_trade(order, best_ask)

        if order.side == "SELL":

            best_bid = self.order_book.best_bid()

            if best_bid and order.price <= best_bid.price:

                return self.execute_trade(order, best_bid)

        self.order_book.add_order(order)

        return None

    def execute_trade(self, order, counterparty):

        trade_price = counterparty.price
        quantity = min(order.quantity, counterparty.quantity)

        logger.info(
            f"Trade executed price={trade_price} qty={quantity}"
        )

        return {
            "price": trade_price,
            "quantity": quantity
        }