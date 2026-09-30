from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field, StrictStr
from harness_memory_mcp.guidance import MCP_CONTEXT_SCOPE_GUIDANCE

from ._guidance import input_data, message


def register_review_change_impact_prompt(server: FastMCP, _observable=None):
    @server.prompt(
        name="review_change_impact",
        description="Guide bounded impact review for a proposed corporate change.",
    )
    def review_change_impact(
        entity_id: Annotated[StrictStr, Field(min_length=1, max_length=255)],
        change_type: Annotated[StrictStr, Field(min_length=1, max_length=255)],
        description: Annotated[StrictStr | None, Field(max_length=4096)] = None,
    ):
        return message(
            f"Review change for entity {input_data(entity_id)}. "
            f"Change type: {input_data(change_type)}. Description: {input_data(description)}. "
            + MCP_CONTEXT_SCOPE_GUIDANCE
            + "Call the existing analyze_impact tool with memory:impact authorization. "
            "Inspect returned evidence and truncation flags. "
            "Review unknowns before proposing action. "
            "This prompt does not execute impact analysis or infer impact conclusions."
        )

    return review_change_impact


register_review_change_impact = register_review_change_impact_prompt
