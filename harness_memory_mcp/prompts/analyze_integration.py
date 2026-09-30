from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field, StrictStr
from harness_memory_mcp.guidance import MCP_CONTEXT_SCOPE_GUIDANCE

from ._guidance import input_data, message


def register_analyze_integration_prompt(server: FastMCP, _observable=None):
    @server.prompt(
        name="analyze_integration",
        description="Guide evidence-backed integration analysis between two entities.",
    )
    def analyze_integration(
        source: Annotated[StrictStr, Field(min_length=1, max_length=255)],
        target: Annotated[StrictStr, Field(min_length=1, max_length=255)],
    ):
        return message(
            f"Analyze integration from {input_data(source)} to {input_data(target)}. "
            + MCP_CONTEXT_SCOPE_GUIDANCE
            + "Load source and target context with get_context. "
            "Use find_integration_paths to inspect known paths. "
            "Check ownership, provenance, and evidence for every relevant relation. "
            "Keep unknowns explicit. Do not compute or claim an integration path in this prompt."
        )

    return analyze_integration


register_analyze_integration = register_analyze_integration_prompt
