import re
from typing import Mapping


class TraceContextExtractor:
    """Extracts W3C TraceContext identifiers from transport headers."""

    _TRACEPARENT_REGEX = re.compile(
        r"^([0-9a-fA-F]{2})-([0-9a-fA-F]{32})-([0-9a-fA-F]{16})-([0-9a-fA-F]{2})$"
    )

    @classmethod
    def extract_trace_id(cls, headers: Mapping[str, str] | None) -> str | None:
        parsed = cls._parse_traceparent(headers)
        return parsed[0] if parsed is not None else None

    @classmethod
    def extract_span_id(cls, headers: Mapping[str, str] | None) -> str | None:
        parsed = cls._parse_traceparent(headers)
        return parsed[1] if parsed is not None else None

    @classmethod
    def _parse_traceparent(
        cls, headers: Mapping[str, str] | None
    ) -> tuple[str, str] | None:
        if not headers:
            return None

        traceparent = None
        for key, value in headers.items():
            if isinstance(key, str) and key.lower() == "traceparent":
                traceparent = value
                break

        if not traceparent or not isinstance(traceparent, str):
            return None

        match = cls._TRACEPARENT_REGEX.match(traceparent.strip())
        if not match:
            return None

        version, trace_id, parent_id, flags = match.groups()
        if version == "ff":
            return None
        if trace_id == "0" * 32:
            return None
        if parent_id == "0" * 16:
            return None

        return trace_id.lower(), parent_id.lower()
