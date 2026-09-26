---
doc_type: feature
domain: mcp_access_surface
stack: [Python 3.12+, FastMCP 4.x, Pydantic 2.x, SQLAlchemy 2.x, PostgreSQL]
node_id: "feature:mcp-access-surface"
tags: [mcp, resources, prompts, bounded-reads, tenant]
edges:
  - relation: implements
    target: "adr:architecture"
  - relation: tested_by
    target: "adr:tests"
  - relation: references
    target: "adr:mcp"
  - relation: depends_on
    target: "feature:impact-analysis"
    read: must
updated: 2026-09-26
---
# MCP Access Surface
Expose bounded memory resources and deterministic workflow prompts through the FastMCP catalog.

```graph
{"node_id":"feature:mcp-access-surface","domain":"mcp_access_surface","implements":["adr:architecture"],"tested_by":["adr:tests"],"entrypoints":["harness_memory_mcp/resources/entity_resource.py","harness_memory_mcp/resources/project_resource.py","harness_memory_mcp/resources/snapshot_resource.py","harness_memory_mcp/prompts/load_corporate_context.py","harness_memory_mcp/prompts/analyze_integration.py","harness_memory_mcp/prompts/review_change_impact.py"],"registration_files":["harness_memory_mcp/server/factory.py"],"reference_files":["core/application/mcp_access_surface/use_cases/get_project_resource/handler.py","core/infrastructure/postgres/repositories/memory_resource_repository.py"],"code_files":["core/application/mcp_access_surface/contracts/project_resource_input.py","core/application/mcp_access_surface/contracts/project_resource_output.py","core/application/mcp_access_surface/contracts/snapshot_context_item.py","core/application/mcp_access_surface/contracts/snapshot_fact_page.py","core/application/mcp_access_surface/contracts/snapshot_resource_input.py","core/application/mcp_access_surface/contracts/snapshot_resource_output.py","core/application/mcp_access_surface/errors/resource_not_found.py","core/application/mcp_access_surface/errors/resource_query_failure.py","core/application/mcp_access_surface/ports/memory_resource_repository.py","core/application/mcp_access_surface/types/resource_read_bounds.py","core/application/mcp_access_surface/use_cases/get_project_resource/inbound.py","core/application/mcp_access_surface/use_cases/get_project_resource/outbound.py","core/application/mcp_access_surface/use_cases/get_snapshot_resource/handler.py","core/application/mcp_access_surface/use_cases/get_snapshot_resource/inbound.py","core/application/mcp_access_surface/use_cases/get_snapshot_resource/outbound.py","harness_memory_mcp/prompts/_guidance.py","harness_memory_mcp/services/resource_error_mapper.py"],"test_files":["tests/unit/core/application/mcp_access_surface/contracts/test_contracts.py","tests/unit/core/application/mcp_access_surface/use_cases/test_get_project_resource.py","tests/unit/core/application/mcp_access_surface/use_cases/test_get_snapshot_resource.py","tests/unit/mcp/prompts/test_prompts.py","tests/unit/mcp/resources/test_entity_resource.py","tests/unit/mcp/resources/test_project_resource.py","tests/unit/mcp/resources/test_snapshot_resource.py","tests/unit/mcp/server/test_factory.py","tests/integration/core/infrastructure/postgres/repositories/test_project_resource.py","tests/integration/core/infrastructure/postgres/repositories/test_snapshot_resource.py","tests/e2e/mcp/test_resource_catalog.py","tests/e2e/mcp/test_resources.py","tests/e2e/mcp/test_prompts.py"],"knowledge":{"schema_version":1,"entities":[{"id":"capability:read-mcp-resources","type":"capability","label":"Read MCP resources","definition":"Expose bounded entity, project, and snapshot context through MCP resource URIs.","aliases":[]},{"id":"rule:bounded-resource-reads","type":"rule","label":"Bounded resource reads","definition":"Apply trusted tenant scope and fixed fact and evidence limits to resource reads.","aliases":[]},{"id":"contract:mcp-resource-content","type":"contract","label":"MCP resource content","definition":"Read-only resource output with bounded normalized facts and explicit truncation.","aliases":[]}],"claims":[{"id":"claim:resource-scope-and-bounds","subject":"capability:read-mcp-resources","relation":"constrained_by","object":"rule:bounded-resource-reads","statement":"Resource handlers pass trusted tenant context to repositories and enforce fixed fact and evidence bounds.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"core/application/mcp_access_surface/use_cases/get_snapshot_resource/handler.py","locator":"GetSnapshotResourceHandler.execute","snapshot":null},{"kind":"code","source":"core/application/mcp_access_surface/types/resource_read_bounds.py","locator":"ResourceReadBounds","snapshot":null},{"kind":"code","source":"core/infrastructure/postgres/repositories/memory_resource_repository.py","locator":"tenant-scoped bounded resource queries","snapshot":null}],"derived_from":[],"gap":null},{"id":"claim:normalized-read-contract","subject":"capability:read-mcp-resources","relation":"exposes","object":"contract:mcp-resource-content","statement":"Snapshot resources read normalized entity, relation, and evidence rows without exposing raw snapshot payloads or a write operation.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"core/infrastructure/postgres/repositories/memory_resource_repository.py","locator":"snapshot resource query","snapshot":null},{"kind":"code","source":"harness_memory_mcp/resources/snapshot_resource.py","locator":"snapshot resource registration","snapshot":null}],"derived_from":[],"gap":null}]}}
```

