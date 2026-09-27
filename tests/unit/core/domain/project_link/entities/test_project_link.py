from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from core.domain.project_link.entities.project_link import ProjectLink
from core.domain.project_link.events.project_linked import ProjectLinked
from core.domain.project_link.events.project_unlinked import ProjectUnlinked
from core.domain.project_link.value_objects.canonical_project_pair import CanonicalProjectPair


def test_create_project_link_success():
    project_a = uuid4()
    project_b = uuid4()
    pair = CanonicalProjectPair(project_a, project_b)
    actor_id = uuid4()

    link = ProjectLink(pair=pair, created_by=actor_id)

    assert isinstance(link.id, UUID)
    assert link.pair == pair
    assert link.created_by == actor_id
    assert isinstance(link.created_at, datetime)
    assert link.created_at.tzinfo is not None

    # Should register ProjectLinked domain event
    assert len(link.events) == 1
    event = link.events[0]
    assert isinstance(event, ProjectLinked)
    assert event.link_id == link.id
    assert event.project_a_id == pair.project_a_id
    assert event.project_b_id == pair.project_b_id
    assert event.created_at == link.created_at


def test_reject_creation_without_canonical_pair():
    with pytest.raises(ValueError, match="pair must be a CanonicalProjectPair"):
        ProjectLink(pair=None)  # type: ignore[arg-type]


def test_project_unlinked_event_fields():
    project_a = uuid4()
    project_b = uuid4()
    now = datetime.now(UTC)

    event = ProjectUnlinked(
        project_a_id=project_a,
        project_b_id=project_b,
        unlinked_at=now,
    )

    assert event.project_a_id == project_a
    assert event.project_b_id == project_b
    assert event.unlinked_at == now
