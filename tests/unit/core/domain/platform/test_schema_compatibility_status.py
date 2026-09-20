import pytest
from core.domain.platform.schema_compatibility_status import SchemaCompatibilityStatus
from core.domain.platform.schema_incompatible_error import SchemaIncompatibleError


def test_schema_compatible_when_current_matches_head():
    status = SchemaCompatibilityStatus(
        current_revision="0002_security_audit",
        head_revision="0002_security_audit",
    )
    assert status.is_compatible() is True


def test_schema_incompatible_when_database_has_no_recorded_revision():
    status = SchemaCompatibilityStatus(
        current_revision=None,
        head_revision="0002_security_audit",
    )
    assert status.is_compatible() is False


def test_schema_incompatible_when_current_differs_from_head():
    status = SchemaCompatibilityStatus(
        current_revision="0001_initial_foundation",
        head_revision="0002_security_audit",
    )
    assert status.is_compatible() is False


def test_schema_incompatible_error_contains_sanitized_message():
    error = SchemaIncompatibleError(
        current_revision="0001",
        head_revision="0002",
    )
    error_message = str(error)
    assert "0001" in error_message
    assert "0002" in error_message
    assert "postgres" not in error_message.lower()
    assert "password" not in error_message.lower()


def test_schema_status_rejects_empty_head_revision():
    with pytest.raises(ValueError):
        SchemaCompatibilityStatus(current_revision=None, head_revision=" ")


def test_schema_incompatible_error_redacts_connection_parameters():
    error = SchemaIncompatibleError(
        current_revision="0001",
        head_revision="0002",
        message="migration failed for postgresql://db-user:db-password@db.example/app",
    )

    assert "db-password" not in str(error)
    assert "db-user:db-password" not in str(error)
    assert "postgresql://" not in str(error)

    error_with_key = SchemaIncompatibleError(
        current_revision="0001",
        head_revision="0002",
        message="password=db-password DATABASE_URL=postgresql://db/app",
    )
    assert "password" not in str(error_with_key).lower()
    assert "database_url" not in str(error_with_key).lower()
