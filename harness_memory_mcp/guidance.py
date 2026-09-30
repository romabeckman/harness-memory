MCP_CONTEXT_SCOPE_GUIDANCE = (
    "Use search_projects to resolve the exact key, tenant, and available environments. "
    "Ask the user to choose the project/tenant when the question is broad or scope is ambiguous. "
    "Ask the user to choose an environment when none is supplied or explicitly established "
    "in the conversation. Reuse an explicitly selected environment; do not assume production. "
    "Do not answer project facts before scope is resolved. Search multiple environments "
    "only when the user explicitly requests them, labeling each result. "
)

MCP_SCOPE_GUIDANCE = MCP_CONTEXT_SCOPE_GUIDANCE + (
    "Use get_environment for the selected environment's environments.current_snapshot_id. "
    "That pointer identifies its latest published version; never choose a different "
    "environment because its timestamp or version is newer. If the pointer is null, "
    "report no current data. Search current facts with search_entities pinned to this "
    "snapshot_id and project/tenant. Call get_context with entity_id and snapshot_id "
    "from the same search result. Use get_dependencies or find_integration_paths for relationships. "
    "For changes that already happened, use get_history with project, tenant, environment, "
    "and query terms. Inspect a returned snapshot_id with get_history using the same query; "
    "read both before and after references with get_context to explain what changed. "
    "For proposed changes, use analyze_impact. Use compare_environments for two current "
    "environments after both are selected. Only current_snapshot_id is current; label "
    "older snapshots historical. Report evidence and unknowns."
)
