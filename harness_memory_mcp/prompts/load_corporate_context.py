from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field, StrictStr

from ._guidance import input_data, message


def register_load_corporate_context_prompt(server: FastMCP, _observable=None):
    @server.prompt(
        name="load_corporate_context",
        description="Guide bounded corporate context discovery before cross-system planning.",
    )
    def load_corporate_context(
        subject: Annotated[StrictStr, Field(min_length=1, max_length=255)],
        project_key: Annotated[StrictStr | None, Field(min_length=1, max_length=255)] = None,
        entity_id: Annotated[StrictStr | None, Field(min_length=1, max_length=255)] = None,
    ):
        return message(
            "Load corporate context for "
            f"{input_data(subject)}. Project hint: {input_data(project_key)}. "
            f"Entity hint: {input_data(entity_id)}. "
            "First use search_projects to confirm the exact project key when a project is "
            "known or search its key and name with query. A project without an active "
            "snapshot has no current graph data. For knowledge facts, use search_entities "
            "with the exact project key and a short query phrase. query searches entity "
            "keys, names, and metadata content, including document sections; name is a "
            "prefix filter. Prioritize current snapshots: Project.active_snapshot_id "
            "is the latest project execution; Environment.current_snapshot_id is the "
            "latest version of that environment. For environment-specific questions, "
            "use get_environment and search_entities with the environment or its current "
            "snapshot_id; do not substitute the project snapshot. Then use get_context "
            "for selected entities. For a comparison of environments, "
            "compare_environments reads their current snapshots. Establish the current "
            "baseline first. If the user requests history or comparison with older "
            "versions, use search_entities with "
            "include_past_snapshots=true even when current facts exist; inspect selected "
            "historical snapshot_id values with get_context. If a search is "
            "empty, verify the project with search_projects and try a specific key or "
            "content phrase. If current facts remain empty, repeat search_entities with "
            "include_past_snapshots=true. Check is_current_snapshot and publication_version "
            "for each match; identify historical results by snapshot_id and revision. "
            "Do not describe a historical match as current. Treat facts with no "
            "retrieved evidence as unknown. "
            "Read memory://entities/{entity_id}, memory://projects/{project_key}, "
            "or memory://snapshots/{snapshot_id} when identifiers are known. "
            "Report retrieved evidence and unknowns. Do not infer business conclusions "
            "from missing data."
        )

    return load_corporate_context


register_load_corporate_context = register_load_corporate_context_prompt
