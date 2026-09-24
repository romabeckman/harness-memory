import hashlib
from typing import Callable
from uuid import UUID

from sqlalchemy import Text, and_, case, cast, exists, func, or_, select
from sqlalchemy.orm import Session, sessionmaker

from core.application.entity_discovery.contracts.entity_search_criteria import EntitySearchCriteria
from core.application.entity_discovery.contracts.entity_search_item import EntitySearchItem
from core.application.entity_discovery.contracts.entity_search_page import EntitySearchPage
from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.application.entity_discovery.errors.cursor_validation import SearchCursorValidationError
from core.application.entity_discovery.errors.search_failure import EntitySearchFailure
from core.application.entity_discovery.services.search_cursor_codec import SearchCursorCodec
from core.application.entity_discovery.value_objects.filter_fingerprint import FilterFingerprint
from core.application.entity_discovery.value_objects.search_cursor import SearchCursor

from ..models.entity import Entity
from ..models.environment import Environment
from ..models.knowledge_publication import KnowledgePublication
from ..models.project import Project
from ..models.snapshot import Snapshot
from .current_snapshot_predicate import current_snapshot_predicate
from .tenant_scope_predicate import tenant_scope_predicate


class PostgresEntitySearchRepository:
    def __init__(
        self,
        session_factory: Callable[[], Session] | sessionmaker | None = None,
        engine=None,
        session: Session | None = None,
        cursor_codec: SearchCursorCodec | None = None,
    ):
        if session_factory is not None and not callable(session_factory):
            session = session_factory
            session_factory = None
        if session is not None and session_factory is None:
            def session_factory():
                return session
        if session_factory is None and engine is not None:
            session_factory = sessionmaker(bind=engine, expire_on_commit=False)
        if session_factory is None:
            raise ValueError("session_factory or engine is required")
        self._session_factory = session_factory
        self._cursor_codec = cursor_codec or SearchCursorCodec()

    def search(
        self,
        scope: TenantScope,
        criteria: EntitySearchCriteria,
        cursor: SearchCursor | None,
        limit: int,
    ) -> EntitySearchPage:
        try:
            with self._session_factory() as session:
                scope_hash = hashlib.sha256(
                    f"{scope.tenant_id}|{scope.is_admin}".encode("utf-8")
                ).hexdigest()
                if cursor is not None and (cursor.version != 2 or cursor.scope_hash != scope_hash):
                    raise SearchCursorValidationError("search cursor scope mismatch or expired")
                pinned = cursor.pinned_snapshot_id if cursor is not None else None
                if criteria.include_past_snapshots and criteria.snapshot_id is None:
                    manifest = self._history_manifest(session, scope, criteria)
                    if cursor is not None and cursor.context_hash != manifest:
                        raise SearchCursorValidationError(
                            "search context changed; restart pagination"
                        )
                    pinned = None
                elif pinned is None:
                    selected = self._selected_snapshots(session, scope, criteria)
                    manifest = hashlib.sha256(
                        "|".join(sorted(str(value) for value in selected)).encode("utf-8")
                    ).hexdigest()
                    if cursor is not None and cursor.context_hash != manifest:
                        raise SearchCursorValidationError(
                            "search context changed; restart pagination"
                        )
                    if len(selected) == 1:
                        pinned = selected[0]
                else:
                    manifest = cursor.context_hash
                statement = self._statement(scope, criteria, cursor, limit, pinned)
                rows = session.execute(statement).all()
            items = tuple(self._map_row(row) for row in rows[:limit])
            has_more = len(rows) > limit
            next_cursor = SearchCursor(
                version=2,
                filter_fingerprint=FilterFingerprint.from_criteria(criteria),
                last_key=items[-1].key,
                last_id=items[-1].occurrence_id,
                scope_hash=scope_hash,
                context_hash=manifest,
                pinned_snapshot_id=pinned,
            ) if has_more and items else None
            return EntitySearchPage(items=items, next_cursor=next_cursor, limit=limit)
        except (EntitySearchFailure, SearchCursorValidationError):
            raise
        except Exception as error:
            raise EntitySearchFailure(str(error)) from None

    @staticmethod
    def _selected_snapshots(
        session: Session, scope: TenantScope, criteria: EntitySearchCriteria
    ) -> tuple[UUID, ...]:
        if criteria.snapshot_id is not None:
            return (criteria.snapshot_id,)
        project_predicates = [tenant_scope_predicate(scope, Project.tenant_id)]
        if criteria.tenant_id is not None:
            project_predicates.append(Project.tenant_id == criteria.tenant_id)
        if criteria.project_id is not None:
            project_predicates.append(Project.id == criteria.project_id)
        if criteria.project is not None:
            project_predicates.append(Project.key == criteria.project)
        if criteria.environment is not None:
            statement = (
                select(Environment.current_snapshot_id)
                .join(Project, and_(Project.id == Environment.project_id,
                                    Project.tenant_id == Environment.tenant_id))
                .where(Environment.name == criteria.environment,
                       Environment.current_snapshot_id.is_not(None),
                       tenant_scope_predicate(scope, Environment.tenant_id),
                       *project_predicates)
            )
            return tuple(session.scalars(statement).all())

        environment_snapshots = session.scalars(
            select(Environment.current_snapshot_id)
            .join(Project, and_(Project.id == Environment.project_id,
                                Project.tenant_id == Environment.tenant_id))
            .where(Environment.current_snapshot_id.is_not(None), *project_predicates)
        ).all()
        legacy_snapshots = session.scalars(
            select(Project.active_snapshot_id)
            .where(
                Project.active_snapshot_id.is_not(None),
                *project_predicates,
                ~exists(select(Environment.id).where(
                    Environment.project_id == Project.id,
                    Environment.tenant_id == Project.tenant_id,
                )),
            )
        ).all()
        return tuple(sorted(set((*environment_snapshots, *legacy_snapshots)), key=str))

    @staticmethod
    def _history_manifest(
        session: Session, scope: TenantScope, criteria: EntitySearchCriteria
    ) -> str:
        statement = (
            select(func.count(Snapshot.id), func.max(Snapshot.created_at))
            .join(Project, and_(Project.id == Snapshot.project_id,
                                Project.tenant_id == Snapshot.tenant_id))
            .where(tenant_scope_predicate(scope, Snapshot.tenant_id))
        )
        if criteria.tenant_id is not None:
            statement = statement.where(Snapshot.tenant_id == criteria.tenant_id)
        if criteria.project_id is not None:
            statement = statement.where(Snapshot.project_id == criteria.project_id)
        if criteria.project is not None:
            statement = statement.where(Project.key == criteria.project)
        if criteria.environment is not None:
            statement = statement.join(
                Environment,
                and_(Environment.id == Snapshot.environment_id,
                     Environment.tenant_id == Snapshot.tenant_id,
                     Environment.project_id == Snapshot.project_id),
            ).where(Environment.name == criteria.environment)
        count, latest = session.execute(statement).one()
        return hashlib.sha256(f"{count}|{latest}".encode("utf-8")).hexdigest()

    @staticmethod
    def _statement(
        scope: TenantScope,
        criteria: EntitySearchCriteria,
        cursor: SearchCursor | None,
        limit: int,
        resolved_snapshot_id: UUID | None = None,
    ):
        stable_entity_id = func.coalesce(Entity.identity_id, Entity.id)
        predicates = [
            tenant_scope_predicate(scope, Project.tenant_id),
            tenant_scope_predicate(scope, Entity.tenant_id),
            tenant_scope_predicate(scope, Snapshot.tenant_id),
            Entity.project_id == Project.id,
            Entity.snapshot_id == Snapshot.id,
            Entity.project_id == Snapshot.project_id,
        ]
        selected_snapshot = criteria.snapshot_id or resolved_snapshot_id
        if selected_snapshot is not None:
            predicates.append(Entity.snapshot_id == selected_snapshot)
        elif criteria.include_past_snapshots:
            pass
        elif criteria.environment is not None:
            predicates.append(Entity.snapshot_id == Environment.current_snapshot_id)
        else:
            predicates.append(current_snapshot_predicate())
        if criteria.tenant_id is not None:
            predicates.append(Entity.tenant_id == criteria.tenant_id)
        if criteria.project_id is not None:
            predicates.append(Project.id == criteria.project_id)
        if criteria.environment is not None:
            predicates.append(Environment.name == criteria.environment)
        if not criteria.include_history:
            predicates.extend([
                Entity.entity_type != "document_revision",
                func.coalesce(Entity.metadata_json["lifecycle"].as_string(), "active") != "removed",
            ])
        if criteria.key is not None:
            predicates.append(Entity.entity_key == criteria.key)
        if criteria.project is not None:
            predicates.append(Project.key == criteria.project)
        if criteria.type is not None:
            predicates.append(Entity.entity_type == criteria.type.value)
        if criteria.name_like is not None:
            predicates.append(
                or_(
                    func.lower(Entity.name).like(f"{criteria.name_like}%", escape="!"),
                    func.lower(Entity.entity_key).like(
                        f"{criteria.name_like}%", escape="!"
                    ),
                )
            )
        if criteria.query_like is not None:
            pattern = f"%{criteria.query_like}%"
            predicates.append(
                or_(
                    func.lower(Entity.entity_key).like(pattern, escape="!"),
                    func.lower(Entity.name).like(pattern, escape="!"),
                    func.lower(cast(Entity.metadata_json, Text)).like(pattern, escape="!"),
                )
            )
        if cursor is not None:
            predicates.append(
                or_(
                    Entity.entity_key > cursor.last_key,
                    and_(
                        Entity.entity_key == cursor.last_key,
                        Entity.id > cursor.last_id,
                    ),
                )
            )
        environment_join = (
            and_(Environment.project_id == Project.id,
                 Environment.tenant_id == Project.tenant_id,
                 Environment.name == criteria.environment)
            if criteria.environment is not None and not criteria.include_past_snapshots
            else and_(Environment.id == Snapshot.environment_id,
                      Environment.project_id == Snapshot.project_id,
                      Environment.tenant_id == Snapshot.tenant_id)
        )
        statement = (
            select(
                stable_entity_id.label("entity_id"), Entity.id.label("occurrence_id"),
                Entity.tenant_id.label("result_tenant_id"),
                Entity.project_id.label("result_project_id"),
                Entity.entity_key, Entity.name, Entity.entity_type,
                Project.key, Project.name, Snapshot.id, Snapshot.revision,
                Environment.name.label("environment_name"),
                case(
                    (Environment.id.is_not(None),
                     Environment.current_snapshot_id == Snapshot.id),
                    else_=Project.active_snapshot_id == Snapshot.id,
                ).label("is_current_snapshot"),
                KnowledgePublication.id.label("publication_id"),
                KnowledgePublication.version.label("publication_version"),
                KnowledgePublication.status.label("publication_status"),
                KnowledgePublication.deployment_id.label("deployment_id"),
            ).select_from(Entity).join(Project, Entity.project_id == Project.id)
            .join(
                Snapshot,
                and_(Entity.snapshot_id == Snapshot.id,
                     Entity.project_id == Snapshot.project_id,
                     Entity.tenant_id == Snapshot.tenant_id),
            )
            .outerjoin(Environment, environment_join)
            .outerjoin(
                KnowledgePublication,
                and_(KnowledgePublication.id == Snapshot.publication_id,
                     KnowledgePublication.snapshot_id == Snapshot.id,
                     KnowledgePublication.project_id == Snapshot.project_id,
                     KnowledgePublication.tenant_id == Snapshot.tenant_id),
            )
        )
        return (
            statement
            .where(*predicates)
            .order_by(Entity.entity_key.asc(), Entity.id.asc())
            .limit(limit + 1)
        )

    @staticmethod
    def _map_row(row) -> EntitySearchItem:
        values = row._mapping
        return EntitySearchItem(
            entity_id=values["entity_id"],
            occurrence_id=values["occurrence_id"],
            tenant_id=str(values["result_tenant_id"]),
            project_id=values["result_project_id"],
            key=values[Entity.entity_key],
            name=values[Entity.name],
            type=values[Entity.entity_type],
            project_key=values[Project.key],
            project_name=values[Project.name],
            snapshot_id=values[Snapshot.id],
            revision=values[Snapshot.revision],
            environment_name=values["environment_name"],
            is_current_snapshot=values["is_current_snapshot"],
            publication_id=values["publication_id"],
            publication_version=values["publication_version"],
            publication_status=values["publication_status"],
            deployment_id=values["deployment_id"],
        )
