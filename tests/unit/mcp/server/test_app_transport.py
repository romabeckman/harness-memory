from types import SimpleNamespace
from unittest.mock import Mock

import harness_memory_mcp.server.app as app


def test_main_starts_stateless_http_transport(monkeypatch):
    settings = SimpleNamespace(mcp_host="127.0.0.1", mcp_port=8000)
    server = SimpleNamespace(run=Mock())
    monkeypatch.setattr(app, "RuntimeSettings", lambda: settings)
    monkeypatch.setattr(app, "create_mcp_server", lambda *_args, **_kwargs: server)

    app.main()

    server.run.assert_called_once_with(
        transport="http",
        host="127.0.0.1",
        port=8000,
        stateless_http=True,
    )
