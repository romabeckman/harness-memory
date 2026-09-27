from unittest.mock import MagicMock
import pytest
from core.infrastructure.telemetry.telemetry_tracer import TelemetryTracer
from harness_memory_mcp.services.telemetry_middleware import TelemetryMiddleware


@pytest.mark.asyncio
async def test_execute_wrapped_tool_logic_when_unconfigured_noop():
    middleware = TelemetryMiddleware(tracer=TelemetryTracer("test-noop"))

    async def invoke():
        return {"result": "success"}

    result = await middleware.handle(
        tool_name="search_entities",
        tenant_id="tenant-123",
        invoke=invoke,
    )
    assert result == {"result": "success"}


@pytest.mark.asyncio
async def test_record_tool_name_tenant_id_and_error_on_exception():
    mock_span = MagicMock()
    mock_tracer = MagicMock()
    mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span

    middleware = TelemetryMiddleware(tracer=mock_tracer)

    class CustomBusinessError(RuntimeError):
        pass

    async def failing_invoke():
        raise CustomBusinessError("business failure")

    with pytest.raises(CustomBusinessError):
        await middleware.handle(
            tool_name="publish_project_snapshot",
            tenant_id="tenant-456",
            invoke=failing_invoke,
        )

    mock_tracer.start_as_current_span.assert_called_once()
    call_args = mock_tracer.start_as_current_span.call_args
    assert "publish_project_snapshot" in call_args[0][0]
    assert call_args[1]["attributes"]["tenant.id"] == "tenant-456"

    mock_span.set_attribute.assert_any_call("error", True)
    mock_span.set_attribute.assert_any_call("error.type", "CustomBusinessError")
    assert any(call.args[0] == "duration_ms" for call in mock_span.set_attribute.call_args_list)


@pytest.mark.asyncio
async def test_span_context_receives_tool_exception_for_exporter_status():
    class RecordingContext:
        def __init__(self):
            self.exit_args = None

        def __enter__(self):
            return MagicMock()

        def __exit__(self, *args):
            self.exit_args = args

    context = RecordingContext()
    tracer = MagicMock()
    tracer.start_as_current_span.return_value = context
    middleware = TelemetryMiddleware(tracer=tracer)

    async def invoke():
        raise RuntimeError("tool failed")

    with pytest.raises(RuntimeError):
        await middleware.handle("search_entities", "tenant-1", invoke)

    assert context.exit_args[0] is RuntimeError
