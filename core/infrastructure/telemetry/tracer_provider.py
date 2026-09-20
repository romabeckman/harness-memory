from .telemetry_tracer import TelemetryTracer


class TelemetryTracerProvider:
    """Factory for TelemetryTracer instances."""

    @staticmethod
    def get_tracer(name: str = "harness-memory") -> TelemetryTracer:
        return TelemetryTracer(name=name)
