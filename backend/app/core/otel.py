import logging

from opentelemetry import trace

logger = logging.getLogger(__name__)


def setup_telemetry(service_name: str) -> None:
    """Configure OTLP export when OTEL_EXPORTER_OTLP_ENDPOINT is set; otherwise keep API defaults (noop)."""
    from app.core.config import settings

    endpoint = (settings.otel_exporter_otlp_endpoint or "").strip()
    if not endpoint:
        return

    try:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        logger.warning("OpenTelemetry SDK packages missing; tracing export disabled")
        return

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    logger.info("OpenTelemetry tracing enabled for %s → %s", service_name, endpoint)


def get_tracer(name: str = "p2dp"):
    return trace.get_tracer(name)
