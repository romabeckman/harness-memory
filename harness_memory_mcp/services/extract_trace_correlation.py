from typing import Mapping

from core.domain.platform.trace_correlation_id import TraceCorrelationId
from .trace_context_extractor import TraceContextExtractor


class ExtractTraceCorrelation:
    """Extracts W3C trace correlation for security audit and logging."""

    def __init__(self, extractor: TraceContextExtractor | None = None):
        self._extractor = extractor or TraceContextExtractor()

    def execute(self, headers: Mapping[str, str]) -> TraceCorrelationId:
        trace_id = self._extractor.extract_trace_id(headers)
        return TraceCorrelationId(value=trace_id)
