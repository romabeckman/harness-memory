from unittest.mock import MagicMock
import pytest
from core.domain.platform.schema_incompatible_error import SchemaIncompatibleError
from core.infrastructure.postgres.migrations_status import MigrationStatus
from core.infrastructure.postgres.schema_compatibility_checker import SchemaCompatibilityChecker
from core.infrastructure.postgres.verify_startup_schema import VerifyStartupSchema


def test_check_returns_compatible_when_current_equals_head():
    runtime = MagicMock()
    runtime.status.return_value = MigrationStatus(
        current_revision="0002_security_audit",
        head_revision="0002_security_audit",
    )
    checker = SchemaCompatibilityChecker()
    status = checker.check(runtime)
    assert status.is_compatible() is True
    assert status.current_revision == "0002_security_audit"
    assert status.head_revision == "0002_security_audit"


def test_check_returns_incompatible_when_pending_migrations():
    runtime = MagicMock()
    runtime.status.return_value = MigrationStatus(
        current_revision="0001_initial_foundation",
        head_revision="0002_security_audit",
    )
    checker = SchemaCompatibilityChecker()
    status = checker.check(runtime)
    assert status.is_compatible() is False


def test_verify_startup_schema_raises_schema_incompatible_error():
    runtime = MagicMock()
    runtime.status.return_value = MigrationStatus(
        current_revision="0001",
        head_revision="0002",
    )
    verifier = VerifyStartupSchema()
    with pytest.raises(SchemaIncompatibleError) as exc_info:
        verifier.execute(runtime)

    assert "0001" in str(exc_info.value)
    assert "0002" in str(exc_info.value)
