---
doc_type: feature
domain: relationship_context
stack: [Python 3.12+, FastMCP 4.x, Pydantic 2.x, SQLAlchemy 2.x, PostgreSQL]
node_id: "feature:relationship-context"
tags: [context, dependencies, provenance, tenant]
edges:
  - relation: implements
    target: "adr:architecture"
  - relation: tested_by
    target: "adr:tests"
  - relation: references
    target: "adr:mcp"
  - relation: depends_on
    target: "feature:entity-discovery"
    read: must
updated: 2026-09-30
---
# Relationship Context
Return bounded context for selected entities and direct dependency views for one entity.

```graph
{"node_id":"feature:relationship-context","domain":"relationship_context","implements":["adr:architecture"],"tested_by":["adr:tests"],"entrypoints":["harness_memory_mcp/tools/get_context.py","harness_memory_mcp/tools/get_dependencies.py"],"registration_files":["harness_memory_mcp/server/factory.py"],"reference_files":[],"code_files":["harness_memory_mcp/services/tenant_context.py","harness_memory_mcp/services/relationship_response_mapper.py","core/application/entity_discovery/contracts/tenant_scope.py","core/application/relationship_context/contracts/entity_context_item.py","core/application/relationship_context/contracts/project_context_item.py","core/application/relationship_context/contracts/evidence_view.py","core/application/relationship_context/contracts/relation_view.py","core/application/relationship_context/contracts/dependency_view.py","core/application/relationship_context/types/dependency_relation_type.py","core/application/relationship_context/types/relationship_direction.py","core/application/relationship_context/types/relationship_query_bounds.py","core/application/relationship_context/ports/relationship_query_repository.py","core/application/relationship_context/errors/entity_context_not_found.py","core/application/relationship_context/errors/relationship_query_failure.py","core/application/relationship_context/use_cases/get_context/inbound.py","core/application/relationship_context/use_cases/get_context/handler.py","core/application/relationship_context/use_cases/get_context/outbound.py","core/application/relationship_context/use_cases/get_context/page.py","core/application/relationship_context/use_cases/get_dependencies/inbound.py","core/application/relationship_context/use_cases/get_dependencies/handler.py","core/application/relationship_context/use_cases/get_dependencies/outbound.py","core/infrastructure/postgres/repositories/current_snapshot_predicate.py","core/infrastructure/postgres/repositories/relationship_query_repository.py"],"test_files":["tests/unit/core/application/relationship_context/contracts/test_contracts.py","tests/unit/core/application/relationship_context/ports/test_relationship_query_repository.py","tests/unit/core/application/relationship_context/use_cases/test_get_context.py","tests/unit/core/application/relationship_context/use_cases/test_get_dependencies.py","tests/unit/mcp/services/test_relationship_response_mapper.py","tests/unit/mcp/server/test_relationship_factory.py","tests/unit/mcp/tools/test_get_context.py","tests/unit/mcp/tools/test_get_dependencies.py","tests/integration/core/infrastructure/postgres/repositories/test_relationship_context_query.py","tests/integration/core/infrastructure/postgres/repositories/test_relationship_query_plans.py","tests/e2e/mcp/test_relationship_queries.py"],"knowledge":{"schema_version":1,"entities":[{"id":"capability:read-relationship-context","type":"capability","label":"Read relationship context","definition":"Return bounded entity context, direct relations, and dependency views.","aliases":[]},{"id":"rule:tenant-snapshot-context","type":"rule","label":"Tenant snapshot context","definition":"Resolve requested entity context within trusted tenant and selected snapshot scope.","aliases":[]},{"id":"contract:relationship-context","type":"contract","label":"Relationship context","definition":"A bounded entity page with direct relations and relation-linked evidence.","aliases":[]}],"claims":[{"id":"claim:context-scope-and-resolution","subject":"capability:read-relationship-context","relation":"constrained_by","object":"rule:tenant-snapshot-context","statement":"The repository resolves entity identity under TenantScope and uses the selected snapshot or current environment context.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"core/infrastructure/postgres/repositories/relationship_query_repository.py","locator":"PostgresRelationshipQueryRepository.load_context, list_contexts, and _resolve_entity","snapshot":null}],"derived_from":[],"gap":null},{"id":"claim:context-evidence-contract","subject":"capability:read-relationship-context","relation":"exposes","object":"contract:relationship-context","statement":"Context results attach bounded evidence to returned relations and exclude snapshot-level evidence.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"core/infrastructure/postgres/repositories/relationship_query_repository.py","locator":"PostgresRelationshipQueryRepository._load_relations and _load_evidence","snapshot":null}],"derived_from":[],"gap":null}]}}
```

