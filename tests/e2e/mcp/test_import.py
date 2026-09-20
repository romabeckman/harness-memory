def test_runtime_entry_point_imports_without_starting_infrastructure():
    import mcp.server.app as app

    assert app.server.name == "harness-memory"
