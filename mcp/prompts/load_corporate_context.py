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
            "First use search_entities for bounded discovery. "
            "Then use get_context for selected entities. "
            "Read memory://entities/{entity_id}, memory://projects/{project_key}, "
            "or memory://snapshots/{snapshot_id} when identifiers are known. "
            "Report retrieved evidence and unknowns. Do not infer business conclusions "
            "from missing data."
        )

    return load_corporate_context


register_load_corporate_context = register_load_corporate_context_prompt
