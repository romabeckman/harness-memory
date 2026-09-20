"""HTTP response mapping for authenticated MCP authorization failures."""

from collections.abc import Callable
from typing import Any

from harness_memory_mcp.services.component_scope_policy import ComponentScopePolicy

_INVALID_ARGUMENT_MARKERS = (
    b"invalid arguments",
    b"validation error",
    b"extra_forbidden",
)


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
                    if response_start.get("status") == 401:
                        stream_buffer.clear()
                        return
                    streaming_sse = any(
                        key.lower() == b"content-type"
                        and value.lower().startswith(b"text/event-stream")
                        for key, value in response_start.get("headers", [])
                    )
                    return
                if message["type"] == "http.response.body":
                    if response_start is not None and response_start.get("status") == 401:
                        stream_buffer.extend(message.get("body", b""))
                        if message.get("more_body", False):
                            return
                        response_started = True
                        body = _authentication_failure_body()
                        start = _response_with_body(
                            response_start,
                            status=401,
                            body=body,
                            www_authenticate=b'Bearer error="invalid_token"',
                        )
                        await send(start)
                        await send({**message, "body": body, "more_body": False})
                        return
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
                        if (
                            len(stream_buffer) < stream_buffer_limit
                            and not complete_event
                            and message.get("more_body", False)
                        ):
                            return
                        buffered_body = bytes(stream_buffer)
                        stream_buffer.clear()
                        if _is_authorization_error(buffered_body):
                            response_start["status"] = 403
                            headers = list(response_start.get("headers", []))
                            headers.append(
                                (b"www-authenticate", _authorization_challenge(buffered_body))
                            )
                            response_start["headers"] = headers
                        if _is_invalid_argument(buffered_body):
                            buffered_body = _mark_invalid_argument(buffered_body)
                            response_start = _response_with_body(
                                response_start,
                                status=response_start.get("status", 200),
                                body=buffered_body,
                            )
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
                                (b"www-authenticate", _authorization_challenge(body))
                            )
                            response_start["headers"] = headers
                        if not message.get("more_body", False) and _is_invalid_argument(body):
                            body = _mark_invalid_argument(body)
                            response_start = _response_with_body(
                                response_start,
                                status=response_start.get("status", 200),
                                body=body,
                            )
                        await send(response_start)
                        if body is not message.get("body", b""):
                            message = {**message, "body": body}
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


def _is_invalid_argument(body: bytes) -> bool:
    normalized = body.lower()
    return b'"iserror":true' in normalized and any(
        marker in normalized for marker in _INVALID_ARGUMENT_MARKERS
    )


def _authorization_challenge(body: bytes) -> bytes:
    normalized = body.lower()
    marker = b"(required:"
    start = normalized.find(marker)
    scope = b""
    if start != -1:
        start += len(marker)
        end = normalized.find(b")", start)
        if end != -1:
            scope = normalized[start:end].strip()
    if not scope:
        for kind in (b"tool", b"resource", b"prompt"):
            component_marker = b"for " + kind + b" '"
            component_start = normalized.find(component_marker)
            if component_start == -1:
                continue
            component_start += len(component_marker)
            component_end = normalized.find(b"'", component_start)
            if component_end == -1:
                continue
            component_name = normalized[component_start:component_end].decode("ascii", "ignore")
            required = ComponentScopePolicy().required_scope(
                kind.decode("ascii"), component_name
            )
            if required:
                scope = required.encode("ascii")
                break
    if not scope or any(
        character not in b"abcdefghijklmnopqrstuvwxyz0123456789:._-" for character in scope
    ):
        return b'Bearer error="insufficient_scope"'
    return b'Bearer error="insufficient_scope", scope="' + scope + b'"'


def _mark_invalid_argument(body: bytes) -> bytes:
    if b"INVALID_ARGUMENT" in body:
        return body
    normalized = body.lower()
    for marker in _INVALID_ARGUMENT_MARKERS:
        index = normalized.find(marker)
        if index != -1:
            return body[:index] + b"INVALID_ARGUMENT: " + body[index:]
    return body


def _authentication_failure_body() -> bytes:
    return b'{"error":"invalid_token","error_description":"authentication required"}'


def _response_with_body(
    response_start: dict[str, Any],
    *,
    status: int,
    body: bytes,
    www_authenticate: bytes | None = None,
) -> dict[str, Any]:
    headers = [
        (key, value)
        for key, value in response_start.get("headers", [])
        if key.lower() not in {b"content-length", b"www-authenticate"}
    ]
    if www_authenticate is not None:
        headers.append((b"www-authenticate", www_authenticate))
    if body.startswith(b"{") and not any(key.lower() == b"content-type" for key, _ in headers):
        headers.append((b"content-type", b"application/json"))
    headers.append((b"content-length", str(len(body)).encode("ascii")))
    return {**response_start, "status": status, "headers": headers}
