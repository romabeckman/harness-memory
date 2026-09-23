from typing import Any, Protocol


class PublicationBaselineReader(Protocol):
    def load_latest_graph(self, project_key: str, environment: str,
                          tenant_id: str | None = None) -> dict[str, Any]: ...
