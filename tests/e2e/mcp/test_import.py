def test_runtime_entry_point_imports_without_starting_infrastructure():
    import harness_memory_mcp.server.app as app

    assert app.server.name == "harness-memory"
    assert callable(app.server)