## OVERVIEW

`get_context` and `get_dependencies` are read-only queries over trusted scope. They expose direct relations, owners, dependency peers, provenance, and linked evidence within request bounds. Context reads use each environment's current snapshot by default; `snapshot_id` pins an immutable snapshot.

## FOLDER STRUCTURE

- `harness_memory_mcp/tools/` and `services/`: thin adapters and safe response mapping.
- `core/application/relationship_context/`: contracts, ports, and handlers.
- `core/infrastructure/postgres/`: scoped snapshot reads.
- `tests/{unit,integration,e2e}/`: module-aligned checks.

## MAIN CONCEPTS / COMPONENTS

- **Pinned context**: Resolve an entity in the requested snapshot. Without one, use the newest occurrence in current environment snapshots; reject ambiguous identities.
- **Scope listing**: Select by snapshot, project, or tenant; otherwise list current environment snapshots, newest first, with bounded paging.
- **Direct relations**: Return one-hop relations, owners from outbound `owned_by` edges, and only `depends_on`, `consumes`, or `subscribes_to` as dependency views.
- **Evidence**: Attach evidence linked to returned relations; exclude snapshot-level evidence.

## HOW TO QUERY

1. Discover an entity and retain its `entity_id`, `snapshot_id`, and `project_id`.
2. Pin `get_context` to that snapshot, or select a bounded context listing with tenant, project, or snapshot ID.
3. Use `get_dependencies` for inbound, outbound, or both direct directions. Use tenant/project selectors to resolve ambiguous identities.

## PARAMETERS / CONFIGURATIONS

| Parameters | Contract |
|------------|----------|
| `entity_id`, `snapshot_id`, `project_id`, `tenant_id` | Required selector set for context; `entity_id` required for dependency queries. |
| `direction` | `inbound`, `outbound`, or `both`; dependencies only. |
| `limit`, `offset` | Context page size 1?500; offset 0?10,000. Dependency limit 1?100. |
| `result_limit`, `evidence_limit` | Relations 1?25; evidence per relation 0?20. |

Context and dependency query pages default to **100 items**. Explicit limits retain their existing bounds.

## BEST PRACTICES

REQUIRED: Apply trusted scope and selected snapshot predicates to every entity, project, snapshot, relation, and evidence join.
REQUIRED: Use one read transaction per query so returned facts match current environment pointers at query time.
REQUIRED: Preserve relation direction, provenance, peer identity, and linked evidence in output projections.
REQUIRED: Authorize `memory:read` before repository access and map authorization failures to stable MCP errors.
PROHIBITED: Recurse through dependency paths; reserve transitive traversal for integration-path or impact features.
REQUIRED: Keep successful MCP responses within 256 KiB; mark truncated responses.
REQUIRED: Return `items`, `count`, `limit`, `offset`, and `has_more` for scope listings; use `offset + count` for the next page when `has_more` is true.
PROHIBITED: Treat a supplied tenant selector as authorization or disclose whether an unauthorized tenant owns a UUID.

## TIPS

Use `evidence_limit=0` when only relation identity, direction, provenance, and peer data are needed.


## REFERENCES

- [**ARCHITECTURE.md**](../../adr/ARCHITECTURE.md): Defines application read ports and infrastructure ownership.
- [**TESTS.md**](../../adr/TESTS.md): Defines bounded query and MCP contract test tiers.
- [**MCP.md**](../../adr/MCP.md): Defines tool, tenant, and response boundaries.
- [**entity-discovery.md**](./entity-discovery.md): Supplies active entity discovery and trusted tenant scope.
