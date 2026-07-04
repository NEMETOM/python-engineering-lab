import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceFlags, set_span_in_context


def init_tracer(service_name: str) -> trace.Tracer:
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if endpoint:
        exporter = OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces")
        provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return trace.get_tracer(service_name)


def extract_ctx(event: dict):
    """Return an OTel Context with parent span extracted from a Kafka message dict, or None."""
    trace_id_hex = event.get("_trace_id")
    span_id_hex = event.get("_span_id")
    if not trace_id_hex or not span_id_hex:
        return None
    try:
        span_ctx = SpanContext(
            trace_id=int(trace_id_hex, 16),
            span_id=int(span_id_hex, 16),
            is_remote=True,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
        )
        return set_span_in_context(NonRecordingSpan(span_ctx))
    except (ValueError, TypeError):
        return None


def inject_ctx(event: dict) -> dict:
    """Inject the current active span context into a Kafka message dict (mutates in-place)."""
    span = trace.get_current_span()
    ctx = span.get_span_context()
    if ctx and ctx.is_valid:
        event["_trace_id"] = format(ctx.trace_id, "032x")
        event["_span_id"] = format(ctx.span_id, "016x")
    return event
