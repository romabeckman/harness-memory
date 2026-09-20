from typing import Callable

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, sessionmaker

from core.application.entity_discovery.contracts.entity_search_criteria import EntitySearchCriteria
from core.application.entity_discovery.contracts.entity_search_item import EntitySearchItem
from core.application.entity_discovery.contracts.entity_search_page import EntitySearchPage
from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.application.entity_discovery.errors.search_failure import EntitySearchFailure
from core.application.entity_discovery.services.search_cursor_codec import SearchCursorCodec
from core.application.entity_discovery.value_objects.search_cursor import SearchCursor

from ..models.entity import Entity
from ..models.project import Project
from ..models.snapshot import Snapshot


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
            statement = self._statement(scope, criteria, cursor, limit)
            with self._session_factory() as session:
                rows = session.execute(statement).all()
            items = tuple(self._map_row(row) for row in rows[:limit])
            has_more = len(rows) > limit
            next_cursor = self._cursor_codec.decode(
                self._cursor_codec.encode(criteria, items[-1]), criteria
            ) if has_more and items else None
            return EntitySearchPage(items=items, next_cursor=next_cursor, limit=limit)
        except EntitySearchFailure:
            raise
        except Exception as error:
            raise EntitySearchFailure(str(error)) from None

    @staticmethod
    def _statement(
        scope: TenantScope,
        criteria: EntitySearchCriteria,
        cursor: SearchCursor | None,
        limit: int,
    ):
        predicates = [
            Project.tenant_id == scope.tenant_id,
            Entity.tenant_id == scope.tenant_id,
            Snapshot.tenant_id == scope.tenant_id,
            Entity.project_id == Project.id,
            Entity.snapshot_id == Project.active_snapshot_id,
            Entity.snapshot_id == Snapshot.id,
            Entity.project_id == Snapshot.project_id,
            Project.active_snapshot_id.is_not(None),
        ]
        if criteria.key is not None:
            predicates.append(Entity.entity_key == criteria.key)
        if criteria.project is not None:
            predicates.append(Project.key == criteria.project)
        if criteria.type is not None:
            predicates.append(Entity.entity_type == criteria.type.value)
        if criteria.name_like is not None:
            predicates.append(
                func.lower(Entity.name).like(f"{criteria.name_like}%", escape="\\")
            )
        if cursor is not None:
            predicates.append(
                or_(
                    Entity.entity_key > cursor.last_key,
                    and_(Entity.entity_key == cursor.last_key, Entity.id > cursor.last_id),
                )
            )
        return (
            select(
                Entity.id,
                Entity.entity_key,
                Entity.name,
                Entity.entity_type,
                Project.key,
                Project.name,
                Snapshot.id,
                Snapshot.revision,
            )
            .select_from(Entity)
            .join(Project, Entity.project_id == Project.id)
            .join(
                Snapshot,
                and_(
                    Entity.snapshot_id == Snapshot.id,
                    Entity.project_id == Snapshot.project_id,
                    Entity.tenant_id == Snapshot.tenant_id,
                ),
            )
            .where(*predicates)
            .order_by(Entity.entity_key.asc(), Entity.id.asc())
            .limit(limit + 1)
        )

    @staticmethod
    def _map_row(row) -> EntitySearchItem:
        values = row._mapping
        return EntitySearchItem(
            entity_id=values[Entity.id],
            key=values[Entity.entity_key],
            name=values[Entity.name],
            type=values[Entity.entity_type],
            project_key=values[Project.key],
            project_name=values[Project.name],
            snapshot_id=values[Snapshot.id],
            revision=values[Snapshot.revision],
        )
