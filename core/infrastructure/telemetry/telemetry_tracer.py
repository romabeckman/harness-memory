from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from opentelemetry import trace

from .telemetry_span_sanitizer import TelemetrySpanSanitizer


class TelemetryTracer:
    """Delegates to OpenTelemetry Tracer with sanitized attributes and graceful NoOp fallback."""

    def __init__(self, name: str = "harness-memory"):
        self._tracer = trace.get_tracer(name)

    @contextmanager
    def start_as_current_span(
        self, name: str, attributes: dict[str, Any] | None = None
    ) -> Iterator[Any]:
        sanitized = TelemetrySpanSanitizer.sanitize(attributes)
        try:
            with self._tracer.start_as_current_span(name, attributes=sanitized) as span:
                yield span
        except Exception:
            # Propagate underlying application exception raised within the span block
            raise

    def start_span(self, name: str, attributes: dict[str, Any] | None = None) -> Any:
        sanitized = TelemetrySpanSanitizer.sanitize(attributes)
        return self._tracer.start_span(name, attributes=sanitized)
