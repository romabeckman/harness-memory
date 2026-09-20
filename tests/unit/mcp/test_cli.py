from io import StringIO

from core.infrastructure.postgres.migrations import MigrationStatus
from harness_memory_mcp.cli import MigrationCLI


def test_migration_cli_returns_zero_for_upgrade():
    output = StringIO()
    calls = []

    def upgrade():
        calls.append("upgrade")
        return MigrationStatus(current_revision="abc", head_revision="abc")

    cli = MigrationCLI(upgrade=upgrade, status=lambda: None, output=output)

    result = cli.dispatch(["migrate"])

    assert result == 0
    assert calls == ["upgrade"]


def test_migration_cli_status_is_read_only_and_reports_revisions():
    output = StringIO()
    calls = []

    def status():
        calls.append("status")
        return MigrationStatus(current_revision="abc", head_revision="def")

    def upgrade():
        calls.append("upgrade")
        return None

    cli = MigrationCLI(upgrade=upgrade, status=status, output=output)

    result = cli.dispatch(["migrate", "--status"])

    assert result == 0
    assert calls == ["status"]
    assert "abc" in output.getvalue()
    assert "def" in output.getvalue()


def test_migration_cli_hides_credentials_on_failure():
    output = StringIO()

    def fail():
        raise RuntimeError(
            "connection failed for postgresql+psycopg2://secret-user:secret-password@localhost/db"
        )

    cli = MigrationCLI(upgrade=fail, status=fail, output=output)

    result = cli.dispatch(["migrate"])

    assert result != 0
    assert "secret-user" not in output.getvalue()
    assert "secret-password" not in output.getvalue()
