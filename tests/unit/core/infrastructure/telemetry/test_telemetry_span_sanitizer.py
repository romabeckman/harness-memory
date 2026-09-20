import pytest
from core.infrastructure.telemetry.telemetry_span_sanitizer import TelemetrySpanSanitizer


def test_preserve_safe_attributes():
    attributes = {
        "tool.name": "search_entities",
        "tenant.id": "tenant-123",
        "project.key": "proj-abc",
        "duration_ms": 42.5,
    }
    sanitized = TelemetrySpanSanitizer.sanitize(attributes)
    assert sanitized == {
        "tool.name": "search_entities",
        "tenant.id": "tenant-123",
        "project.key": "proj-abc",
        "duration_ms": 42.5,
    }


def test_strip_sensitive_fields():
    attributes = {
        "tool.name": "search_entities",
        "authorization": "Bearer secret-token",
        "token": "sensitive-jwt-token",
        "password": "super-secret-password",
        "payload": '{"key": "value"}',
        "database_url": "postgresql://user:pass@localhost:5432/db",
    }
    sanitized = TelemetrySpanSanitizer.sanitize(attributes)
    assert sanitized == {"tool.name": "search_entities"}
    for sensitive_key in ("authorization", "token", "password", "payload", "database_url"):
        assert sensitive_key not in sanitized


def test_strip_sensitive_fields_when_names_are_qualified():
    sanitized = TelemetrySpanSanitizer.sanitize(
        {
            "request.payload": "entity data",
            "jwt.claims": "subject and scopes",
            "authorization.header": "Bearer token",
            "tenant.id": "tenant-123",
        }
    )

    assert sanitized == {"tenant.id": "tenant-123"}


def test_truncate_oversized_string_attributes():
    long_string = "a" * 300
    attributes = {
        "description": long_string,
    }
    sanitized = TelemetrySpanSanitizer.sanitize(attributes)
    assert len(sanitized["description"]) <= 256
    assert sanitized["description"].endswith("...")
