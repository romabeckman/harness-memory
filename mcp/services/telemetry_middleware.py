from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

from fastmcp.server.dependencies import get_http_headers, get_http_request
from fastmcp.server.middleware import Middleware

from core.infrastructure.telemetry.telemetry_tracer import TelemetryTracer
from core.infrastructure.telemetry.tracer_provider import TelemetryTracerProvider
from .trace_context_extractor import TraceContextExtractor
from .trace_context_holder import TraceContextHolder

logger = logging.getLogger(__name__)


class TelemetryMiddleware(Middleware):
    """Instruments MCP tool executions with OpenTelemetry spans and extracts trace context."""

    def __init__(
        self,
        tracer: TelemetryTracer | None = None,
        tenant_context: Any | None = None,
    ):
        self._tracer = tracer or TelemetryTracerProvider.get_tracer()
        self._tenant_context = tenant_context

    async def on_call_tool(self, context: Any, call_next: Callable) -> Any:
        tool_name = getattr(getattr(context, "message", None), "name", "unknown_tool")
        tenant_id = None
        if self._tenant_context is not None:
            try:
                principal = self._tenant_context.security_context.current()
                if principal is not None:
                    tenant_id = principal.tenant_id
            except Exception:
                pass

        headers = {}
        try:
            req = get_http_request()
            headers = dict(req.headers)
        except Exception:
            try:
                headers = get_http_headers(include={"traceparent"})
            except Exception:
                pass

        return await self.handle(
            tool_name=tool_name,
            tenant_id=tenant_id,
            invoke=lambda: call_next(context),
            headers=headers,
        )

    async def handle(
        self,
        tool_name: str,
        tenant_id: str | None,
        invoke: Callable,
        headers: dict[str, str] | None = None,
    ) -> Any:
        trace_id = TraceContextExtractor.extract_trace_id(headers)
        span_id = TraceContextExtractor.extract_span_id(headers)
        token = None
        span_token = None
        if trace_id:
            token = TraceContextHolder.set_current_trace_id(trace_id)
        if span_id:
            span_token = TraceContextHolder.set_current_span_id(span_id)

        span_attributes = {
            "tool.name": tool_name,
            "tenant.id": tenant_id or "anonymous",
        }
        if trace_id:
            span_attributes["trace.id"] = trace_id

        span_cm = None
        active_span = None
        try:
            span_cm = self._tracer.start_as_current_span(
                f"mcp.tool.{tool_name}", attributes=span_attributes
            )
            active_span = span_cm.__enter__()
        except Exception as error:
            logger.debug("telemetry span creation failed: %s", error)

        start_time = time.perf_counter()
        tool_error: Exception | None = None
        try:
            result = invoke()
            if hasattr(result, "__await__"):
                result = await result
            return result
        except Exception as error:
            tool_error = error
            if active_span is not None:
                try:
                    if hasattr(active_span, "set_attribute"):
                        active_span.set_attribute("error", True)
                        active_span.set_attribute("error.type", type(error).__name__)
                except Exception:
                    pass
            raise
        finally:
            if active_span is not None:
                try:
                    if hasattr(active_span, "set_attribute"):
                        active_span.set_attribute(
                            "duration_ms", (time.perf_counter() - start_time) * 1000.0
                        )
                except Exception:
                    pass
            if span_cm is not None:
                try:
                    if tool_error is None:
                        span_cm.__exit__(None, None, None)
                    else:
                        span_cm.__exit__(
                            type(tool_error),
                            tool_error,
                            tool_error.__traceback__,
                        )
                except Exception as exit_err:
                    logger.debug("telemetry span exit failed: %s", exit_err)
            if token is not None:
                TraceContextHolder.reset(token)
            if span_token is not None:
                TraceContextHolder.reset_span_id(span_token)
