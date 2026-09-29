from sqlalchemy import exists, select

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
    return environment_current
