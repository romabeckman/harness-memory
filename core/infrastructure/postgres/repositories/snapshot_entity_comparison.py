from sqlalchemy import Text, and_, case, cast, func, literal, or_, select, union_all
from sqlalchemy.orm import aliased

from core.infrastructure.postgres.models.entity import Entity


def snapshot_entity_comparison(pairs, tenant_id: str | None, query: str | None = None):
    """Compare complete snapshot pairs by entity key, retaining both occurrences."""
    after = aliased(Entity, name="comparison_after")
    before = aliased(Entity, name="comparison_before")
    same_key = and_(
        after.entity_key == before.entity_key,
        after.tenant_id == before.tenant_id,
        after.project_id == before.project_id,
    )
    changed = or_(
        after.entity_type != before.entity_type,
        after.name.is_distinct_from(before.name),
        after.metadata_json != before.metadata_json,
    )

    def columns(status):
        return (
            pairs.c.after_snapshot_id.label("snapshot_id"),
            pairs.c.before_snapshot_id,
            func.coalesce(after.entity_key, before.entity_key).label("entity_key"),
            status.label("status"),
            func.coalesce(before.identity_id, before.id).label("before_entity_id"),
            before.id.label("before_occurrence_id"),
            func.coalesce(after.identity_id, after.id).label("after_entity_id"),
            after.id.label("after_occurrence_id"),
        )

    after_rows = (
        select(
            *columns(case((before.id.is_(None), "added"), (changed, "modified"), else_="unchanged"))
        )
        .select_from(pairs)
        .join(after, after.snapshot_id == pairs.c.after_snapshot_id)
        .outerjoin(before, and_(same_key, before.snapshot_id == pairs.c.before_snapshot_id))
    )
    before_only = (
        select(*columns(literal("removed")))
        .select_from(pairs)
        .join(before, before.snapshot_id == pairs.c.before_snapshot_id)
        .outerjoin(after, and_(same_key, after.snapshot_id == pairs.c.after_snapshot_id))
        .where(after.id.is_(None))
    )
    if tenant_id is not None:
        after_rows = after_rows.where(after.tenant_id == tenant_id)
        before_only = before_only.where(before.tenant_id == tenant_id)
    if query is not None:
        escaped = query.lower().replace("!", "!!").replace("%", "!%").replace("_", "!_")
        pattern = f"%{escaped}%"
        matches = or_(
            *(
                func.lower(value).like(pattern, escape="!")
                for entity in (before, after)
                for value in (entity.entity_key, entity.name, cast(entity.metadata_json, Text))
            )
        )
        after_rows = after_rows.where(matches)
        before_only = before_only.where(matches)
    return union_all(after_rows, before_only).subquery()
