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
            "known or search its key and name with query. For a generic project question, "
            "inspect each non-null Environment.current_snapshot_id exposed by "
            "search_projects.environments. "
            "Search current facts in every environment and label each result with its "
            "environment. For a named environment, use only that environment's "
            "current_snapshot_id or get_environment. If no environment has a current "
            "snapshot, report no current environment data. "
            "For facts, use search_entities with the exact project key and a short query "
            "phrase. query searches entity keys, names, and metadata content, including "
            "document sections; name is a prefix filter. Pin get_context with entity_id "
            "and snapshot_id from the same search result. Without snapshot_id, get_context "
            "resolves the newest current occurrence. For an environment comparison, "
            "compare_environments reads current snapshots. If current search has no match, "
            "report no match in current snapshots and refine the current query if useful. "
            "Do not search past snapshots unless the user explicitly asks for history, "
            "past state, comparison, or changes. For those requests, establish the current "
            "baseline first, then use include_past_snapshots=true and label each historical "
            "result by snapshot_id and revision. Check is_current_snapshot and "
            "publication_version. Do not describe historical results as current. Treat "
            "facts without retrieved evidence as unknown. "
            "Read memory://snapshots/{snapshot_id} when a selected snapshot needs fuller "
            "bounded facts. "
            "Report retrieved evidence and unknowns. Do not infer business conclusions "
            "from missing data."
        )

    return load_corporate_context


register_load_corporate_context = register_load_corporate_context_prompt
