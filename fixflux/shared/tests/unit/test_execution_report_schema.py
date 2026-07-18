from datetime import datetime, timezone

import pytest
from pydantic import ValidationError as PydanticValidationError

from shared.schemas.execution_report_event import ExecutionReportEvent


def _make(**overrides):
    defaults = dict(
        order_id="O1",
        cl_ord_id="O1",
        client_id="CLIENT-A",
        exec_type="0",
        ord_status="0",
        symbol="AAPL",
        side="BUY",
        price=100.0,
        order_qty=10,
        leaves_qty=10,
        cum_qty=0,
    )
    return ExecutionReportEvent(**{**defaults, **overrides})


class TestRequiredFields:
    @pytest.mark.parametrize(
        "field",
        [
            "order_id",
            "cl_ord_id",
            "client_id",
            "exec_type",
            "ord_status",
            "symbol",
            "side",
            "price",
            "order_qty",
            "leaves_qty",
            "cum_qty",
        ],
    )
    def test_missing_required_field_raises(self, field):
        data = dict(
            order_id="O1",
            cl_ord_id="O1",
            client_id="CLIENT-A",
            exec_type="0",
            ord_status="0",
            symbol="AAPL",
            side="BUY",
            price=100.0,
            order_qty=10,
            leaves_qty=10,
            cum_qty=0,
        )
        del data[field]
        with pytest.raises(PydanticValidationError):
            ExecutionReportEvent(**data)


class TestExecTypeValidation:
    def test_new_accepted(self):
        assert _make(exec_type="0").exec_type == "0"

    def test_rejected_accepted(self):
        assert _make(exec_type="8", ord_status="8").exec_type == "8"

    def test_fill_accepted(self):
        assert _make(exec_type="F", ord_status="2").exec_type == "F"

    def test_unknown_exec_type_rejected(self):
        with pytest.raises(PydanticValidationError):
            _make(exec_type="X")

    def test_lowercase_rejected(self):
        with pytest.raises(PydanticValidationError):
            _make(exec_type="f")

    def test_numeric_rejected(self):
        with pytest.raises(PydanticValidationError):
            _make(exec_type=0)


class TestOrdStatusValidation:
    def test_new_accepted(self):
        assert _make(ord_status="0").ord_status == "0"

    def test_filled_accepted(self):
        assert _make(exec_type="F", ord_status="2").ord_status == "2"

    def test_rejected_accepted(self):
        assert _make(exec_type="8", ord_status="8").ord_status == "8"

    def test_unknown_status_rejected(self):
        with pytest.raises(PydanticValidationError):
            _make(ord_status="1")

    def test_empty_string_rejected(self):
        with pytest.raises(PydanticValidationError):
            _make(ord_status="")


class TestSideValidation:
    def test_buy_accepted(self):
        assert _make(side="BUY").side == "BUY"

    def test_sell_accepted(self):
        assert _make(side="SELL").side == "SELL"

    def test_lowercase_buy_rejected(self):
        with pytest.raises(PydanticValidationError):
            _make(side="buy")

    def test_unknown_side_rejected(self):
        with pytest.raises(PydanticValidationError):
            _make(side="SHORT")


class TestOptionalFields:
    def test_last_px_defaults_to_none(self):
        assert _make().last_px is None

    def test_last_qty_defaults_to_none(self):
        assert _make().last_qty is None

    def test_reason_defaults_to_none(self):
        assert _make().reason is None

    def test_last_px_set_for_fill(self):
        event = _make(exec_type="F", ord_status="2", last_px=99.5, last_qty=10)
        assert event.last_px == 99.5

    def test_last_qty_set_for_fill(self):
        event = _make(exec_type="F", ord_status="2", last_px=99.5, last_qty=7)
        assert event.last_qty == 7

    def test_reason_set_for_rejection(self):
        event = _make(exec_type="8", ord_status="8", reason="Notional limit exceeded")
        assert event.reason == "Notional limit exceeded"


class TestDefaults:
    def test_exec_id_auto_generated(self):
        event = _make()
        assert event.exec_id != ""
        assert len(event.exec_id) == 36  # UUID4 format

    def test_exec_id_unique_per_instance(self):
        a = _make()
        b = _make()
        assert a.exec_id != b.exec_id

    def test_timestamp_defaults_to_utc_now(self):
        event = _make()
        assert isinstance(event.timestamp, datetime)
        assert event.timestamp.tzinfo == timezone.utc


class TestSerialization:
    def test_model_dump_json_mode_serializes_datetime(self):
        event = _make()
        data = event.model_dump(mode="json")
        assert isinstance(data["timestamp"], str)

    def test_model_dump_contains_all_fields(self):
        event = _make(
            exec_type="F", ord_status="2", last_px=100.0, last_qty=10, leaves_qty=0,
            cum_qty=10,
        )
        data = event.model_dump(mode="json")
        for key in [
            "exec_id", "order_id", "cl_ord_id", "client_id", "exec_type",
            "ord_status", "symbol", "side", "price", "order_qty",
            "last_px", "last_qty", "leaves_qty", "cum_qty", "reason", "timestamp",
        ]:
            assert key in data

    def test_round_trip_via_model_validate(self):
        original = _make()
        data = original.model_dump(mode="json")
        restored = ExecutionReportEvent.model_validate(data)
        assert restored.order_id == original.order_id
        assert restored.exec_type == original.exec_type
        assert restored.exec_id == original.exec_id
