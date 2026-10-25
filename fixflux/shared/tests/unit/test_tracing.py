from unittest.mock import patch

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceFlags

from shared.observability.tracing import extract_ctx, init_tracer, inject_ctx

TRACE_ID = "4bf92f3577b34da6a3ce929d0e0e4736"
SPAN_ID = "00f067aa0ba902b7"


def _make_message(**overrides):
    defaults = {"order_id": "O1", "_trace_id": TRACE_ID, "_span_id": SPAN_ID}
    return {**defaults, **overrides}


def _local_tracer():
    # A private provider: init_tracer's global set_tracer_provider can only
    # take effect once per process, so tests never rely on the global one.
    return TracerProvider().get_tracer("test")


class TestExtractCtx:
    def test_child_span_continues_the_upstream_trace(self):
        # The whole point of propagation: a span started from the extracted
        # context belongs to the producer's trace, parented on its span.
        ctx = extract_ctx(_make_message())
        with _local_tracer().start_as_current_span("consumer", context=ctx) as span:
            assert span.get_span_context().trace_id == int(TRACE_ID, 16)
            assert span.parent.span_id == int(SPAN_ID, 16)
            assert span.parent.is_remote

    @pytest.mark.parametrize("missing", ["_trace_id", "_span_id"])
    def test_message_without_trace_fields_starts_a_new_trace(self, missing):
        message = _make_message()
        del message[missing]
        assert extract_ctx(message) is None

    @pytest.mark.parametrize(
        "trace_id, span_id",
        [
            ("not-hex", SPAN_ID),  # ValueError from int(..., 16)
            (TRACE_ID, 12345),  # TypeError: int() can't parse a non-str in base 16
        ],
    )
    def test_corrupt_trace_fields_are_ignored_not_raised(self, trace_id, span_id):
        # A bad header must never crash the consumer loop that calls this.
        assert extract_ctx(_make_message(_trace_id=trace_id, _span_id=span_id)) is None


class TestInjectCtx:
    def test_no_active_span_leaves_message_untouched(self):
        message = {"order_id": "O1"}
        assert inject_ctx(message) == {"order_id": "O1"}

    def test_ids_keep_leading_zeros_as_fixed_width_hex(self):
        # Deterministic IDs with leading zeros: random IDs rarely start with
        # 0, so a test using them would miss a lost zero-pad ~15 runs in 16.
        span_ctx = SpanContext(
            trace_id=int("00000000000000000000000000abcdef", 16),
            span_id=int(SPAN_ID, 16),  # "00f067aa0ba902b7"
            is_remote=False,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
        )
        with trace.use_span(NonRecordingSpan(span_ctx)):
            message = inject_ctx({"order_id": "O1"})
        assert message["_trace_id"] == "00000000000000000000000000abcdef"
        assert message["_span_id"] == SPAN_ID

    def test_mutates_and_returns_the_same_dict(self):
        message = {"order_id": "O1"}
        with _local_tracer().start_as_current_span("producer"):
            assert inject_ctx(message) is message


class TestRoundTrip:
    def test_inject_then_extract_links_producer_and_consumer_spans(self):
        # Mirrors one Kafka hop: producer injects, JSON crosses the topic,
        # consumer extracts. Breaking either side splits traces in Tempo.
        tracer = _local_tracer()
        with tracer.start_as_current_span("producer") as producer:
            message = inject_ctx({"order_id": "O1"})
        with tracer.start_as_current_span(
            "consumer", context=extract_ctx(message)
        ) as consumer:
            assert (
                consumer.get_span_context().trace_id
                == producer.get_span_context().trace_id
            )
            assert consumer.parent.span_id == producer.get_span_context().span_id


class TestInitTracer:
    def test_without_endpoint_no_exporter_is_configured(self, monkeypatch):
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
        with (
            patch("shared.observability.tracing.trace.set_tracer_provider") as set_p,
            patch("shared.observability.tracing.OTLPSpanExporter") as exporter,
        ):
            init_tracer("svc")
        exporter.assert_not_called()
        set_p.assert_called_once()

    def test_endpoint_gets_the_otlp_traces_path_appended(self, monkeypatch):
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://tempo:4318")
        with (
            patch("shared.observability.tracing.trace.set_tracer_provider"),
            patch("shared.observability.tracing.OTLPSpanExporter") as exporter,
            patch("shared.observability.tracing.BatchSpanProcessor") as processor,
        ):
            init_tracer("svc")
        exporter.assert_called_once_with(endpoint="http://tempo:4318/v1/traces")
        processor.assert_called_once_with(exporter.return_value)

    def test_provider_carries_the_service_name(self, monkeypatch):
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
        with patch("shared.observability.tracing.trace.set_tracer_provider") as set_p:
            init_tracer("risk-service")
        provider = set_p.call_args.args[0]
        assert provider.resource.attributes["service.name"] == "risk-service"

    def test_returns_a_tracer(self, monkeypatch):
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
        with patch("shared.observability.tracing.trace.set_tracer_provider"):
            assert isinstance(init_tracer("svc"), trace.Tracer)
