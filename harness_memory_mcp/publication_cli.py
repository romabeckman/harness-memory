import argparse
from collections.abc import Callable, Sequence
from typing import TextIO

from core.application.knowledge_publication.use_cases.publish_knowledge.inbound import (
    PublishKnowledgeInput,
)
from core.application.knowledge_publication.use_cases.publish_knowledge.outbound import (
    PublishKnowledgeOutput,
)
from core.domain.knowledge_publication.types.publication_status import PublicationStatus


class PublicationCLI:
    def __init__(
        self,
        publish: Callable[[PublishKnowledgeInput], PublishKnowledgeOutput],
        output: TextIO,
    ) -> None:
        self._publish = publish
        self._output = output

    def dispatch(self, arguments: Sequence[str]) -> int:
        if not arguments or arguments[0] != "publish":
            self._output.write("error: expected 'publish' command\n")
            return 2

        parser = argparse.ArgumentParser(prog="harness-memory publish", add_help=False)
        parser.add_argument("--project", dest="project", required=False)
        parser.add_argument("--environment", dest="environment", required=False)
        parser.add_argument("--deployment", dest="deployment", required=False)
        parser.add_argument("--version", dest="version", required=False)
        parser.add_argument("--tenant-id", dest="tenant_id", default="default")

        try:
            parsed, _ = parser.parse_known_args(arguments[1:])
        except Exception as error:
            self._output.write(f"error: {error}\n")
            return 2

        if not all([parsed.project, parsed.environment, parsed.deployment, parsed.version]):
            self._output.write(
                "error: missing required options (--project, --environment, --deployment, --version)\n"
            )
            return 2

        try:
            input_data = PublishKnowledgeInput(
                project_key=parsed.project,
                environment_name=parsed.environment,
                deployment_id=parsed.deployment,
                version=parsed.version,
                tenant_id=parsed.tenant_id,
            )
            result = self._publish(input_data)
            status_label = (
                "ALREADY_PUBLISHED"
                if result.status == PublicationStatus.ALREADY_PUBLISHED
                else "ACTIVATED"
            )
            self._output.write(f"status: {status_label}\n")
            self._output.write(f"publication_id: {result.publication_id}\n")
            self._output.write(f"snapshot_id: {result.snapshot_id}\n")
            return 0
        except Exception as error:
            self._output.write(f"error: {error}\n")
            return 1
