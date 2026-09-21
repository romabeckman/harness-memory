import pytest

from core.domain.knowledge_publication.value_objects.deployment_id import DeploymentId


class TestDeploymentId:
    def test_creates_deployment_id_successfully(self) -> None:
        deployment_id = DeploymentId("gh-run-12849")
        assert deployment_id.value == "gh-run-12849"

    def test_rejects_empty_or_whitespace_deployment_id(self) -> None:
        with pytest.raises(ValueError, match="deployment_id must not be empty"):
            DeploymentId("   ")

    def test_rejects_deployment_id_exceeding_max_length(self) -> None:
        with pytest.raises(ValueError, match="deployment_id exceeds maximum length"):
            DeploymentId("a" * 256)

    def test_equality_by_value(self) -> None:
        dep1 = DeploymentId("deploy-1")
        dep2 = DeploymentId("deploy-1")
        dep3 = DeploymentId("deploy-2")

        assert dep1 == dep2
        assert dep1 != dep3
        assert len({dep1, dep2}) == 1
