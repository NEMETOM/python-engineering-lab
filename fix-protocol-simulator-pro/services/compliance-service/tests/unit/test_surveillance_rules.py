import pytest

from compliance_service.rules.surveillance.rapid_fire import RapidFireRule
from compliance_service.rules.surveillance.repeated_orders import RepeatedOrdersRule
from compliance_service.rules.surveillance.volume_spike import VolumeSpikeRule
from compliance_service.rules.surveillance.wash_trading import WashTradingRule


class TestWashTradingRule:
    def setup_method(self):
        self.rule = WashTradingRule({"enabled": True, "window_seconds": 300})

    def _event(self, client_id: str, symbol: str, side: str) -> dict:
        return {"client_id": client_id, "symbol": symbol, "side": side}

    def test_buy_then_sell_same_symbol_is_flagged(self):
        self.rule.check(self._event("C1", "EURUSD", "BUY"))
        violation = self.rule.check(self._event("C1", "EURUSD", "SELL"))
        assert violation is not None
        assert violation.severity.value == "CRITICAL"
        assert "wash trading" in violation.description.lower()

    def test_two_buys_not_flagged(self):
        self.rule.check(self._event("C1", "EURUSD", "BUY"))
        assert self.rule.check(self._event("C1", "EURUSD", "BUY")) is None

    def test_different_clients_not_flagged(self):
        self.rule.check(self._event("C1", "EURUSD", "BUY"))
        assert self.rule.check(self._event("C2", "EURUSD", "SELL")) is None

    def test_different_symbols_not_flagged(self):
        self.rule.check(self._event("C1", "EURUSD", "BUY"))
        assert self.rule.check(self._event("C1", "BTCUSD", "SELL")) is None


class TestRapidFireRule:
    @pytest.mark.parametrize(
        "order_count, max_orders, should_flag",
        [
            (5, 10, False),
            (10, 10, False),
            (11, 10, True),
            (20, 10, True),
        ],
    )
    def test_order_count_threshold(self, order_count, max_orders, should_flag):
        rule = RapidFireRule(
            {"enabled": True, "max_orders": max_orders, "window_seconds": 60}
        )
        event = {"client_id": "C1", "symbol": "EURUSD"}
        result = None
        for _ in range(order_count):
            result = rule.check(event)
        assert (result is not None) == should_flag

    def test_different_clients_tracked_independently(self):
        rule = RapidFireRule({"enabled": True, "max_orders": 3, "window_seconds": 60})
        c1_event = {"client_id": "C1", "symbol": "EURUSD"}
        c2_event = {"client_id": "C2", "symbol": "EURUSD"}
        for _ in range(4):
            rule.check(c1_event)
        assert rule.check(c2_event) is None


class TestVolumeSpikeRule:
    def test_first_events_build_baseline(self):
        rule = VolumeSpikeRule(
            {"enabled": True, "spike_multiplier": 5.0, "baseline_window_seconds": 3600}
        )
        for _ in range(5):
            assert rule.check({"symbol": "EURUSD", "quantity": 100}) is None

    def test_spike_detected_above_multiplier(self):
        rule = VolumeSpikeRule(
            {"enabled": True, "spike_multiplier": 5.0, "baseline_window_seconds": 3600}
        )
        for _ in range(5):
            rule.check({"symbol": "EURUSD", "quantity": 100})
        violation = rule.check({"symbol": "EURUSD", "quantity": 10000})
        assert violation is not None
        assert violation.metadata["multiplier"] > 5.0


class TestRepeatedOrdersRule:
    def test_repeated_identical_orders_flagged(self):
        rule = RepeatedOrdersRule(
            {"enabled": True, "repeat_threshold": 3, "window_seconds": 300}
        )
        event = {
            "client_id": "C1",
            "symbol": "EURUSD",
            "side": "BUY",
            "price": 1.09,
            "quantity": 100,
        }
        rule.check(event)
        rule.check(event)
        violation = rule.check(event)
        assert violation is not None
        assert violation.metadata["repeat_count"] == 3

    def test_different_prices_not_repeated(self):
        rule = RepeatedOrdersRule(
            {"enabled": True, "repeat_threshold": 3, "window_seconds": 300}
        )
        e = {"client_id": "C1", "symbol": "EURUSD", "side": "BUY", "quantity": 100}
        for price in [1.09, 1.10, 1.11]:
            assert rule.check({**e, "price": price}) is None
