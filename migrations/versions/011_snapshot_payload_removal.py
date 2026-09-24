"""Backfill normalized snapshot projections, then remove the duplicate payload column."""

import json
from collections import defaultdict
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def _json_object() -> sa.JSON:
    return sa.JSON().with_variant(JSONB(), "postgresql")


def _value(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _json_key(value) -> str:
    return json.dumps(_value(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _generated_at(value) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _relation_signature(source, target, relation_type, provenance, metadata, evidence_profile):
    return (
        source,
        target,
        relation_type,
        provenance,
        _json_key(metadata or {}),
        tuple(sorted(evidence_profile)),
    )


def _fail(snapshot_id, detail):
    raise RuntimeError(
        f"Cannot remove snapshots.payload for snapshot {snapshot_id}: {detail}. "
        "Repair the normalized snapshot rows before retrying the migration."
    )


def _backfill_snapshot(connection, snapshot):
    snapshot_id = snapshot["id"]
    payload = _value(snapshot["payload"])
    if not isinstance(payload, dict):
        _fail(snapshot_id, "payload is not a JSON object")
    project_payload = payload.get("project") or {}
    project = (
        connection.execute(
            sa.text("SELECT key, name FROM projects WHERE CAST(id AS TEXT)=:id"),
            {"id": str(snapshot["project_id"])},
        )
        .mappings()
        .first()
    )
    project_key = project_payload.get("key") or (project["key"] if project else None)
    project_name = (
        project_payload.get("name")
        if "name" in project_payload
        else (project["name"] if project else None)
    )
    if not project_key:
        _fail(snapshot_id, "project key is missing")
    generated_at = payload.get("generated_at")
    if generated_at is None:
        _fail(snapshot_id, "generated_at is missing")
    connection.execute(
        sa.text(
            "UPDATE snapshots SET project_key=:project_key, project_name=:project_name, "
            "generated_at=:generated_at WHERE CAST(id AS TEXT)=:id"
        ),
        {
            "id": str(snapshot_id),
            "project_key": project_key,
            "project_name": project_name,
            "generated_at": _generated_at(generated_at),
        },
    )

    entity_payload = payload.get("entities") or []
    entity_rows = (
        connection.execute(
            sa.text(
                "SELECT id, entity_key, entity_type, name, metadata FROM entities "
                "WHERE CAST(snapshot_id AS TEXT)=:snapshot_id"
            ),
            {"snapshot_id": str(snapshot_id)},
        )
        .mappings()
        .all()
    )
    entities_by_key = {row["entity_key"]: row for row in entity_rows}
    if len(entity_payload) != len(entity_rows) or len(entities_by_key) != len(entity_rows):
        _fail(snapshot_id, "entity row count or keys do not match payload")
    entity_key_by_id = {}
    for position, item in enumerate(entity_payload):
        row = entities_by_key.get(item.get("key"))
        if row is None:
            _fail(snapshot_id, f"entity {item.get('key')!r} is missing")
        if (
            row["entity_type"] != item.get("type")
            or row["name"] != item.get("name")
            or _json_key(row["metadata"] or {}) != _json_key(item.get("metadata") or {})
        ):
            _fail(snapshot_id, f"entity {item.get('key')!r} differs from payload")
        entity_key_by_id[str(row["id"])] = row["entity_key"]
        connection.execute(
            sa.text(
                "UPDATE entities SET canonical_key=:canonical_key, graph_position=:position "
                "WHERE CAST(id AS TEXT)=:id"
            ),
            {
                "id": str(row["id"]),
                "canonical_key": item.get("canonical_key"),
                "position": position,
            },
        )

    evidence_payload = payload.get("evidence") or []
    evidence_rows = (
        connection.execute(
            sa.text(
                "SELECT id, relation_id, source, excerpt, metadata FROM evidence "
                "WHERE CAST(snapshot_id AS TEXT)=:snapshot_id"
            ),
            {"snapshot_id": str(snapshot_id)},
        )
        .mappings()
        .all()
    )
    if len(evidence_payload) != len(evidence_rows):
        _fail(snapshot_id, "evidence row count does not match payload")
    expected_evidence_by_ref = defaultdict(list)
    for item in evidence_payload:
        expected_evidence_by_ref[item.get("relation_ref")].append(
            (item.get("source"), item.get("excerpt"), _json_key(item.get("metadata") or {}))
        )
    actual_evidence_by_relation = defaultdict(list)
    for row in evidence_rows:
        if row["relation_id"] is not None:
            actual_evidence_by_relation[str(row["relation_id"])].append(
                (row["source"], row["excerpt"], _json_key(row["metadata"] or {}))
            )

    relation_payload = payload.get("relations") or []
    relation_rows = (
        connection.execute(
            sa.text(
                "SELECT id, source_entity_id, target_entity_id, "
                "relation_type, provenance_kind, metadata "
                "FROM relations WHERE CAST(snapshot_id AS TEXT)=:snapshot_id"
            ),
            {"snapshot_id": str(snapshot_id)},
        )
        .mappings()
        .all()
    )
    expected_relations = defaultdict(list)
    for position, item in enumerate(relation_payload):
        signature = _relation_signature(
            item.get("source_entity_key"),
            item.get("target_entity_key"),
            item.get("type"),
            item.get("provenance"),
            item.get("metadata") or {},
            expected_evidence_by_ref.get(item.get("ref"), []),
        )
        expected_relations[signature].append((position, item))
    actual_relations = defaultdict(list)
    for row in relation_rows:
        source_key = entity_key_by_id.get(str(row["source_entity_id"]))
        target_key = entity_key_by_id.get(str(row["target_entity_id"]))
        if source_key is None or target_key is None:
            _fail(snapshot_id, f"relation {row['id']} has an unresolved endpoint")
        signature = _relation_signature(
            source_key,
            target_key,
            row["relation_type"],
            row["provenance_kind"],
            row["metadata"] or {},
            actual_evidence_by_relation.get(str(row["id"]), []),
        )
        actual_relations[signature].append(row)
    if set(expected_relations) != set(actual_relations):
        _fail(snapshot_id, "relation rows or evidence links do not match payload")
    relation_ref_by_id = {}
    for signature, expected in expected_relations.items():
        actual = sorted(actual_relations[signature], key=lambda row: str(row["id"]))
        if len(expected) != len(actual):
            _fail(snapshot_id, "relation row count does not match payload")
        for (position, item), row in zip(expected, actual):
            relation_ref_by_id[str(row["id"])] = item.get("ref")
            connection.execute(
                sa.text(
                    "UPDATE relations SET relation_ref=:relation_ref, graph_position=:position "
                    "WHERE CAST(id AS TEXT)=:id"
                ),
                {"id": str(row["id"]), "relation_ref": item.get("ref"), "position": position},
            )

    expected_evidence = defaultdict(list)
    for position, item in enumerate(evidence_payload):
        signature = (
            item.get("source"),
            item.get("excerpt"),
            item.get("relation_ref"),
            _json_key(item.get("metadata") or {}),
        )
        expected_evidence[signature].append(position)
    actual_evidence = defaultdict(list)
    for row in evidence_rows:
        relation_ref = (
            relation_ref_by_id.get(str(row["relation_id"]))
            if row["relation_id"] is not None
            else None
        )
        signature = (
            row["source"],
            row["excerpt"],
            relation_ref,
            _json_key(row["metadata"] or {}),
        )
        actual_evidence[signature].append(row)
    if set(expected_evidence) != set(actual_evidence):
        _fail(snapshot_id, "evidence row content or relation links do not match payload")
    for signature, positions in expected_evidence.items():
        actual = sorted(actual_evidence[signature], key=lambda row: str(row["id"]))
        if len(positions) != len(actual):
            _fail(snapshot_id, "evidence row count does not match payload")
        for position, row in zip(positions, actual):
            connection.execute(
                sa.text("UPDATE evidence SET graph_position=:position WHERE CAST(id AS TEXT)=:id"),
                {"id": str(row["id"]), "position": position},
            )


def upgrade() -> None:
    connection = op.get_bind()
    op.add_column("snapshots", sa.Column("project_key", sa.String(255), nullable=True))
    op.add_column("snapshots", sa.Column("project_name", sa.String(255), nullable=True))
    op.add_column("snapshots", sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("entities", sa.Column("canonical_key", sa.String(255), nullable=True))
    op.add_column("entities", sa.Column("graph_position", sa.Integer(), nullable=True))
    op.add_column("relations", sa.Column("relation_ref", sa.String(255), nullable=True))
    op.add_column("relations", sa.Column("graph_position", sa.Integer(), nullable=True))
    op.add_column("evidence", sa.Column("graph_position", sa.Integer(), nullable=True))

    snapshots = (
        connection.execute(sa.text("SELECT id, project_id, payload FROM snapshots ORDER BY id"))
        .mappings()
        .all()
    )
    for snapshot in snapshots:
        _backfill_snapshot(connection, snapshot)

    snapshot_checks = {
        constraint["name"]
        for constraint in sa.inspect(connection).get_check_constraints("snapshots")
    }
    with op.batch_alter_table("snapshots") as batch_op:
        batch_op.alter_column("project_key", existing_type=sa.String(255), nullable=False)
        batch_op.alter_column(
            "generated_at", existing_type=sa.DateTime(timezone=True), nullable=False
        )
        if "ck_snapshots_payload_object" in snapshot_checks:
            batch_op.drop_constraint("ck_snapshots_payload_object", type_="check")
        batch_op.drop_column("payload")
    with op.batch_alter_table("entities") as batch_op:
        batch_op.alter_column("graph_position", existing_type=sa.Integer(), nullable=False)
    with op.batch_alter_table("relations") as batch_op:
        batch_op.alter_column("relation_ref", existing_type=sa.String(255), nullable=False)
        batch_op.alter_column("graph_position", existing_type=sa.Integer(), nullable=False)
    with op.batch_alter_table("evidence") as batch_op:
        batch_op.alter_column("graph_position", existing_type=sa.Integer(), nullable=False)


def _payload_from_rows(connection, snapshot):
    snapshot_id = str(snapshot["id"])
    entities = (
        connection.execute(
            sa.text(
                "SELECT id, entity_key, entity_type, name, canonical_key, graph_position, metadata "
                "FROM entities WHERE CAST(snapshot_id AS TEXT)=:snapshot_id ORDER BY graph_position"
            ),
            {"snapshot_id": snapshot_id},
        )
        .mappings()
        .all()
    )
    entity_keys = {str(row["id"]): row["entity_key"] for row in entities}
    relations = (
        connection.execute(
            sa.text(
                "SELECT id, source_entity_id, target_entity_id, relation_type, provenance_kind, "
                "relation_ref, graph_position, metadata FROM relations "
                "WHERE CAST(snapshot_id AS TEXT)=:snapshot_id ORDER BY graph_position"
            ),
            {"snapshot_id": snapshot_id},
        )
        .mappings()
        .all()
    )
    relation_refs = {str(row["id"]): row["relation_ref"] for row in relations}
    evidence = (
        connection.execute(
            sa.text(
                "SELECT relation_id, source, excerpt, graph_position, metadata FROM evidence "
                "WHERE CAST(snapshot_id AS TEXT)=:snapshot_id ORDER BY graph_position"
            ),
            {"snapshot_id": snapshot_id},
        )
        .mappings()
        .all()
    )
    generated_at = _generated_at(snapshot["generated_at"])
    return {
        "schema_version": snapshot["schema_version"],
        "project": {
            "key": snapshot["project_key"],
            "name": snapshot["project_name"],
            "metadata": _value(snapshot["metadata"]) or {},
        },
        "revision": snapshot["revision"],
        "generated_at": generated_at.isoformat(timespec="microseconds").replace("+00:00", "Z"),
        "entities": [
            {
                "key": row["entity_key"],
                "type": row["entity_type"],
                "name": row["name"],
                "canonical_key": row["canonical_key"],
                "metadata": _value(row["metadata"]) or {},
            }
            for row in entities
        ],
        "relations": [
            {
                "ref": row["relation_ref"],
                "source_entity_key": entity_keys[str(row["source_entity_id"])],
                "type": row["relation_type"],
                "target_entity_key": entity_keys[str(row["target_entity_id"])],
                "provenance": row["provenance_kind"],
                "metadata": _value(row["metadata"]) or {},
            }
            for row in relations
        ],
        "evidence": [
            {
                "source": row["source"],
                "excerpt": row["excerpt"],
                "relation_ref": relation_refs.get(str(row["relation_id"]))
                if row["relation_id"] is not None
                else None,
                "metadata": _value(row["metadata"]) or {},
            }
            for row in evidence
        ],
    }


def downgrade() -> None:
    connection = op.get_bind()
    op.add_column("snapshots", sa.Column("payload", _json_object(), nullable=True))
    snapshots = (
        connection.execute(
            sa.text(
                "SELECT id, revision, schema_version, metadata, project_key, "
                "project_name, generated_at "
                "FROM snapshots ORDER BY id"
            )
        )
        .mappings()
        .all()
    )
    update_payload = sa.text(
        "UPDATE snapshots SET payload=:payload WHERE CAST(id AS TEXT)=:id"
    ).bindparams(sa.bindparam("payload", type_=_json_object()))
    for snapshot in snapshots:
        connection.execute(
            update_payload,
            {"id": str(snapshot["id"]), "payload": _payload_from_rows(connection, snapshot)},
        )
    with op.batch_alter_table("snapshots") as batch_op:
        batch_op.alter_column("payload", existing_type=_json_object(), nullable=False)
        batch_op.create_check_constraint(
            "ck_snapshots_payload_object", "substr(CAST(payload AS TEXT), 1, 1) = '{'"
        )
    op.drop_column("evidence", "graph_position")
    op.drop_column("relations", "graph_position")
    op.drop_column("relations", "relation_ref")
    op.drop_column("entities", "graph_position")
    op.drop_column("entities", "canonical_key")
    op.drop_column("snapshots", "generated_at")
    op.drop_column("snapshots", "project_name")
    op.drop_column("snapshots", "project_key")
