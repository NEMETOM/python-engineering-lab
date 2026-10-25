from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from sqlalchemy.exc import OperationalError

from reporting_service import consumer
from reporting_service.consumer import handle, save_with_retry
from reporting_service.enricher import ReportEnricher

NOW = datetime(2026, 10, 25, 12, 0, 0, tzinfo=UTC)


def _make_payload(**overrides):
    defaults = {
        "trade_id": "T1",
        "symbol": "EURUSD",
        "buy_order_id": "B1",
        "sell_order_id": "S1",
        "price": 1.085,
        "quantity": 1000,
        "buy_client_id": "B",
        "sell_client_id": "S",
        "timestamp": "2026-10-25T11:59:59+00:00",
    }
    return {**defaults, **overrides}


def _make_enricher():
    data = {
        "instruments": {
            "EURUSD": {"mifid_in_scope": False, "currency": "USD"},
        }
    }
    return ReportEnricher(data, clock=lambda: NOW)


def _db_down():
    return OperationalError("INSERT", {}, Exception("connection refused"))


class TestHandle:
    def test_valid_trade_is_enriched_and_saved(self):
        repo = MagicMock()
        repo.save.return_value = True
        handle(_make_payload(), _make_enricher(), repo)
        report = repo.save.call_args.args[0]
        assert report.trade_id == "T1"
        assert report.status == "NOT_REPORTABLE"
        assert report.publication_latency_ms == 1000

    def test_outcome_counter_uses_status_or_duplicate(self):
        repo = MagicMock()
        with patch.object(consumer, "regulatory_reports") as counter:
            repo.save.return_value = True
            handle(_make_payload(), _make_enricher(), repo)
            repo.save.return_value = False
            handle(_make_payload(), _make_enricher(), repo)
        labels = [c.kwargs["status"] for c in counter.labels.call_args_list]
        assert labels == ["NOT_REPORTABLE", "DUPLICATE"]

    def test_latency_observed_only_for_newly_inserted_reports(self):
        repo = MagicMock()
        with patch.object(consumer, "regulatory_report_latency_seconds") as hist:
            repo.save.return_value = False
            handle(_make_payload(), _make_enricher(), repo)
            hist.observe.assert_not_called()
            repo.save.return_value = True
            handle(_make_payload(), _make_enricher(), repo)
            hist.observe.assert_called_once_with(1.0)

    def test_malformed_payload_is_logged_and_skipped(self):
        repo = MagicMock()
        payload = _make_payload()
        del payload["price"]
        handle(payload, _make_enricher(), repo)  # must not raise
        repo.save.assert_not_called()

    def test_non_connection_db_error_is_skipped_not_retried(self):
        repo = MagicMock()
        repo.save.side_effect = ValueError("bad data")
        sleep = MagicMock()
        handle(_make_payload(), _make_enricher(), repo, sleep=sleep)
        repo.save.assert_called_once()
        sleep.assert_not_called()


class TestSaveWithRetry:
    def test_retries_until_database_comes_back(self):
        repo = MagicMock()
        repo.save.side_effect = [_db_down(), _db_down(), True]
        sleep = MagicMock()
        assert save_with_retry(repo, MagicMock(), sleep=sleep) is True
        assert [c.args[0] for c in sleep.call_args_list] == [1.0, 2.0]

    def test_backoff_is_capped(self):
        repo = MagicMock()
        repo.save.side_effect = [_db_down()] * 6 + [True]
        sleep = MagicMock()
        save_with_retry(repo, MagicMock(), sleep=sleep, max_backoff=5)
        assert [c.args[0] for c in sleep.call_args_list] == [1, 2, 4, 5, 5, 5]


class TestRun:
    def test_wires_consumer_to_handler(self):
        msg = MagicMock(value=_make_payload())
        with (
            patch.object(consumer, "start_http_server") as metrics,
            patch.object(consumer, "create_consumer", return_value=[msg]) as create,
            patch.object(consumer, "ReportRepository") as repo_cls,
            patch.object(consumer, "handle") as handler,
        ):
            consumer.run()
        metrics.assert_called_once_with(8012)
        create.assert_called_once_with("trades", "reporting-service")
        handler.assert_called_once()
        assert handler.call_args.args[0] == msg.value
        assert handler.call_args.args[2] is repo_cls.return_value

    def test_every_outcome_series_exists_at_zero_before_the_first_report(self):
        # increase() can't see a series that first appears already at 1, so the
        # Grafana dashboard would miss the first report of each outcome.
        from prometheus_client import REGISTRY

        with (
            patch.object(consumer, "start_http_server"),
            patch.object(consumer, "create_consumer", return_value=[]),
            patch.object(consumer, "ReportRepository"),
        ):
            consumer.run()
        for outcome in consumer.OUTCOMES:
            value = REGISTRY.get_sample_value(
                "regulatory_reports_total", {"status": outcome}
            )
            assert value is not None, f"{outcome} series not exported"
