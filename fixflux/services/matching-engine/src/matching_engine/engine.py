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
                # Peek, don't pop: a resting order that is only partly filled
                # must keep its remainder at the front of its price level
                # (time priority). Popping first silently discarded it.
                best_sell = book.sells[0]

                trade_qty = min(order.quantity, best_sell.quantity)
                order.quantity -= trade_qty
                best_sell.quantity -= trade_qty
                if best_sell.quantity == 0:
                    book.sells.pop(0)

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
                        buy_approved_at=order.approved_at,
                        sell_approved_at=best_sell.approved_at,
                        buy_leaves_qty=order.quantity,
                        sell_leaves_qty=best_sell.quantity,
                    )
                )

                if order.quantity == 0:
                    break

        else:
            while book.buys and order.price <= book.best_bid().price:
                best_buy = book.buys[0]  # peek - see the BUY branch

                trade_qty = min(order.quantity, best_buy.quantity)
                order.quantity -= trade_qty
                best_buy.quantity -= trade_qty
                if best_buy.quantity == 0:
                    book.buys.pop(0)

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
                        buy_approved_at=best_buy.approved_at,
                        sell_approved_at=order.approved_at,
                        buy_leaves_qty=best_buy.quantity,
                        sell_leaves_qty=order.quantity,
                    )
                )

                if order.quantity == 0:
                    break

        if order.quantity > 0:
            book.add_order(order)

        return trades
