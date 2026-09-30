---
doc_type: feature
domain: environment_history
stack: [Python 3.12+, FastMCP 4.x, Pydantic 2.x, SQLAlchemy 2.x, PostgreSQL]
node_id: "feature:environment-history"
tags: [environment, history, snapshots, entities, mcp]
edges:
  - relation: implements
    target: "adr:architecture"
  - relation: tested_by
    target: "adr:tests"
  - relation: references
    target: "adr:mcp"
  - relation: depends_on
    target: "feature:environment-snapshots"
    read: must
updated: 2026-09-29
---
```graph
{"node_id":"feature:environment-history","domain":"environment_history","implements":["adr:architecture"],"tested_by":["adr:tests"],"entrypoints":["harness_memory_mcp/tools/get_history.py"],"registration_files":["harness_memory_mcp/server/factory.py","harness_memory_mcp/services/component_scope_policy.py"],"reference_files":["core/infrastructure/postgres/repositories/environment_history_repository.py","core/infrastructure/postgres/repositories/memory_resource_repository.py","core/infrastructure/postgres/repositories/snapshot_entity_comparison.py"],"code_files":["core/application/environment_context/ports/environment_history_repository.py","core/application/environment_context/use_cases/get_history/handler.py","core/application/environment_context/use_cases/get_history/inbound.py"],"test_files":["tests/integration/core/infrastructure/postgres/repositories/test_environment_history_repository.py","tests/unit/mcp/tools/test_get_history.py","tests/e2e/mcp/test_tool_descriptions.py","tests/e2e/mcp/test_get_history.py"],"knowledge":{"schema_version":1,"entities":[{"id":"capability:read-environment-history","type":"capability","label":"Read environment history","definition":"List historical snapshots and inspect entity changes for one environment.","aliases":[]},{"id":"rule:current-pointer-is-latest","type":"rule","label":"Current pointer selects latest revision","definition":"Only environments.current_snapshot_id identifies the latest published version of that environment.","aliases":[]},{"id":"contract:history-read","type":"contract","label":"History read","definition":"Search snapshot revisions and entity changes by literal before/after terms; return filtered totals and references.","aliases":[]}],"claims":[{"id":"claim:history-read-contract","subject":"capability:read-environment-history","relation":"exposes","object":"contract:history-read","statement":"get_history searches changed entity keys, names, and metadata on both sides, including removals, before totals and pagination; detail returns before/after references against the preceding revision or empty initial state.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"core/infrastructure/postgres/repositories/environment_history_repository.py","locator":"PostgresEnvironmentHistoryRepository.get_history","snapshot":null},{"kind":"code","source":"harness_memory_mcp/tools/get_history.py","locator":"register_get_history","snapshot":null},{"kind":"code","source":"core/infrastructure/postgres/repositories/snapshot_entity_comparison.py","locator":"snapshot_entity_comparison: literal matching on both sides","snapshot":null}],"derived_from":[],"gap":null},{"id":"claim:current-pointer","subject":"capability:read-environment-history","relation":"constrained_by","object":"rule:current-pointer-is-latest","statement":"History output labels a snapshot current only when its ID equals the environment current_snapshot_id; publication promotes the new revision in the same transaction.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"core/infrastructure/postgres/repositories/environment_history_repository.py","locator":"PostgresEnvironmentHistoryRepository._snapshot","snapshot":null},{"kind":"code","source":"core/infrastructure/postgres/repositories/knowledge_publication_repository.py","locator":"publish_atomically_with_environment: revision rebase and env.current_snapshot_id assignment","snapshot":null}],"derived_from":[],"gap":null}]}}
```

# Environment History

Read one environment's immutable snapshot revisions and entity changes through MCP.

## OVERVIEW

`get_history` requires `memory:read` and a trusted tenant. **`environments.current_snapshot_id` identifies the latest published revision for that environment.** Older snapshots remain historical.

## FOLDER STRUCTURE

- `harness_memory_mcp/tools/`: validated MCP boundary.
- `core/application/environment_context/`: history contract and handler.
- `core/infrastructure/postgres/`: tenant-scoped snapshot query and entity comparison.

## HOW TO READ HISTORY

1. Resolve the exact project key and tenant with `search_projects`; ask for missing or ambiguous scope and an environment unless already selected.
2. Call `get_history(project_key, environment, query=...)` for past changes. Without `query`, list all revisions newest first. With `query`, list only revisions containing matching entity changes.
3. Pass a returned `snapshot_id` and the same `query` to inspect added, removed, and modified entities against the preceding revision. The first revision compares with empty state.
4. Call `get_context` with each non-null `before` and `after` reference's `entity_id` and `snapshot_id` for full historical facts and evidence.

## PARAMETERS / CONFIGURATIONS

| Parameter | Contract |
|-----------|----------|
| `project_key`, `environment` | Required exact names from `search_projects`. |
| `snapshot_id` | Optional snapshot from the selected environment; selects entity changes. |
| `query` | Optional nonblank literal substring, at most 255 characters; case-insensitive matching in keys, names, and metadata on either side, including removals. |
| `limit`, `offset` | Page 1–100 snapshots or entity keys per change category; offset 0–10,000. |
| `tenant_id` | Optional selector for permitted cross-tenant reads; never grants access. |

## OUTPUT AND PAGINATION

Snapshot pages include `total_snapshots` and `has_more`. Detail includes legacy key lists in `changes`, filtered `totals`, and `entity_changes` with status and before/after entity, occurrence, and snapshot IDs. Added entities have no before reference; removed entities have no after reference.

Filtering precedes totals and pagination. Each change category gets its own `limit` and `offset`, so detail contains at most three times `limit` references. Unchanged entities never match history searches; no matches return empty pages and zero totals. Snapshot pages without `query` retain unchanged revisions.

## BEST PRACTICES

REQUIRED: Use `current_snapshot_id` to identify current state; label older results historical.
REQUIRED: Preserve tenant scope and sanitize internal errors.
PROHIBITED: Treat an arbitrary snapshot ID as current or accept a snapshot from another environment.

## REFERENCES

- [**ARCHITECTURE.md**](../../adr/ARCHITECTURE.md): Defines adapter and persistence boundaries.
- [**TESTS.md**](../../adr/TESTS.md): Defines backend verification tiers.
- [**MCP.md**](../../adr/MCP.md): Defines MCP read scope and tool contracts.
- [**environment-snapshots.md**](./environment-snapshots.md): Defines current environment state and publication.