## OVERVIEW

Register a read-only MCP catalog: bounded query/impact tools, two environment tools,
three resources, and three prompts. Adapters delegate to application ports and PostgreSQL
projections; prompts render guidance only.

## FOLDER STRUCTURE

- `harness_memory_mcp/`: resource and prompt adapters; `core/application/mcp_access_surface/`: contracts and handlers; `core/infrastructure/postgres/`: bounded tenant reads.
- `tests/{unit,integration,e2e}/`: contract, persistence, catalog, and read checks.

## MAIN CONCEPTS / COMPONENTS

- **Entity resource**: Read the newest current environment occurrence at `memory://entities/{entity_id}`; pin one environment with `get_context` and `snapshot_id`.
- **Project resource**: Read the active snapshot at `memory://projects/{project_key}` and decode one URI segment once.
- **Snapshot resource**: Read a tenant-owned historical snapshot at `memory://snapshots/{snapshot_id}` without activation or raw payload exposure.
- **Prompt and environment surfaces**: Confirm projects with `search_projects`; prompts guide existing tools. Environment comparisons return added, removed, modified, and unchanged entity fingerprints.
- **Current-first guidance**: Use each environment's `current_snapshot_id`; use `Project.active_snapshot_id` only when no environment records exist. Search history only on request.

## HOW TO READ

1. Require trusted tenant context and `memory:read`; cap resources at 25 facts and 5 evidence items.
2. Expose truncation flags and identical sanitized not-found results for missing or foreign-tenant identifiers.
3. Confirm project keys with `search_projects`; validate prompt arguments and render deterministic text without I/O.

## TOOL CALL ORDER

1. Call `search_projects` without filters to list accessible projects, or supply **key** or **query** to narrow results. For generic project questions, inspect each non-null environment `current_snapshot_id` and keep findings labeled by environment.
2. Call `search_entities` with at least one filter or scope selector. For a named environment, use only its current snapshot. Reuse `entity_id`, `project_id`, and `snapshot_id` from the same result to pin `get_context`.
3. Use entity IDs from `search_entities` for `get_dependencies`, `find_integration_paths`, or `analyze_impact` when authorized.
4. Use project key and environment names from `search_projects` for `get_environment` and `compare_environments`. If current search has no match, refine the current query or report no current match. Search older snapshots only when the user explicitly asks for history, a past state, comparison, or changes; establish the current baseline first.

REQUIRED: Supply one target UUID to `analyze_impact`; if multiple target fields are supplied, all must identify the same entity.
PROHIBITED: Register the legacy `publish_project_snapshot` adapter in the default MCP catalog; publish through REST or the SDK CLI.

## PARAMETERS / CONFIGURATIONS

| Name | Type | Required | Description | Default |
|------|------|----------|-------------|---------|
| `entity_id` | UUID | Resource path | Entity identity; the resource resolves its newest current environment occurrence. | — |
| `project_key` | URI segment | Resource path | Percent-encoded project key, decoded once. | — |
| `snapshot_id` | UUID | Resource path | Snapshot identity. | — |
| `fact_limit` | fixed integer | Internal | Maximum resource facts. | `25` |
| `evidence_limit` | fixed integer | Internal | Maximum evidence items per bounded fact. | `5` |

## BEST PRACTICES

REQUIRED: Read searchable document content from normalized entity metadata; never expose raw snapshot payloads.
REQUIRED: Keep prompt renderers data-free; mention existing public tools instead of duplicating business logic.
PROHIBITED: Register snapshot publication or any other graph mutation as an MCP tool.
PROHIBITED: Treat tenant identity from URI or prompt arguments as authorization, or expose repository errors.
PROHIBITED: Let resource adapters own SQL, traversal, activation, or impact classification.

## REFERENCES

- [**ARCHITECTURE.md**](../../adr/ARCHITECTURE.md): Defines adapter, application, and persistence boundaries.
- [**TESTS.md**](../../adr/TESTS.md): Defines FastMCP catalog, read, and persistence test tiers.
- [**MCP.md**](../../adr/MCP.md): Defines resource URIs, prompt responsibilities, and scopes.
- [**impact-analysis.md**](../core/impact-analysis.md): Supplies the existing impact contract named by review guidance.
