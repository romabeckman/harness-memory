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
updated: 2026-09-24
---
# Relationship Context
Return bounded context for selected entities and direct dependency views for one entity.

```graph
{
  "node_id": "feature:relationship-context",
  "domain": "relationship_context",
  "implements": ["adr:architecture"],
  "tested_by": ["adr:tests"],
  "entrypoints": ["harness_memory_mcp/tools/get_context.py", "harness_memory_mcp/tools/get_dependencies.py"],
  "registration_files": ["harness_memory_mcp/server/factory.py"],
  "reference_files": [
  ],
  "code_files": [
    "harness_memory_mcp/services/tenant_context.py",
    "harness_memory_mcp/services/relationship_response_mapper.py",
    "core/application/entity_discovery/contracts/tenant_scope.py",
    "core/application/relationship_context/contracts/entity_context_item.py",
    "core/application/relationship_context/contracts/project_context_item.py",
    "core/application/relationship_context/contracts/evidence_view.py",
    "core/application/relationship_context/contracts/relation_view.py",
    "core/application/relationship_context/contracts/dependency_view.py",
    "core/application/relationship_context/types/dependency_relation_type.py",
    "core/application/relationship_context/types/relationship_direction.py",
    "core/application/relationship_context/types/relationship_query_bounds.py",
    "core/application/relationship_context/ports/relationship_query_repository.py",
    "core/application/relationship_context/errors/entity_context_not_found.py",
    "core/application/relationship_context/errors/relationship_query_failure.py",
    "core/application/relationship_context/use_cases/get_context/inbound.py",
    "core/application/relationship_context/use_cases/get_context/handler.py",
    "core/application/relationship_context/use_cases/get_context/outbound.py",
    "core/application/relationship_context/use_cases/get_context/page.py",
    "core/application/relationship_context/use_cases/get_dependencies/inbound.py",
    "core/application/relationship_context/use_cases/get_dependencies/handler.py",
    "core/application/relationship_context/use_cases/get_dependencies/outbound.py",
    "core/infrastructure/postgres/repositories/relationship_query_repository.py"
  ],
  "test_files": [
    "tests/unit/core/application/relationship_context/contracts/test_contracts.py",
    "tests/unit/core/application/relationship_context/ports/test_relationship_query_repository.py",
    "tests/unit/core/application/relationship_context/use_cases/test_get_context.py",
    "tests/unit/core/application/relationship_context/use_cases/test_get_dependencies.py",
    "tests/unit/mcp/services/test_relationship_response_mapper.py",
    "tests/unit/mcp/server/test_relationship_factory.py",
    "tests/unit/mcp/tools/test_get_context.py",
    "tests/unit/mcp/tools/test_get_dependencies.py",
    "tests/integration/core/infrastructure/postgres/repositories/test_relationship_context_query.py",
    "tests/integration/core/infrastructure/postgres/repositories/test_relationship_query_plans.py",
    "tests/e2e/mcp/test_relationship_queries.py"
  ]
}
```

## OVERVIEW

`get_context` and `get_dependencies` are read-only queries over trusted scope. They expose direct relations, owners, dependency peers, provenance, and linked evidence within request bounds. A scope-only `get_context` call returns a page of current entity contexts; `snapshot_id` can select a historical snapshot.

## FOLDER STRUCTURE

```text
harness_memory_mcp/tools/                                  # Thin context and dependency adapters
harness_memory_mcp/services/                               # Tenant and safe response mapping
core/application/relationship_context/      # Contracts, ports, and handlers
core/infrastructure/postgres/repositories/  # Active-snapshot relationship reads
tests/{unit,integration,e2e}/               # Contract, repository, and MCP tests
```

## MAIN CONCEPTS / COMPONENTS

