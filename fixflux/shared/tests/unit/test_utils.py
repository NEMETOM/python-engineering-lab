from datetime import datetime, timezone

from shared.utils.time import to_iso, utc_now


class TestUtcNow:
    def test_returns_datetime_instance(self):
        assert isinstance(utc_now(), datetime)

    def test_is_timezone_aware(self):
        assert utc_now().tzinfo is not None

    def test_timezone_is_utc(self):
        assert utc_now().tzinfo == timezone.utc

    def test_successive_calls_advance_in_time(self):
        t1 = utc_now()
        t2 = utc_now()
        assert t2 >= t1


class TestToIso:
    def test_returns_string(self):
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        assert isinstance(to_iso(dt), str)

    def test_utc_datetime_iso_format(self):
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        assert to_iso(dt) == "2024-01-15T10:30:00+00:00"

    def test_another_utc_datetime(self):
        dt = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        assert to_iso(dt) == "2024-06-01T12:00:00+00:00"

    def test_result_is_parseable_back_to_datetime(self):
        dt = datetime(2024, 3, 20, 8, 0, 0, tzinfo=timezone.utc)
        assert datetime.fromisoformat(to_iso(dt)) == dt
