from fastmcp import FastMCP

from .analyze_integration import (
    register_analyze_integration,
    register_analyze_integration_prompt,
)
from .load_corporate_context import (
    register_load_corporate_context,
    register_load_corporate_context_prompt,
)
from .review_change_impact import (
    register_review_change_impact,
    register_review_change_impact_prompt,
)


def register_mcp_guidance_prompts(server: FastMCP) -> None:
    register_load_corporate_context_prompt(server)
    register_analyze_integration_prompt(server)
    register_review_change_impact_prompt(server)


__all__ = [
    "register_analyze_integration_prompt",
    "register_analyze_integration",
    "register_load_corporate_context",
    "register_load_corporate_context_prompt",
    "register_mcp_guidance_prompts",
    "register_review_change_impact",
    "register_review_change_impact_prompt",
]
