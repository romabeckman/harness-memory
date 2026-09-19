from core.infrastructure.postgres.migrations import (
    InspectMigrationStatus,
    MigrationStatus,
    UpgradeDatabase,
)


def test_migration_status_is_current_when_revisions_match():
    status = MigrationStatus(current_revision="abc", head_revision="abc")

    assert status.is_current is True


def test_migration_status_is_pending_when_current_revision_is_missing():
    status = MigrationStatus(current_revision=None, head_revision="abc")

    assert status.is_current is False


def test_upgrade_database_requests_head_revision():
    calls = []

    class Runtime:
        def upgrade(self, revision):
            calls.append(revision)
            return MigrationStatus(current_revision="abc", head_revision="abc")

    result = UpgradeDatabase(Runtime()).execute()

    assert calls == ["head"]
    assert result.is_current is True


def test_inspect_migration_status_does_not_upgrade():
    calls = []

    class Runtime:
        def status(self):
            calls.append("status")
            return MigrationStatus(current_revision="abc", head_revision="def")

        def upgrade(self, revision):
            calls.append(f"upgrade:{revision}")

    result = InspectMigrationStatus(Runtime()).execute()

    assert calls == ["status"]
    assert result.is_current is False
