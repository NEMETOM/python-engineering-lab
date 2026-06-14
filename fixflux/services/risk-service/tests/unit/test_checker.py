from datetime import datetime, timezone

from risk_service.checker import RiskChecker
from risk_service.models import ValidatedOrder
from risk_service.position_store import PositionStore


def _checker(**overrides):
    defaults = dict(
        notional_limit=1_000_000.0,
        fat_finger_pct=10.0,
        gross_position_limit=10_000,
        net_position_limit=5_000,
        max_open_orders=10,
    )
    defaults.update(overrides)
    return RiskChecker(**defaults)


def _order(**overrides):
    defaults = dict(
        order_id="O1",
        symbol="AAPL",
        side="BUY",
        price=100.0,
        quantity=10,
        timestamp=datetime.now(timezone.utc),
        client_id="C1",
    )
    defaults.update(overrides)
    return ValidatedOrder(**defaults)


class TestNotionalCheck:
    def test_below_limit_is_approved(self):
        d = _checker(notional_limit=1_000_000).check_notional(
            _order(price=100.0, quantity=100)
        )
        assert d.approved

    def test_exactly_at_limit_is_approved(self):
        # 100 * 10000 == 1_000_000 (strict greater-than in checker)
        d = _checker(notional_limit=1_000_000).check_notional(
            _order(price=100.0, quantity=10_000)
        )
        assert d.approved

    def test_above_limit_is_rejected(self):
        d = _checker(notional_limit=1_000_000).check_notional(
            _order(price=100.0, quantity=10_001)
        )
        assert not d.approved

    def test_rejection_reason_contains_notional(self):
        d = _checker(notional_limit=500).check_notional(
            _order(price=100.0, quantity=10)
        )
        assert "notional" in d.reason

    def test_large_price_small_qty_can_breach(self):
        d = _checker(notional_limit=1_000).check_notional(
            _order(price=10_001.0, quantity=1)
        )
        assert not d.approved


class TestFatFingerCheck:
    def test_within_threshold_is_approved(self):
        # last=100, order=105 → 5% deviation, threshold=10%
        d = _checker().check_fat_finger(_order(price=105.0), last_price=100.0)
        assert d.approved

    def test_exactly_at_threshold_is_approved(self):
        # 10% of 100 = 10, order=110 → exactly 10%, strict greater-than
        d = _checker(fat_finger_pct=10.0).check_fat_finger(
            _order(price=110.0), last_price=100.0
        )
        assert d.approved

    def test_above_threshold_is_rejected(self):
        # last=100, order=115 → 15% deviation, threshold=10%
        d = _checker(fat_finger_pct=10.0).check_fat_finger(
            _order(price=115.0), last_price=100.0
        )
        assert not d.approved

    def test_rejection_reason_contains_deviates(self):
        d = _checker(fat_finger_pct=5.0).check_fat_finger(
            _order(price=200.0), last_price=100.0
        )
        assert "deviates" in d.reason

    def test_no_reference_price_skips_check(self):
        # last_price=0 means no reference - should always approve
        d = _checker().check_fat_finger(_order(price=99_999.0), last_price=0.0)
        assert d.approved

    def test_downward_deviation_is_also_checked(self):
        # last=100, order=85 → 15% below, threshold=10%
        d = _checker(fat_finger_pct=10.0).check_fat_finger(
            _order(price=85.0), last_price=100.0
        )
        assert not d.approved


