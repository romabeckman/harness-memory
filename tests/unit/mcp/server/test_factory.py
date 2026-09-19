from mcp.config import RuntimeSettings
from mcp.server.factory import create_mcp_server


def test_create_mcp_server_is_named_and_database_independent():
    server = create_mcp_server(
        RuntimeSettings(mcp_host="127.0.0.1", mcp_port=8000, database_url=None)
    )

    assert server.name == "harness-memory"
