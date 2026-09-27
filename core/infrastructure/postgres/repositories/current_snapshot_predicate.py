from sqlalchemy import and_, exists, or_, select

from ..models.entity import Entity
from ..models.environment import Environment
from ..models.project import Project


def current_snapshot_predicate():
    environment_current = exists(
        select(Environment.id)
        .where(
            Environment.project_id == Project.id,
            Environment.tenant_id == Project.tenant_id,
            Environment.current_snapshot_id == Entity.snapshot_id,
        )
        .correlate(Project, Entity)
    )
    project_has_environments = exists(
        select(Environment.id)
        .where(
            Environment.project_id == Project.id,
            Environment.tenant_id == Project.tenant_id,
        )
        .correlate(Project)
    )
    legacy_project_current = and_(
        Project.active_snapshot_id == Entity.snapshot_id,
        ~project_has_environments,
    )
    return or_(environment_current, legacy_project_current)