class TestPositionCheck:
    def setup_method(self):
        self.store = PositionStore()

    def test_flat_position_buy_within_limit_is_approved(self):
        d = _checker(gross_position_limit=10_000).check_position(
            _order(side="BUY", quantity=5_000), self.store
        )
        assert d.approved

    def test_exactly_at_gross_limit_is_approved(self):
        # net_limit matches gross_limit so only the gross boundary is under test
        d = _checker(
            gross_position_limit=10_000, net_position_limit=10_000
        ).check_position(_order(side="BUY", quantity=10_000), self.store)
        assert d.approved

    def test_exceeding_gross_limit_is_rejected(self):
        d = _checker(gross_position_limit=10_000).check_position(
            _order(side="BUY", quantity=10_001), self.store
        )
        assert not d.approved

    def test_gross_rejection_reason_contains_gross_position(self):
        d = _checker(gross_position_limit=100).check_position(
            _order(side="BUY", quantity=101), self.store
        )
        assert "gross position" in d.reason

    def test_exceeding_net_limit_with_large_gross_limit_is_rejected(self):
        # gross_limit=20000 won't trip, but net_limit=4999 will
        d = _checker(
            gross_position_limit=20_000, net_position_limit=4_999
        ).check_position(_order(side="BUY", quantity=5_000), self.store)
        assert not d.approved

    def test_net_rejection_reason_contains_net_position(self):
        d = _checker(
            gross_position_limit=20_000, net_position_limit=4_999
        ).check_position(_order(side="BUY", quantity=5_000), self.store)
        assert "net position" in d.reason

    def test_existing_long_reduces_available_sell_headroom(self):
        # Client is already long 8000; a SELL of 3000 → new_net = +5000, gross = 5000 - OK
        self.store.record_open_order("O-PREV", "C1", "AAPL", "BUY", 8_000)
        self.store.fill_order("O-PREV")
        d = _checker(gross_position_limit=10_000).check_position(
            _order(side="SELL", quantity=3_000), self.store
        )
        assert d.approved

    def test_existing_long_blocks_further_buy_above_limit(self):
        self.store.record_open_order("O-PREV", "C1", "AAPL", "BUY", 9_000)
        self.store.fill_order("O-PREV")
        d = _checker(gross_position_limit=10_000).check_position(
            _order(side="BUY", quantity=1_001), self.store
        )
        assert not d.approved


class TestOpenOrderCheck:
    def setup_method(self):
        self.store = PositionStore()

    def test_below_limit_is_approved(self):
        for i in range(4):
            self.store.record_open_order(f"O{i}", "C1", "AAPL", "BUY", 10)
        d = _checker(max_open_orders=5).check_open_orders(_order(), self.store)
        assert d.approved

    def test_exactly_at_limit_is_rejected(self):
        for i in range(5):
            self.store.record_open_order(f"O{i}", "C1", "AAPL", "BUY", 10)
        d = _checker(max_open_orders=5).check_open_orders(_order(), self.store)
        assert not d.approved

    def test_rejection_reason_contains_open_order_count(self):
        for i in range(3):
            self.store.record_open_order(f"O{i}", "C1", "AAPL", "BUY", 10)
        d = _checker(max_open_orders=3).check_open_orders(_order(), self.store)
        assert "open order count" in d.reason

    def test_other_clients_orders_do_not_count(self):
        for i in range(10):
            self.store.record_open_order(f"O{i}", "C2", "AAPL", "BUY", 10)
        d = _checker(max_open_orders=5).check_open_orders(
            _order(client_id="C1"), self.store
        )
        assert d.approved


class TestCheckAll:
    def setup_method(self):
        self.store = PositionStore()
        self.checker = _checker()

    def test_all_checks_pass_returns_approved(self):
        d = self.checker.check_all(_order(), self.store, {})
        assert d.approved

    def test_notional_failure_stops_at_first_check(self):
        # Notional breaches; fat-finger and position would pass
        d = _checker(notional_limit=1).check_all(
            _order(price=100.0, quantity=10), self.store, {}
        )
        assert not d.approved
        assert "notional" in d.reason

    def test_fat_finger_failure_uses_last_prices_dict(self):
        last_prices = {"AAPL": 100.0}
        # price=200 is 100% deviation on a 10% threshold - fat finger fires
        d = _checker(fat_finger_pct=10.0).check_all(
            _order(price=200.0), self.store, last_prices
        )
        assert not d.approved
        assert "deviates" in d.reason

    def test_position_failure_is_caught_by_check_all(self):
        d = _checker(gross_position_limit=5).check_all(
            _order(quantity=6), self.store, {}
        )
        assert not d.approved
        assert "gross position" in d.reason

    def test_unknown_symbol_in_last_prices_skips_fat_finger(self):
        # "BTCUSD" not in last_prices → fat_finger is skipped
        d = _checker(fat_finger_pct=1.0).check_all(
            _order(symbol="BTCUSD", price=99_999.0), self.store, {}
        )
        assert d.approved
