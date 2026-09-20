from io import StringIO
from uuid import uuid4

from core.application.knowledge_publication.use_cases.publish_knowledge.outbound import (
    PublishKnowledgeOutput,
)
from core.domain.knowledge_publication.types.publication_status import PublicationStatus
from harness_memory_mcp.publication_cli import PublicationCLI


class TestPublicationCLI:
    def test_dispatches_publish_command_successfully(self) -> None:
        output = StringIO()
        pub_id = uuid4()
        snap_id = uuid4()

        def publish(input_data):
            assert input_data.project_key == "catalog"
            assert input_data.environment_name == "staging"
            assert input_data.deployment_id == "deploy-42"
            assert input_data.version == "1.2.0"
            return PublishKnowledgeOutput(
                publication_id=pub_id,
                snapshot_id=snap_id,
                status=PublicationStatus.COMPLETED,
            )

        cli = PublicationCLI(publish=publish, output=output)
        code = cli.dispatch(
            [
                "publish",
                "--project",
                "catalog",
                "--environment",
                "staging",
                "--deployment",
                "deploy-42",
                "--version",
                "1.2.0",
            ]
        )

        assert code == 0
        content = output.getvalue()
        assert "status: ACTIVATED" in content
        assert str(pub_id) in content
        assert str(snap_id) in content

    def test_returns_error_on_missing_required_options(self) -> None:
        output = StringIO()
        cli = PublicationCLI(publish=lambda _: None, output=output)

        code = cli.dispatch(["publish", "--project", "catalog"])
        assert code == 2
        assert "error: missing required options" in output.getvalue()
