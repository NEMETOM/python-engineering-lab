from risk_service.models import RiskDecision, ValidatedOrder
from risk_service.position_store import PositionStore


class RiskChecker:
    def __init__(
        self,
        notional_limit: float,
        fat_finger_pct: float,
        gross_position_limit: int,
        net_position_limit: int,
        max_open_orders: int,
    ):
        self.notional_limit = notional_limit
        self.fat_finger_pct = fat_finger_pct
        self.gross_position_limit = gross_position_limit
        self.net_position_limit = net_position_limit
        self.max_open_orders = max_open_orders

    def check_notional(self, order: ValidatedOrder) -> RiskDecision:
        notional = order.price * order.quantity
        if notional > self.notional_limit:
            return RiskDecision(
                approved=False,
                reason=f"notional {notional:.2f} exceeds limit {self.notional_limit:.2f}",
            )
        return RiskDecision(approved=True)

    def check_fat_finger(
        self, order: ValidatedOrder, last_price: float
    ) -> RiskDecision:
        if last_price <= 0:
            return RiskDecision(approved=True)
        deviation_pct = abs(order.price - last_price) / last_price * 100
        if deviation_pct > self.fat_finger_pct:
            return RiskDecision(
                approved=False,
                reason=(
                    f"price {order.price} deviates {deviation_pct:.1f}% from "
                    f"last {last_price} (limit {self.fat_finger_pct}%)"
                ),
            )
        return RiskDecision(approved=True)

    def check_position(
        self, order: ValidatedOrder, store: PositionStore
    ) -> RiskDecision:
        current_net = store.get_net_position(order.client_id, order.symbol)
        delta = order.quantity if order.side == "BUY" else -order.quantity
        new_net = current_net + delta
        new_gross = abs(new_net)
        if new_gross > self.gross_position_limit:
            return RiskDecision(
                approved=False,
                reason=f"gross position {new_gross} would exceed limit {self.gross_position_limit}",
            )
        if abs(new_net) > self.net_position_limit:
            return RiskDecision(
                approved=False,
                reason=f"net position {new_net} would exceed limit {self.net_position_limit}",
            )
        return RiskDecision(approved=True)

    def check_open_orders(
        self, order: ValidatedOrder, store: PositionStore
    ) -> RiskDecision:
        count = store.get_open_order_count(order.client_id)
        if count >= self.max_open_orders:
            return RiskDecision(
                approved=False,
                reason=f"open order count {count} at limit {self.max_open_orders}",
            )
        return RiskDecision(approved=True)

    def check_all(
        self, order: ValidatedOrder, store: PositionStore, last_prices: dict
    ) -> RiskDecision:
        last_price = last_prices.get(order.symbol, 0.0)
        for check in (
            lambda: self.check_notional(order),
            lambda: self.check_fat_finger(order, last_price),
            lambda: self.check_position(order, store),
            lambda: self.check_open_orders(order, store),
        ):
            decision = check()
            if not decision.approved:
                return decision
        return RiskDecision(approved=True)
