import json
from datetime import datetime
from importlib import import_module
from uuid import uuid4

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_migration_projects_payload_fields_before_dropping_duplicate_column(monkeypatch):
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    metadata = sa.MetaData()
    projects = sa.Table(
        "projects",
        metadata,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("key", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255)),
    )
    snapshots = sa.Table(
        "snapshots",
        metadata,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("revision", sa.Integer, nullable=False),
        sa.Column("schema_version", sa.String(64), nullable=False),
        sa.Column("payload_hash", sa.String(128), nullable=False),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column("metadata", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "substr(CAST(payload AS TEXT), 1, 1) = '{'", name="ck_snapshots_payload_object"
        ),
    )
    entities = sa.Table(
        "entities",
        metadata,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("snapshot_id", sa.String(36), nullable=False),
        sa.Column("entity_key", sa.String(255), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255)),
        sa.Column("metadata", sa.JSON, nullable=False),
    )
    relations = sa.Table(
        "relations",
        metadata,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("snapshot_id", sa.String(36), nullable=False),
        sa.Column("source_entity_id", sa.String(36), nullable=False),
        sa.Column("target_entity_id", sa.String(36), nullable=False),
        sa.Column("relation_type", sa.String(64), nullable=False),
        sa.Column("provenance_kind", sa.String(32), nullable=False),
        sa.Column("metadata", sa.JSON, nullable=False),
    )
    evidence = sa.Table(
        "evidence",
        metadata,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("snapshot_id", sa.String(36), nullable=False),
        sa.Column("relation_id", sa.String(36)),
        sa.Column("source", sa.String(1024), nullable=False),
        sa.Column("excerpt", sa.String(4096)),
        sa.Column("metadata", sa.JSON, nullable=False),
    )
    metadata.create_all(engine)

    project_id, snapshot_id = str(uuid4()), str(uuid4())
    entity_ids = {"service": str(uuid4()), "api": str(uuid4())}
    relation_id, evidence_id = str(uuid4()), str(uuid4())
    payload = {
        "schema_version": "1.0",
        "project": {"key": "payments", "name": "Payments", "metadata": {"owner": "team-a"}},
        "revision": 3,
        "generated_at": "2026-09-17T12:00:00.123456Z",
        "entities": [
            {
                "key": "service",
                "type": "service",
                "name": "Payments",
                "canonical_key": "shared:payments",
                "metadata": {"content": "x" * 5000},
            },
            {"key": "api", "type": "api", "name": None, "canonical_key": None, "metadata": {}},
        ],
        "relations": [
            {
                "ref": "service-api",
                "source_entity_key": "service",
                "type": "provides",
                "target_entity_key": "api",
                "provenance": "declared",
                "metadata": {"priority": 1},
            }
        ],
        "evidence": [
            {
                "source": "catalog.yaml",
                "excerpt": "Payments provides an API.",
                "relation_ref": "service-api",
                "metadata": {"line": 12},
            }
        ],
    }
    with engine.begin() as connection:
        connection.execute(
            projects.insert(), {"id": project_id, "key": "payments", "name": "Payments"}
        )
        connection.execute(
            snapshots.insert(),
            {
                "id": snapshot_id,
                "project_id": project_id,
                "revision": 3,
                "schema_version": "1.0",
                "payload_hash": "a" * 64,
                "payload": payload,
                "metadata": {"owner": "team-a"},
                "created_at": datetime(2026, 9, 17, 12),
            },
        )
        connection.execute(
            entities.insert(),
            [
                {
                    "id": entity_ids["service"],
                    "snapshot_id": snapshot_id,
                    "entity_key": "service",
                    "entity_type": "service",
                    "name": "Payments",
                    "metadata": {"content": "x" * 5000},
                },
                {
                    "id": entity_ids["api"],
                    "snapshot_id": snapshot_id,
                    "entity_key": "api",
                    "entity_type": "api",
                    "name": None,
                    "metadata": {},
                },
            ],
        )
        connection.execute(
            relations.insert(),
            {
                "id": relation_id,
                "snapshot_id": snapshot_id,
                "source_entity_id": entity_ids["service"],
                "target_entity_id": entity_ids["api"],
                "relation_type": "provides",
                "provenance_kind": "declared",
                "metadata": {"priority": 1},
            },
        )
        connection.execute(
            evidence.insert(),
            {
                "id": evidence_id,
                "snapshot_id": snapshot_id,
                "relation_id": relation_id,
                "source": "catalog.yaml",
                "excerpt": "Payments provides an API.",
                "metadata": {"line": 12},
            },
        )

        migration = import_module("migrations.versions.011_snapshot_payload_removal")
        monkeypatch.setattr(migration, "op", Operations(MigrationContext.configure(connection)))
        migration.upgrade()

        columns = {column["name"] for column in sa.inspect(connection).get_columns("snapshots")}
        assert "payload" not in columns
        snapshot_row = connection.execute(
            sa.text("SELECT project_key, project_name, generated_at FROM snapshots WHERE id=:id"),
            {"id": snapshot_id},
        ).one()
        assert snapshot_row.project_key == "payments"
        assert snapshot_row.project_name == "Payments"
        assert "2026-09-17 12:00:00.123456" in str(snapshot_row.generated_at)
        assert connection.execute(
            sa.text("SELECT canonical_key, graph_position FROM entities WHERE id=:id"),
            {"id": entity_ids["service"]},
        ).one() == ("shared:payments", 0)
        assert connection.execute(
            sa.text("SELECT relation_ref, graph_position FROM relations WHERE id=:id"),
            {"id": relation_id},
        ).one() == ("service-api", 0)
        assert (
            connection.execute(
                sa.text("SELECT graph_position FROM evidence WHERE id=:id"),
                {"id": evidence_id},
            ).scalar_one()
            == 0
        )

        migration.downgrade()
        restored = connection.execute(
            sa.text("SELECT payload FROM snapshots WHERE id=:id"), {"id": snapshot_id}
        ).scalar_one()
        if isinstance(restored, str):
            restored = json.loads(restored)
        assert restored["project"] == payload["project"]
        assert restored["generated_at"] == payload["generated_at"]
        assert restored["entities"] == payload["entities"]
        assert restored["relations"] == payload["relations"]
        assert restored["evidence"] == payload["evidence"]
        assert {column["name"] for column in sa.inspect(connection).get_columns("snapshots")} >= {
            "payload"
        }

    engine.dispose()
