---
doc_type: adr
domain: architecture
stack: [Python 3.12+, FastAPI, FastMCP 4.x, Pydantic 2.x, SQLAlchemy 2.x, PostgreSQL, Alembic, Docker, OpenTelemetry]
node_id: "adr:architecture"
tags: [architecture, design-patterns, folder-structure]
edges:
  - relation: references
    target: "adr:api"
  - relation: references
    target: "adr:mcp"
  - relation: references
    target: "adr:tests"
updated: 2026-09-20
---
# Project Architecture

## OVERVIEW

Use **hexagonal architecture with pragmatic DDD** across two application modules: `api/` provides the REST management interface and `mcp/` provides the MCP interface. Both depend inward on application/domain code and reuse `core/` for shared business capabilities and PostgreSQL infrastructure.

Keep transport concerns at module boundaries. Domain rules remain independent from FastAPI, FastMCP, SQLAlchemy, PostgreSQL, and Alembic. `core/infrastructure/postgres` owns shared persistence adapters; `migrations/` owns schema revisions.

## GLOBAL MODULE MAP

| Module | Responsibility | Architecture detail |
|--------|----------------|--------------------|
| API | User and MCP-token management over FastAPI, including health and OpenAPI endpoints. | [API.md](./API.md) |
| MCP | Tools, resources, prompts, and authenticated MCP transport. | [MCP.md](./MCP.md) |
| Core | Shared domain/application capabilities and PostgreSQL models, repositories, and runtime. | [Platform foundation](../feature/core/platform-foundation.md), [snapshot publication](../feature/core/snapshot-publication.md) |
| Delivery | Project-wide containers, migration/startup checks, CI, and telemetry. | [Production delivery](../feature/core/production-delivery.md) |

## TOP-LEVEL STRUCTURE

```text
harness-memory/
├── api/                 # FastAPI adapter, API application/domain, composition root
├── mcp/                 # FastMCP adapter, transport security, runtime
├── core/                # Shared application/domain and infrastructure
├── migrations/          # Alembic revisions for shared PostgreSQL schema
├── tests/               # unit/, integration/, e2e/ mirroring source modules
└── docs/                # ADRs and feature documentation by owning module
```

## DEPENDENCY RULES

- **Inbound adapters**: `api/` and `mcp/` validate transport input, invoke application services/use cases, and map safe output.
- **Application**: Coordinate use cases, contracts, ports, transactions, and typed failures without depending on transport or persistence implementations.
- **Domain**: Enforce business invariants without framework or database imports.
- **Shared infrastructure**: `core/infrastructure/postgres` implements persistence ports for API, MCP, and core application behavior.
- **Migrations**: `migrations/versions/` describes schema changes; runtime startup verifies compatibility rather than migrating implicitly.

REQUIRED: Inject repository ports and boundary services through constructors or explicit handler arguments.
REQUIRED: Keep API PostgreSQL adapters in `core/infrastructure/postgres`; keep SQLAlchemy out of `api/domain` and `api/application`.
REQUIRED: Verify API-issued MCP tokens by stored digest, active lifetime, and owning user.
REQUIRED: Keep graph queries tenant-scoped and active-snapshot bounded.
PROHIBITED: Import FastAPI, FastMCP, SQLAlchemy, PostgreSQL drivers, or infrastructure implementations into domain code.
PROHIBITED: Let prompts execute business logic or MCP tools mutate graph facts outside complete snapshot publication.

## DOCUMENT MAP

```mermaid
graph TD
    ARCH["Project Architecture"] -->|references| API["API Architecture"]
    ARCH -->|references| MCP["MCP Interface"]
    ARCH -->|references| TESTS["Testing Protocol"]
    click API "./API.md"
    click MCP "./MCP.md"
    click TESTS "./TESTS.md"
```

## REFERENCES

- [**API.md**](./API.md): FastAPI module boundaries, persistence reuse, and token handoff to MCP.
- [**MCP.md**](./MCP.md): MCP components, transport, and security boundary.
- [**TESTS.md**](./TESTS.md): Test tiers, commands, and coverage policy.
- [**README.md**](../README.md): Documentation navigation index.
