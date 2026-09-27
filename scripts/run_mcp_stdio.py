"""Stdio runner for harness-memory MCP server in Antigravity."""

import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(PROJECT_ROOT / ".env")

from core.application.snapshot_publication.types.publication_context import (  # noqa: E402
    PublicationContext,
)
from harness_memory_mcp.config import RuntimeSettings  # noqa: E402
from harness_memory_mcp.server.factory import create_mcp_server  # noqa: E402
from harness_memory_mcp.services.tenant_context import TenantContextProvider  # noqa: E402


class McpStdioRunner:
    @staticmethod
    def run() -> None:
        settings = RuntimeSettings()
        tenant = TenantContextProvider()
        tenant._context.set(
            PublicationContext(
                tenant_id="6e5c445f-77c8-4ed7-bc9c-3c9942ba2992",
                scopes=frozenset(["memory:read", "memory:publish", "memory:impact"]),
                is_admin=True,
            )
        )
        server = create_mcp_server(
            settings,
            tenant_context=tenant,
            production=False,
            verify_schema=False,
        )
        server.run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    McpStdioRunner.run()
