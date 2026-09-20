import json

from harness_memory_mcp.config import RuntimeSettings
from harness_memory_mcp.migration_cli import MigrationCLI

from .factory import create_mcp_server


def _fail_closed_server(error_message: str = "production authentication is not configured"):
    async def application(scope, receive, send):
        if scope.get("type") == "lifespan":
            while True:
                message = await receive()
                if message.get("type") == "lifespan.startup":
                    await send({"type": "lifespan.startup.complete"})
                elif message.get("type") == "lifespan.shutdown":
                    await send({"type": "lifespan.shutdown.complete"})
                    return
        if scope.get("type") != "http":
            return
        body = json.dumps({"error": error_message}).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": 503,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode("ascii")),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})

    application.name = "harness-memory"
    application.http_app = lambda *args, **kwargs: application
    return application


def _build_server():
    try:
        settings = RuntimeSettings()
        settings.mcp_production = True
        return create_mcp_server(settings, production=True, verify_schema=False)
    except Exception as exc:
        return _fail_closed_server(MigrationCLI._redact(str(exc)))


server = _build_server()
mcp = server


def main() -> None:
    import sys

    try:
        settings = RuntimeSettings()
        settings.mcp_production = True
        server = create_mcp_server(settings, production=True, verify_schema=False)
        server.run(
            transport="http",
            host=settings.mcp_host,
            port=settings.mcp_port,
        )
    except Exception as exc:
        sys.stderr.write(f"Startup failed: {MigrationCLI._redact(str(exc))}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
