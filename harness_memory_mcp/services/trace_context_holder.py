from contextvars import ContextVar


class TraceContextHolder:
    """Thread-safe and async-safe holder for the active trace ID."""

    _current_trace_id: ContextVar[str | None] = ContextVar("current_trace_id", default=None)
    _current_span_id: ContextVar[str | None] = ContextVar("current_span_id", default=None)

    @classmethod
    def get_current_trace_id(cls) -> str | None:
        return cls._current_trace_id.get()

    @classmethod
    def set_current_trace_id(cls, trace_id: str | None):
        return cls._current_trace_id.set(trace_id)

    @classmethod
    def reset(cls, token) -> None:
        cls._current_trace_id.reset(token)

    @classmethod
    def get_current_span_id(cls) -> str | None:
        return cls._current_span_id.get()

    @classmethod
    def set_current_span_id(cls, span_id: str | None):
        return cls._current_span_id.set(span_id)

    @classmethod
    def reset_span_id(cls, token) -> None:
        cls._current_span_id.reset(token)
