from uuid import uuid4
import pytest

from core.domain.environment.value_objects.environment_name import EnvironmentName
from core.domain.knowledge_publication.aggregates.knowledge_publication import (
    KnowledgePublication,
)
from core.domain.knowledge_publication.events.knowledge_publication_recorded import (
    KnowledgePublicationRecorded,
)
from core.domain.knowledge_publication.types.publication_status import PublicationStatus
from core.domain.knowledge_publication.value_objects.deployment_id import DeploymentId
from core.domain.knowledge_publication.value_objects.publication_id import PublicationId
from core.domain.snapshot_publication.value_objects.project_key import ProjectKey


class TestKnowledgePublication:
    def test_creates_publication_in_pending_status(self) -> None:
        pub_id = PublicationId.generate()
        project_key = ProjectKey("catalog")
        env_name = EnvironmentName("staging")
        deployment_id = DeploymentId("deploy-900")

        pub = KnowledgePublication(
            id=pub_id,
            project_key=project_key,
            environment_name=env_name,
            deployment_id=deployment_id,
            version="1.4.0",
        )

        assert pub.id == pub_id
        assert pub.project_key == project_key
        assert pub.environment_name == env_name
        assert pub.deployment_id == deployment_id
        assert pub.version == "1.4.0"
        assert pub.status == PublicationStatus.PENDING
        assert pub.snapshot_id is None
        assert len(pub.events) == 0

    def test_completes_publication_and_records_event(self) -> None:
        pub = KnowledgePublication(
            id=PublicationId.generate(),
            project_key=ProjectKey("catalog"),
            environment_name=EnvironmentName("staging"),
            deployment_id=DeploymentId("deploy-900"),
            version="1.4.0",
        )
        snapshot_id = uuid4()

        pub.complete(snapshot_id)

        assert pub.status == PublicationStatus.COMPLETED
        assert pub.snapshot_id == snapshot_id
        assert len(pub.events) == 1
        event = pub.events[0]
        assert isinstance(event, KnowledgePublicationRecorded)
        assert event.publication_id == pub.id.value
        assert event.snapshot_id == snapshot_id
        assert event.environment_name == pub.environment_name.value
        assert event.deployment_id == pub.deployment_id.value

    def test_rejects_duplicate_completion_when_already_completed(self) -> None:
        pub = KnowledgePublication(
            id=PublicationId.generate(),
            project_key=ProjectKey("catalog"),
            environment_name=EnvironmentName("staging"),
            deployment_id=DeploymentId("deploy-900"),
            version="1.4.0",
        )
        pub.complete(uuid4())

        with pytest.raises(ValueError, match="publication is already completed"):
            pub.complete(uuid4())

    def test_rejects_empty_snapshot_id_on_completion(self) -> None:
        pub = KnowledgePublication(
            id=PublicationId.generate(),
            project_key=ProjectKey("catalog"),
            environment_name=EnvironmentName("staging"),
            deployment_id=DeploymentId("deploy-900"),
            version="1.4.0",
        )

        with pytest.raises(ValueError, match="snapshot_id must be a valid UUID"):
            pub.complete(None)  # type: ignore[arg-type]