- **Pinned context**: Resolve a stable identity or row UUID in the requested immutable snapshot, or current active state when no snapshot is supplied. Apply trusted scope and reject ambiguous canonical identities.
- **Scope listing**: Supply `snapshot_id`, `project_id`, or `tenant_id` without `entity_id` to receive a bounded page. Sort by snapshot creation time, revision, then entity creation time, newest first; use IDs to break ties. Keep current snapshots as the default.
- **Direct relation**: Return one-hop relations; derive owners from outbound `owned_by` relations targeting teams.
- **Dependency relation**: Limit dependency views to `depends_on`, `consumes`, and `subscribes_to`; support inbound, outbound, and both directions.
- **Evidence**: Attach only evidence linked to returned relations; exclude snapshot-level evidence from entity context.

## HOW TO QUERY

1. Discover an entity with `search_entities` and retain its `snapshot_id` and `occurrence_id`.
2. Call `get_context` with the entity ID for one context, optionally pinned by `snapshot_id`. Supply only `snapshot_id`, `project_id`, or `tenant_id` to list matching contexts, newest first.
3. Call `get_dependencies` with `inbound`, `outbound`, or `both` for one-hop dependency views.
4. Use `tenant_id` and `project_id` to narrow ambiguous global identities. An ambiguous canonical identity returns `AMBIGUOUS_ENTITY`.

## PARAMETERS / CONFIGURATIONS

| Name | Type | Required | Description | Default |
|------|------|----------|-------------|---------|
| `entity_id` | UUID | One of four selectors for `get_context`; required for `get_dependencies` | Stable entity identity from discovery; legacy row UUIDs remain accepted. | unset |
| `direction` | enum | No | `inbound`, `outbound`, or `both`; dependencies only. | `both` |
| `tenant_id` / `project_id` | string / UUID | One of four selectors for `get_context` | Narrow resolution or list contexts within a known tenant or project. | unset |
| `snapshot_id` | UUID | One of four selectors for `get_context` | Pin one entity or list contexts in an immutable snapshot, including historical snapshots. | current active |
| `limit` | strict integer | No | Relation bound from 1 through 100. | `25` |
| `evidence_limit` | strict integer | No | Evidence bound per relation from 0 through 20. | `5` |
| `result_limit` | strict integer | No | Contexts per page from 1 through 25 when `entity_id` is absent. | `25` |
| `offset` | strict integer | No | Matching contexts to skip, from 0 through 10,000. | `0` |

## BEST PRACTICES

REQUIRED: Apply trusted scope and selected snapshot predicates to every entity, project, snapshot, relation, and evidence join.
REQUIRED: Use one read transaction per query so returned facts come from one active snapshot.
REQUIRED: Preserve relation direction, provenance, peer identity, and linked evidence in output projections.
REQUIRED: Authorize `memory:read` before repository access and map authorization failures to stable MCP errors.
PROHIBITED: Recurse through dependency paths; reserve transitive traversal for integration-path or impact features.
REQUIRED: Keep successful MCP responses within 256 KiB; mark truncated responses.
REQUIRED: Return `items`, `count`, `limit`, `offset`, and `has_more` for scope listings; use `offset + count` for the next page when `has_more` is true.
PROHIBITED: Treat a supplied tenant selector as authorization or disclose whether an unauthorized tenant owns a UUID.

## TIPS

Use `evidence_limit=0` when only relation identity, direction, provenance, and peer data are needed.

## DOCUMENT MAP

```mermaid
graph TD
    THIS["Relationship Context"] -->|implements| ARCH["Project Architecture"]
    THIS -->|tested_by| TESTS["Testing Protocol"]
    THIS -->|references| MCP["MCP Interface"]
    THIS -->|depends_on| ENTITY["Entity Discovery"]
    click ARCH "../../adr/ARCHITECTURE.md"
    click TESTS "../../adr/TESTS.md"
    click MCP "../../adr/MCP.md"
    click ENTITY "./entity-discovery.md"
```

## REFERENCES

- [**ARCHITECTURE.md**](../../adr/ARCHITECTURE.md): Defines application read ports and infrastructure ownership.
- [**TESTS.md**](../../adr/TESTS.md): Defines bounded query and MCP contract test tiers.
- [**MCP.md**](../../adr/MCP.md): Defines tool, tenant, and response boundaries.
- [**entity-discovery.md**](./entity-discovery.md): Supplies active entity discovery and trusted tenant scope.
