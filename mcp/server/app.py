from mcp.config import RuntimeSettings

from .factory import create_mcp_server

server = create_mcp_server()
mcp = server


def main() -> None:
    settings = RuntimeSettings()
    create_mcp_server(settings).run(
        transport="http",
        host=settings.mcp_host,
        port=settings.mcp_port,
    )


if __name__ == "__main__":
    main()
