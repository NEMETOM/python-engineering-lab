import uuid

from matching_engine.models import Trade


class MatchingEngine:

    def __init__(self, book):

        self.book = book

    def process(self, order):

        trades = []

        if order.side == "BUY":

            while self.book.sells and order.price >= self.book.best_ask().price:

                best_sell = self.book.sells.pop(0)

                trade_qty = min(order.quantity, best_sell.quantity)

                trades.append(
                    Trade(
                        trade_id=str(uuid.uuid4()),
                        symbol=order.symbol,
                        buy_order_id=order.order_id,
                        sell_order_id=best_sell.order_id,
                        price=best_sell.price,
                        quantity=trade_qty,
                    )
                )

                order.quantity -= trade_qty

                if order.quantity == 0:
                    break

        else:

            while self.book.buys and order.price <= self.book.best_bid().price:

                best_buy = self.book.buys.pop(0)

                trade_qty = min(order.quantity, best_buy.quantity)

                trades.append(
                    Trade(
                        trade_id=str(uuid.uuid4()),
                        symbol=order.symbol,
                        buy_order_id=best_buy.order_id,
                        sell_order_id=order.order_id,
                        price=best_buy.price,
                        quantity=trade_qty,
                    )
                )

                order.quantity -= trade_qty

                if order.quantity == 0:
                    break

        if order.quantity > 0:

            self.book.add_order(order)

        return trades
