import uuid
from collections import defaultdict

from matching_engine.models import Trade
from matching_engine.order_book import OrderBook


class MatchingEngine:
    def __init__(self):
        self.books: dict[str, OrderBook] = defaultdict(OrderBook)

    def process(self, order):
        book = self.books[order.symbol]
        trades = []

        if order.side == "BUY":
            while book.sells and order.price >= book.best_ask().price:
                best_sell = book.sells.pop(0)

                trade_qty = min(order.quantity, best_sell.quantity)

                trades.append(
                    Trade(
                        trade_id=str(uuid.uuid4()),
                        symbol=order.symbol,
                        buy_order_id=order.order_id,
                        sell_order_id=best_sell.order_id,
                        price=best_sell.price,
                        quantity=trade_qty,
                        buy_client_id=order.client_id,
                        sell_client_id=best_sell.client_id,
                        buy_order_qty=order.order_qty,
                        sell_order_qty=best_sell.order_qty,
                    )
                )

                order.quantity -= trade_qty

                if order.quantity == 0:
                    break

        else:
            while book.buys and order.price <= book.best_bid().price:
                best_buy = book.buys.pop(0)

                trade_qty = min(order.quantity, best_buy.quantity)

                trades.append(
                    Trade(
                        trade_id=str(uuid.uuid4()),
                        symbol=order.symbol,
                        buy_order_id=best_buy.order_id,
                        sell_order_id=order.order_id,
                        price=best_buy.price,
                        quantity=trade_qty,
                        buy_client_id=best_buy.client_id,
                        sell_client_id=order.client_id,
                        buy_order_qty=best_buy.order_qty,
                        sell_order_qty=order.order_qty,
                    )
                )

                order.quantity -= trade_qty

                if order.quantity == 0:
                    break

        if order.quantity > 0:
            book.add_order(order)

        return trades
