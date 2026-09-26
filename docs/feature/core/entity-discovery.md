---
doc_type: feature
domain: entity_discovery
stack: [Python 3.12+, FastMCP 4.x, Pydantic 2.x, SQLAlchemy 2.x, PostgreSQL]
node_id: "feature:entity-discovery"
tags: [entity-search, pagination, tenant, snapshots]
edges:
  - relation: implements
    target: "adr:architecture"
  - relation: tested_by
    target: "adr:tests"
  - relation: references
    target: "adr:mcp"
  - relation: depends_on
    target: "feature:snapshot-publication"
    read: must
updated: 2026-09-26
---
# Entity Discovery
Find projects and bounded Entity identities through tenant-scoped MCP search tools.

```graph
{"node_id":"feature:entity-discovery","domain":"entity_discovery","implements":["adr:architecture"],"tested_by":["adr:tests"],"entrypoints":["harness_memory_mcp/tools/search_entities.py","harness_memory_mcp/tools/search_projects.py"],"registration_files":["harness_memory_mcp/server/factory.py"],"reference_files":["core/application/entity_discovery/use_cases/search_entities/handler.py","core/infrastructure/postgres/repositories/entity_search_repository.py","core/infrastructure/postgres/repositories/knowledge_read_repository.py"],"code_files":["core/application/entity_discovery/contracts/entity_search_criteria.py","core/application/entity_discovery/contracts/entity_search_item.py","core/application/entity_discovery/contracts/entity_search_page.py","core/application/entity_discovery/contracts/project_environment_item.py","core/application/entity_discovery/contracts/project_search_item.py","core/application/entity_discovery/contracts/project_search_page.py","core/application/entity_discovery/contracts/tenant_scope.py","core/application/entity_discovery/errors/cursor_validation.py","core/application/entity_discovery/errors/search_failure.py","core/application/entity_discovery/errors/project_search_failure.py","core/application/entity_discovery/ports/entity_search_repository.py","core/application/entity_discovery/ports/project_search_repository.py","core/application/entity_discovery/services/search_criteria_normalizer.py","core/application/entity_discovery/services/search_cursor_codec.py","core/application/entity_discovery/use_cases/search_entities/inbound.py","core/application/entity_discovery/use_cases/search_entities/outbound.py","core/application/entity_discovery/use_cases/search_projects/__init__.py","core/application/entity_discovery/use_cases/search_projects/handler.py","core/application/entity_discovery/use_cases/search_projects/inbound.py","core/application/entity_discovery/value_objects/filter_fingerprint.py","core/application/entity_discovery/value_objects/search_cursor.py","core/application/snapshot_publication/errors/missing_tenant_context.py","core/domain/snapshot_publication/types/entity_type.py","core/infrastructure/postgres/models/entity.py","core/infrastructure/postgres/models/environment.py","core/infrastructure/postgres/models/project.py","core/infrastructure/postgres/models/snapshot.py","core/infrastructure/postgres/repositories/current_snapshot_predicate.py","migrations/versions/002_indexes_and_relationships.py","harness_memory_mcp/services/entity_search_response_mapper.py","harness_memory_mcp/services/tenant_context.py"],"test_files":["tests/unit/core/application/entity_discovery/contracts/test_contracts.py","tests/unit/core/application/entity_discovery/services/test_cursor_and_criteria.py","tests/unit/core/application/entity_discovery/use_cases/test_search_entities.py","tests/unit/core/application/entity_discovery/use_cases/test_search_projects.py","tests/unit/core/infrastructure/postgres/repositories/test_entity_search_sql.py","tests/unit/core/infrastructure/postgres/models/test_entity_search_indexes.py","tests/unit/core/infrastructure/postgres/migrations/test_entity_search_indexes.py","tests/unit/mcp/tools/test_search_entities.py","tests/unit/mcp/tools/test_search_projects.py","tests/unit/core/infrastructure/postgres/repositories/test_knowledge_read_repository.py","tests/integration/core/infrastructure/postgres/repositories/test_entity_search_repository.py","tests/integration/migrations/test_entity_search_indexes.py","tests/e2e/mcp/test_search_entities.py","tests/e2e/mcp/test_tool_descriptions.py"],"knowledge":{"schema_version":1,"entities":[{"id":"capability:discover-entities","type":"capability","label":"Discover entities","definition":"Find projects and entity identities in published knowledge snapshots.","aliases":[]},{"id":"rule:cursor-context-binding","type":"rule","label":"Cursor context binding","definition":"Continue a page only with the same filters, trusted scope, and snapshot context.","aliases":[]},{"id":"contract:entity-search-page","type":"contract","label":"Entity search page","definition":"Bounded entity results with occurrence identity, snapshot context, and an optional continuation cursor.","aliases":[]}],"claims":[{"id":"claim:current-snapshot-selection","subject":"capability:discover-entities","relation":"exposes","object":"contract:entity-search-page","statement":"Return bounded identity and revision pages; default to current environment snapshots and use the project pointer only when no environment records exist.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"core/infrastructure/postgres/repositories/entity_search_repository.py","locator":"PostgresEntitySearchRepository._selected_snapshots and _statement","snapshot":null},{"kind":"code","source":"core/application/entity_discovery/contracts/entity_search_item.py","locator":"EntitySearchItem fields","snapshot":null}],"derived_from":[],"gap":null},{"id":"claim:search-cursor-binding","subject":"capability:discover-entities","relation":"constrained_by","object":"rule:cursor-context-binding","statement":"Reject cursors when trusted scope or the selected snapshot set changes; history requests also bind to a snapshot manifest.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"core/infrastructure/postgres/repositories/entity_search_repository.py","locator":"PostgresEntitySearchRepository.search: scope_hash and context_hash checks","snapshot":null}],"derived_from":[],"gap":null},{"id":"claim:search-publication-dependency","subject":"capability:discover-entities","relation":"depends_on","object":"feature:snapshot-publication#capability:publish-snapshot","statement":"Entity discovery reads facts from snapshots and current pointers created by snapshot publication.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"core/infrastructure/postgres/repositories/entity_search_repository.py","locator":"PostgresEntitySearchRepository._selected_snapshots and _statement","snapshot":null}],"derived_from":[],"gap":null}]}}
```

