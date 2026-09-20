---
doc_type: adr
domain: architecture
stack: [Python 3.12+, FastMCP 4.x, Pydantic 2.x, SQLAlchemy 2.x, PostgreSQL, Alembic, Docker, OpenTelemetry]
node_id: "adr:architecture"
tags: [architecture, design-patterns, folder-structure]
edges:
  - relation: references
    target: "adr:tests"
updated: 2026-09-19
---
# Project Architecture

## OVERVIEW

Use **pragmatic DDD organized by business domain**. FastMCP is the adapter boundary; application use cases coordinate ports; domain code owns invariants; infrastructure implements persistence and runtime integrations.

Keep dependencies inward: `mcp` calls `core/application`, application calls `core/domain`, and infrastructure implements application or domain ports.

## FOLDER STRUCTURE

<folder_structure>
```text
harness-memory/
├── mcp/                         # HTTP/MCP adapters, security, resources, prompts
│   ├── server/                  # FastMCP composition and lifespan
│   ├── tools/                   # One public tool per file
│   ├── resources/               # Bounded memory resource adapters
│   ├── prompts/                 # Deterministic workflow guidance
│   └── services/                # Tenant, authorization, mapping, telemetry
├── core/
│   ├── domain/<domain>/         # Entities, value objects, invariants
│   ├── application/<domain>/    # Contracts, use cases, ports
│   └── infrastructure/
│       ├── postgres/            # Models, repositories, migrations runtime
│       ├── telemetry/           # OpenTelemetry adapters and sanitization
│       └── architecture/       # Dependency-rule validation
├── migrations/                 # Explicit Alembic revisions
└── tests/{unit,integration,e2e}/ # Tests mirror source modules
```
</folder_structure>

## LAYERS

- **MCP adapter**: Authenticate, authorize, validate boundary input, call one application use case, map safe output. Keep SQL and business rules out.
- **Application**: Coordinate handlers, contracts, trusted tenant scope, ports, bounded results, and typed failures.
- **Domain**: Enforce invariants independently of FastMCP, HTTP, SQLAlchemy, PostgreSQL, and Alembic.
- **Infrastructure**: Implement PostgreSQL repositories, migrations inspection, telemetry, and external technical adapters.

## MODULES

| Module | Responsibility | Location |
|--------|----------------|----------|
| Platform foundation | Runtime configuration, schema, migrations, dependency checks. | [platform-foundation.md](../feature/platform-foundation.md) |
| Snapshot publication | Immutable versioned graph publication and active-snapshot switching. | [snapshot-publication.md](../feature/snapshot-publication.md) |
| Entity and relationship reads | Bounded active-snapshot discovery and context queries. | [entity-discovery.md](../feature/entity-discovery.md), [relationship-context.md](../feature/relationship-context.md) |
| Graph analysis | Integration paths and structured change impact. | [integration-paths.md](../feature/integration-paths.md), [impact-analysis.md](../feature/impact-analysis.md) |
| MCP access surface | Resources and deterministic prompts. | [mcp-access-surface.md](../feature/mcp-access-surface.md) |
| Tenant security | Authentication, scopes, isolation, and append-only audit. | [tenant-security.md](../feature/tenant-security.md) |
| Production delivery | Docker, startup schema checks, CI, and telemetry. | [production-delivery.md](../feature/production-delivery.md) |

## PATTERNS

REQUIRED: Put one use case in one `use_cases/<use_case>/` package with `handler.py`, `inbound.py`, and `outbound.py` where applicable.
REQUIRED: Inject repository ports and boundary services through constructors or explicit handler arguments.
REQUIRED: Keep every PostgreSQL query tenant-scoped and active-snapshot bounded when reading graph facts.
PROHIBITED: Import FastMCP, SQLAlchemy, PostgreSQL drivers, or infrastructure implementations into domain code.
PROHIBITED: Let tools mutate graph facts outside complete snapshot publication or let prompts execute business logic.

<code_patterns>
# CORRECT: application depends on a port.
handler = AnalyzeImpactHandler(repository=impact_repository)

# WRONG: application constructs a concrete database adapter.
handler = AnalyzeImpactHandler(repository=PostgresImpactRepository())
</code_patterns>

## INTEGRATIONS

| External Service / Component | Purpose | Connection / Authentication Method |
|------------------------------|---------|-------------------------------------|
| FastMCP 4.x | Tools, resources, prompts, HTTP transport. | In-process client for tests; bearer authentication in production. |
| Pydantic 2.x | Application and MCP boundary contracts. | Frozen, bounded models; trusted context supplied separately. |
| PostgreSQL | Tenant-scoped graph and audit persistence. | SQLAlchemy/psycopg2; explicit transactions and Alembic schema. |
| Alembic | Versioned schema and startup compatibility checks. | CLI migration; runtime checks current revision against head. |
| Docker Compose | Local production-like PostgreSQL, migration, and MCP services. | Environment-configured database and HTTP settings. |
| OpenTelemetry | Bounded tool tracing and request correlation. | API tracer with NoOp fallback; sensitive attributes removed. |

## REFERENCES

- [**README.md**](../README.md): Documentation navigation index.
- [**TESTS.md**](./TESTS.md): Test tiers, commands, and coverage policy.
- [**MCP.md**](./MCP.md): External interface and security boundary.
