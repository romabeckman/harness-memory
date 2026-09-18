---
doc_type: adr
domain: architecture
stack: [Python 3.12+, FastMCP 4.x, Pydantic, PostgreSQL, Alembic]
node_id: "adr:architecture"
tags: [architecture, design-patterns, folder-structure]
edges:
  - relation: references
    target: "adr:tests"
updated: 2026-09-17
---
# Project Architecture

## OVERVIEW

Use **pragmatic DDD organized by business domain**. FastMCP is an external adapter; application modules expose use cases; domain modules own business rules; infrastructure implements persistence.

Dependency flow:

`mcp → core/application → core/domain`

`core/infrastructure → application/domain ports`

The application layer is grouped by `<domain>` so each business capability keeps its use cases, contracts, ports, and application services together.

## FOLDER STRUCTURE

```text
<project-root-folder>/
├── pyproject.toml
├── mcp/                            # External adapter / transport boundary.
│   ├── server/                     # FastMCP registration and runtime.
│   ├── tools/                      # Public MCP tools; call application handlers.
│   ├── services/                   # Auth, tenant context and response mapping.
│   ├── config.py
│   └── cli.py
│
├── core/
│   ├── domain/
│   │   └── <domain>/               # Business model for one bounded capability.
│   │       ├── entities/
│   │       ├── value_objects/
│   │       ├── services/           # Pure domain services when behavior spans entities.
│   │       └── ports/              # Domain-owned interfaces when required by domain rules.
│   │
│   ├── application/
│   │   └── <domain>/
│   │       ├── use_cases/
│   │       │   ├── handler.py      # Executes/orchestrates the use case.
│   │       │   ├── inbound.py      # Pydantic input contracts.
│   │       │   └── outbound.py     # Pydantic output contracts.
│   │       ├── services/           # Reusable application orchestration.
│   │       └── ports/              # Repository/gateway interfaces required by application.
│   │
│   └── infrastructure/
│       └── postgres/
│           ├── config.py           # PostgreSQL configuration.
│           ├── models/             # Database models.
│           └── repositories/       # Implement application/domain ports.
│
├── migrations/                     # Alembic migrations.
└── tests/
    ├── unit/
    ├── integration/
    └── e2e/
```

When a domain has several operations, create one package per use case:

```text
core/application/<domain>/use_cases/
├── publish_snapshot/{handler.py,inbound.py,outbound.py}
├── query_knowledge/{handler.py,inbound.py,outbound.py}
└── calculate_impact/{handler.py,inbound.py,outbound.py}
```

## LAYERS

### MCP

Transport adapter only: parse context, call an application handler, map failures, and return the outbound contract.

PROHIBITED: business rules, SQL, or direct repository usage inside MCP tools.

### Application

Coordinates business operations: receive `inbound`, load state through ports, invoke domain behavior, coordinate boundaries, and return `outbound`.

`services/` contains orchestration reused by multiple use cases, not generic helpers.

### Domain

Contains business behavior independent of FastMCP, SQLAlchemy, PostgreSQL, or HTTP. Entities own identity and behavior; value objects model concepts; domain services handle rules spanning multiple domain objects.

### Infrastructure

Implements persistence and technical adapters. PostgreSQL models must not become domain entities.

## USE-CASE CONTRACTS

### `inbound.py`

Defines application input schemas with Pydantic and validates shape and primitive constraints.

### `handler.py`

Contains the application operation. Prefer explicit constructor dependencies rather than global repository access.

### `outbound.py`

Defines the stable result exposed to adapters. Do not leak ORM or persistence structures. Pydantic contracts belong to the **application boundary**; convert them to domain objects before business decisions.

REQUIRED: Pydantic validates transport/application contracts.
REQUIRED: domain objects enforce business invariants.
PROHIBITED: using Pydantic validation as a replacement for domain rules.

## PORTS AND DEPENDENCIES

Put a port where the abstraction is consumed:

- `core/application/<domain>/ports/`: repositories, transaction boundaries, external gateways required by use cases.
- `core/domain/<domain>/ports/`: only interfaces genuinely required by domain behavior.
- `core/infrastructure/...`: concrete implementations.

Example: `mcp/tools/publish.py` → `application/knowledge/use_cases/publish_snapshot/handler.py` → `domain/knowledge/`, using a repository port implemented by `infrastructure/postgres/knowledge/`.

REQUIRED: dependencies point inward.
PROHIBITED: `domain` importing `application`, `infrastructure`, FastMCP, SQLAlchemy, or PostgreSQL drivers.
PROHIBITED: `application` importing FastMCP or concrete PostgreSQL repositories.

## DATA AND PERSISTENCE

- Keep persistence models under `core/infrastructure/postgres/<domain>/models/`.
- Keep repository implementations under `.../repositories/`.
- Map persistence models to domain objects explicitly.
- Use transactions for snapshot activation/replacement.
- Keep immutable, versioned and idempotent snapshots.
- Preserve provenance and tenant isolation.
- Store bounded JSONB metadata only after validation.
- Version public snapshot contracts with `schema_version` and reject unsupported versions.

## TESTING BOUNDARIES

- **Unit/domain**: entities, value objects and domain services without infrastructure.
- **Unit/application**: handlers using fake/mock ports.
- **Integration**: PostgreSQL repository implementations and transactions.
- **MCP contract**: adapter input/output and mapping to application handlers.

REQUIRED: test valid, invalid, incomplete and version-incompatible inbound payloads.
REQUIRED: test domain invariants separately from Pydantic contract validation.

## INTEGRATIONS

| Component | Responsibility |
|---|---|
| FastMCP 4.x | External MCP transport and tool/resource exposure. |
| Pydantic | Application inbound/outbound contracts. |
| PostgreSQL | Persistent storage. |
| Alembic | Explicit versioned database migrations. |
| OpenTelemetry | Optional operational telemetry where useful. |

## REFERENCES

- [**README.md**](../README.md): Documentation navigation index.
- [**TESTS.md**](./TESTS.md): Test strategy and coverage requirements.