## OVERVIEW

`search_projects` discovers projects with tenant and environment attribution. `search_entities` searches each environment's current snapshot by default. Historical occurrences appear only when the caller explicitly selects history or a snapshot.

## FOLDER STRUCTURE

- `core/application/entity_discovery/`: search contracts and cursor policy.
- `core/infrastructure/postgres/`: snapshot selection and paged queries.
- `harness_memory_mcp/tools/`: project and entity search adapters.
- `tests/{unit,integration,e2e}/`: module-aligned checks.

## MAIN CONCEPTS / COMPONENTS

- **Snapshot scope**: Pin one snapshot, select current environment snapshots by default, and include history only when requested. `include_history` adds document revisions and retired documents.
- **Results**: Project search returns environment names and current snapshot IDs; entity filters combine key, name, type, project, and literal content. Entity pages return scalar identity and revision fields, not metadata, relations, or evidence.

## HOW TO SEARCH

1. Use `search_projects` to confirm project identity and inspect current environment snapshots.
2. Search with a filter or scope selector; match keys/types exactly and use `name` for prefixes or `query` for literal phrases.
3. Continue with unchanged cursor filters; restart when snapshots change. Pass `entity_id` and `snapshot_id` together to `get_context`.

## PARAMETERS / CONFIGURATIONS

| Parameters | Contract |
|------------|----------|
| `key`, `project`, `type` | Exact key, project key, or supported entity type. |
| `name`, `query` | Case-insensitive name/key prefix or literal phrase in key, name, or metadata. |
| `tenant_id`, `project_id`, `environment`, `snapshot_id` | Narrow scope or select one immutable/current snapshot. With no environment, use every environment current snapshot; use the project pointer only if no environments exist. |
| `include_history`, `include_past_snapshots` | Independently include document revisions/retired documents or older snapshots. |
| `limit`, `cursor` | Page size 1?500; opaque cursor up to 1,024 characters, bound to scope and snapshot context. |
| `search_projects.key`, `query`, `limit`, `offset` | Exact key or substring query; page size 1?500 and offset 0?10,000. |

## BEST PRACTICES

REQUIRED: Authorize `memory:read` and treat tenant selectors as filters, never authorization.
REQUIRED: Narrow metadata searches by exact project key when known.
REQUIRED: Fetch one extra row to decide whether to emit `next_cursor`; bind cursor validity to scope and snapshot context.
REQUIRED: Search history only when requested; label historical matches.
PROHIBITED: Treat an empty entity result as proof that a project does not exist or a fact is false.

## REFERENCES

- [**ARCHITECTURE.md**](../../adr/ARCHITECTURE.md): Defines application ports and infrastructure boundaries.
- [**TESTS.md**](../../adr/TESTS.md): Defines query, persistence, and MCP test tiers.
- [**MCP.md**](../../adr/MCP.md): Defines the project and entity search tool contracts.
- [**snapshot-publication.md**](./snapshot-publication.md): Owns active snapshot publication and tenant-scoped facts.
