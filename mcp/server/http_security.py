"""HTTP response mapping for authenticated MCP authorization failures."""

from collections.abc import Callable
from typing import Any


def install_http_security_error_mapping(server: Any) -> None:
    """Map FastMCP authorization protocol errors to HTTP 403 responses.

    FastMCP serializes middleware authorization exceptions into successful
    JSON-RPC/SSE responses. Production HTTP callers need transport-level
    semantics, so wrap the generated ASGI application and change only those
    redacted authorization responses.
    """

    original_http_app = server.http_app

    def http_app(*args: Any, **kwargs: Any):
        application = original_http_app(*args, **kwargs)

        async def wrapped(scope: dict[str, Any], receive: Callable, send: Callable) -> None:
            if scope.get("type") != "http":
                await application(scope, receive, send)
                return

            response_start: dict[str, Any] | None = None
            response_started = False
            streaming_sse = False
            stream_buffer = bytearray()
            stream_buffer_limit = 64 * 1024

            async def capture(message: dict[str, Any]) -> None:
                nonlocal response_start, response_started, streaming_sse, stream_buffer
                if message["type"] == "http.response.start":
                    response_start = dict(message)
                    streaming_sse = any(
                        key.lower() == b"content-type"
                        and value.lower().startswith(b"text/event-stream")
                        for key, value in response_start.get("headers", [])
                    )
                    return
                if message["type"] == "http.response.body":
                    if response_start is None:
                        await send(message)
                        return
                    if streaming_sse and not response_started:
                        initial_body = message.get("body", b"")
                        if not stream_buffer and not any(
                            marker in initial_body[:128].lower()
                            for marker in (b"event:", b"data:")
                        ):
                            response_started = True
                            await send(response_start)
                            await send(message)
                            return
                        stream_buffer.extend(message.get("body", b""))
                        complete_event = (
                            b"\n\n" in stream_buffer or b"\r\n\r\n" in stream_buffer
                        )
                        if len(stream_buffer) < stream_buffer_limit and not complete_event and message.get(
                            "more_body", False
                        ):
                            return
                        buffered_body = bytes(stream_buffer)
                        stream_buffer.clear()
                        if _is_authorization_error(buffered_body):
                            response_start["status"] = 403
                            headers = list(response_start.get("headers", []))
                            headers.append(
                                (b"www-authenticate", b'Bearer error="insufficient_scope"')
                            )
                            response_start["headers"] = headers
                        response_started = True
                        await send(response_start)
                        buffered_message = dict(message)
                        buffered_message["body"] = buffered_body
                        await send(buffered_message)
                        return
                    if not response_started:
                        response_started = True
                        body = message.get("body", b"")
                        if not message.get("more_body", False) and _is_authorization_error(body):
                            response_start["status"] = 403
                            headers = list(response_start.get("headers", []))
                            headers.append(
                                (b"www-authenticate", b'Bearer error="insufficient_scope"')
                            )
                            response_start["headers"] = headers
                        await send(response_start)
                    await send(message)
                    return
                await send(message)

            await application(scope, receive, capture)
            if response_start is not None and not response_started:
                await send(response_start)

        # Keep Starlette/FastMCP inspection attributes available to callers.
        wrapped.__dict__.update(getattr(application, "__dict__", {}))
        wrapped._fastmcp_application = application
        return wrapped

    server.http_app = http_app


def _is_authorization_error(body: bytes) -> bool:
    normalized = body.lower()
    return b'"iserror":true' in normalized and b"authorization failed" in normalized
