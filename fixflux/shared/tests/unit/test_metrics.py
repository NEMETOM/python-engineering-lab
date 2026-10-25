"""Contract tests for the shared Prometheus registry.

Alert rules (prometheus_alerts.yml), SLO burn-rate rules (prometheus_slo_rules.yml)
and Grafana dashboards query these metrics by exact name, label and bucket
boundary. Renaming one, or dropping a bucket the SLO math depends on, breaks
monitoring silently, with no error anywhere in the services themselves.
"""

import pytest

from shared.observability import metrics


def _make_expected_metrics():
    # (attribute, exposed name, labels) - names as Prometheus queries them
    return [
        ("fix_messages_received", "fix_messages_received", ("msg_type",)),
        ("trades_executed", "trades_executed", ("symbol",)),
        ("order_matching_latency", "order_matching_latency_seconds", ()),
        ("orders_in_book", "orders_in_book", ("side", "symbol")),
        ("orders_processed", "orders_processed", ("status",)),
        ("violations_detected", "violations_detected", ("rule", "severity")),
        ("trades_stored", "trades_stored", ("symbol",)),
        ("api_requests", "api_requests", ("endpoint", "method", "status_code")),
        ("api_request_latency", "api_request_latency_seconds", ("endpoint",)),
        ("regulatory_reports", "regulatory_reports", ("status",)),
        (
            "regulatory_report_latency_seconds",
            "regulatory_report_latency_seconds",
            (),
        ),
    ]


class TestMetricNamesAndLabels:
    @pytest.mark.parametrize("attr, name, labels", _make_expected_metrics())
    def test_queried_metric_keeps_its_name_and_labels(self, attr, name, labels):
        metric = getattr(metrics, attr)
        # prometheus_client stores counters without the _total suffix it adds
        # on exposition, so "trades_executed" is exposed as trades_executed_total.
        assert metric._name == name
        assert metric._labelnames == labels


class TestBucketBoundaries:
    def test_api_latency_has_a_bucket_at_the_200ms_slo_threshold(self):
        # SLO.md: burn-rate math needs a real le="0.2" bucket, not an
        # interpolation across a bucket gap.
        assert 0.2 in metrics.api_request_latency._kwargs["buckets"]

    def test_regulatory_latency_has_a_bucket_at_the_one_minute_deadline(self):
        # RTS 1 Art. 14(1)(a): within one minute - breaches must be countable
        # exactly from the le="60.0" bucket.
        assert 60 in metrics.regulatory_report_latency_seconds._upper_bounds

    def test_matching_latency_buckets_contain_the_10ms_alert_threshold(self):
        # MatchingEngineP99LatencyHigh fires at > 0.01s; the threshold must sit
        # inside the bucket range or histogram_quantile can't resolve it.
        bounds = metrics.order_matching_latency._upper_bounds
        assert 0.01 in bounds and max(b for b in bounds if b != float("inf")) > 0.01
