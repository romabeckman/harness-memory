from collections.abc import Callable
from uuid import UUID

from sqlalchemy import Uuid, func, literal, select, type_coerce
from sqlalchemy.orm import Session, sessionmaker

from core.application.environment_context.use_cases.get_history.inbound import GetHistoryInput
from core.infrastructure.postgres.models.environment import Environment
from core.infrastructure.postgres.models.knowledge_publication import KnowledgePublication
from core.infrastructure.postgres.models.project import Project
from core.infrastructure.postgres.models.snapshot import Snapshot
from core.infrastructure.postgres.repositories.snapshot_entity_comparison import (
    snapshot_entity_comparison,
)


class PostgresEnvironmentHistoryRepository:
    def __init__(self, session_factory: Callable[[], Session] | None = None, *, engine=None):
        if session_factory is None and engine is not None:
            session_factory = sessionmaker(bind=engine, expire_on_commit=False)
        if session_factory is None:
            raise ValueError("session_factory or engine is required")
        self._session_factory = session_factory

    def get_history(self, request: GetHistoryInput) -> dict:
        with self._session_factory() as session:
            environment_query = (
                select(Environment)
                .join(
                    Project,
                    (Project.id == Environment.project_id)
                    & (Project.tenant_id == Environment.tenant_id),
                )
                .where(Project.key == request.project_key, Environment.name == request.environment)
            )
            if request.tenant_id is not None:
                environment_query = environment_query.where(
                    Environment.tenant_id == request.tenant_id
                )
            environments = session.scalars(environment_query.limit(2)).all()
            if not environments:
                raise LookupError("environment not found")
            if len(environments) != 1:
                raise ValueError("environment matches multiple tenants; provide tenant_id")
            environment = environments[0]
            scope = (
                Snapshot.tenant_id == environment.tenant_id,
                Snapshot.project_id == environment.project_id,
                Snapshot.environment_id == environment.id,
            )
            snapshots = (
                select(Snapshot, KnowledgePublication.version)
                .outerjoin(
                    KnowledgePublication,
                    (KnowledgePublication.id == Snapshot.publication_id)
                    & (KnowledgePublication.tenant_id == Snapshot.tenant_id),
                )
                .where(*scope)
                .order_by(Snapshot.revision.desc(), Snapshot.id.desc())
            )
            base = {
                "project_key": request.project_key,
                "environment": environment.name,
                "current_snapshot_id": (
                    str(environment.current_snapshot_id)
                    if environment.current_snapshot_id
                    else None
                ),
            }
            if request.snapshot_id is None:
                matching = select(Snapshot.id).where(*scope)
                if request.query is not None:
                    pairs = (
                        select(
                            Snapshot.id.label("after_snapshot_id"),
                            type_coerce(
                                func.lag(Snapshot.id).over(order_by=Snapshot.revision),
                                Snapshot.id.type,
                            ).label("before_snapshot_id"),
                        )
                        .where(*scope)
                        .subquery()
                    )
                    comparisons = snapshot_entity_comparison(
                        pairs, str(environment.tenant_id), request.query
                    )
                    matched_ids = select(comparisons.c.snapshot_id).where(
                        comparisons.c.status != "unchanged"
                    )
                    matching = matching.where(Snapshot.id.in_(matched_ids))
                    snapshots = snapshots.where(Snapshot.id.in_(matched_ids))
                total = session.scalar(select(func.count()).select_from(matching.subquery()))
                rows = session.execute(
                    snapshots.limit(request.limit + 1).offset(request.offset)
                ).all()
                return {
                    **base,
                    "snapshots": [
                        self._snapshot(snapshot, version, environment.current_snapshot_id)
                        for snapshot, version in rows[: request.limit]
                    ],
                    "limit": request.limit,
                    "offset": request.offset,
                    "has_more": len(rows) > request.limit,
                    "total_snapshots": total,
                }
            selected_row = session.execute(
                snapshots.where(Snapshot.id == request.snapshot_id)
            ).one_or_none()
            if selected_row is None:
                raise LookupError("snapshot not found in environment")
            selected, selected_version = selected_row
            previous_row = session.execute(
                snapshots.where(Snapshot.revision < selected.revision).limit(1)
            ).one_or_none()
            selected_data = self._snapshot(
                selected, selected_version, environment.current_snapshot_id
            )
            previous_data = (
                self._snapshot(previous_row[0], previous_row[1], environment.current_snapshot_id)
                if previous_row
                else None
            )
            selected_pairs = select(
                literal(selected.id, type_=Uuid).label("after_snapshot_id"),
                literal(previous_row[0].id if previous_row else None, type_=Uuid).label(
                    "before_snapshot_id"
                ),
            ).subquery()
            comparisons = snapshot_entity_comparison(
                selected_pairs, str(environment.tenant_id), request.query
            )
            counts = dict(
                session.execute(
                    select(comparisons.c.status, func.count())
                    .where(comparisons.c.status != "unchanged")
                    .group_by(comparisons.c.status)
                ).all()
            )
            changes = {}
            entity_changes = []
            for status in ("added", "removed", "modified"):
                rows = (
                    session.execute(
                        select(comparisons)
                        .where(comparisons.c.status == status)
                        .order_by(comparisons.c.entity_key)
                        .limit(request.limit)
                        .offset(request.offset)
                    )
                    .mappings()
                    .all()
                )
                changes[status] = [row["entity_key"] for row in rows]
                entity_changes.extend(self._change(row) for row in rows)
        return {
            **base,
            "snapshot": selected_data,
            "previous_snapshot": previous_data,
            "changes": {
                f"{status}_entities": list(changes[status])
                for status in ("added", "removed", "modified")
            },
            "totals": {
                status: counts.get(status, 0) for status in ("added", "removed", "modified")
            },
            "entity_changes": entity_changes,
            "has_more": any(
                counts.get(status, 0) > request.offset + request.limit
                for status in ("added", "removed", "modified")
            ),
            "limit": request.limit,
            "offset": request.offset,
        }

    @staticmethod
    def _change(row) -> dict:
        def occurrence(side, snapshot_id):
            occurrence_id = row[f"{side}_occurrence_id"]
            if occurrence_id is None:
                return None
            return {
                "entity_id": str(row[f"{side}_entity_id"]),
                "occurrence_id": str(occurrence_id),
                "snapshot_id": str(snapshot_id),
            }

        return {
            "key": row["entity_key"],
            "status": row["status"],
            "before": occurrence("before", row["before_snapshot_id"]),
            "after": occurrence("after", row["snapshot_id"]),
        }

    @staticmethod
    def _snapshot(snapshot: Snapshot, version: str | None, current_id: UUID | None) -> dict:
        return {
            "snapshot_id": str(snapshot.id),
            "revision": snapshot.revision,
            "created_at": snapshot.created_at.isoformat(),
            "is_current": snapshot.id == current_id,
            "publication_version": version,
        }
