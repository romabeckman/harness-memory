import pytest
from harness_memory_mcp.services.trace_context_extractor import TraceContextExtractor


def test_extract_valid_w3c_trace_id():
    headers = {
        "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
    }
    trace_id = TraceContextExtractor.extract_trace_id(headers)
    assert trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"


def test_return_none_when_traceparent_absent_or_malformed():
    assert TraceContextExtractor.extract_trace_id({}) is None
    assert TraceContextExtractor.extract_trace_id({"traceparent": "invalid-header-value"}) is None
    assert (
        TraceContextExtractor.extract_trace_id(
            {"traceparent": "00-00000000000000000000000000000000-00f067aa0ba902b7-01"}
        )
        is None
    )
    assert (
        TraceContextExtractor.extract_trace_id(
            {"traceparent": "ff-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"}
        )
        is None
    )


def test_extract_valid_w3c_parent_span_id():
    headers = {
        "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
    }

    assert TraceContextExtractor.extract_span_id(headers) == "00f067aa0ba902b7"


def test_return_none_for_non_string_header_keys_or_values():
    assert TraceContextExtractor.extract_trace_id({1: "traceparent"}) is None
    assert TraceContextExtractor.extract_trace_id({"traceparent": 1}) is None
