from core.application.knowledge_publication.ports.publication_baseline_reader import (
    PublicationBaselineReader,
)


class GetPublicationBaseline:
    def __init__(self, reader: PublicationBaselineReader):
        self._reader = reader

    def execute(self, project_key: str, environment: str, tenant_id: str | None = None):
        if not all(value.strip() for value in (project_key, environment)):
            raise ValueError("project and environment are required")
        return self._reader.load_latest_graph(project_key, environment, tenant_id)
