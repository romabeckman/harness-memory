from uuid import UUID, uuid4
import pytest

from core.domain.environment.aggregates.environment import Environment
from core.domain.environment.events.environment_snapshot_promoted import (
    EnvironmentSnapshotPromoted,
)
from core.domain.environment.value_objects.environment_name import EnvironmentName
from core.domain.environment.value_objects.environment_type import EnvironmentType
from core.domain.snapshot_publication.value_objects.project_key import ProjectKey


class TestEnvironment:
    def test_creates_environment_successfully(self) -> None:
        env_id = uuid4()
        project_key = ProjectKey("checkout-api")
        name = EnvironmentName("staging")

        env = Environment(
            id=env_id,
            project_key=project_key,
            name=name,
            environment_type=EnvironmentType.STAGING,
        )

        assert env.id == env_id
        assert env.project_key == project_key
        assert env.name == name
        assert env.environment_type == EnvironmentType.STAGING
        assert env.current_snapshot_id is None
        assert len(env.events) == 0

    def test_promotes_active_snapshot_and_records_event(self) -> None:
        env = Environment(
            id=uuid4(),
            project_key=ProjectKey("checkout-api"),
            name=EnvironmentName("staging"),
        )
        new_snapshot_id = uuid4()

        env.promote_snapshot(new_snapshot_id)

        assert env.current_snapshot_id == new_snapshot_id
        assert len(env.events) == 1
        event = env.events[0]
        assert isinstance(event, EnvironmentSnapshotPromoted)
        assert event.environment_id == env.id
        assert event.snapshot_id == new_snapshot_id
        assert event.project_key == env.project_key.value

    def test_rejects_invalid_snapshot_id_on_promotion(self) -> None:
        env = Environment(
            id=uuid4(),
            project_key=ProjectKey("checkout-api"),
            name=EnvironmentName("staging"),
        )

        with pytest.raises(ValueError, match="snapshot_id must be a valid UUID"):
            env.promote_snapshot(None)  # type: ignore[arg-type]
