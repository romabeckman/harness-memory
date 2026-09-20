from unittest.mock import MagicMock
import pytest
from core.infrastructure.telemetry.telemetry_tracer import TelemetryTracer
from core.infrastructure.telemetry.tracer_provider import TelemetryTracerProvider


def test_tracer_provider_returns_telemetry_tracer():
    tracer = TelemetryTracerProvider.get_tracer("test-harness-memory")
    assert isinstance(tracer, TelemetryTracer)


def test_telemetry_tracer_operates_cleanly_when_noop():
    tracer = TelemetryTracer("test-tracer")
    executed = False
    with tracer.start_as_current_span("test-span", attributes={"tool.name": "test", "password": "pass"}) as span:
        executed = True

    assert executed is True
