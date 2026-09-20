from mcp.config import RuntimeSettings

from .factory import create_mcp_server



def _fail_closed_server():
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
        body = b'{"error":"production authentication is not configured"}'
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
        return create_mcp_server(settings, production=True)
    except Exception:
        return _fail_closed_server()


server = _build_server()
mcp = server


def main() -> None:
    settings = RuntimeSettings()
    settings.mcp_production = True
    create_mcp_server(settings, production=True).run(
        transport="http",
        host=settings.mcp_host,
        port=settings.mcp_port,
    )


if __name__ == "__main__":
    main()
