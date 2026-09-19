# Harness Memory — Project Scope

> **Status:** Draft for review  
> **Version:** 0.3  
> **Date:** 2026-09-18  
> **Project:** `harness-memory`  
> **Type:** Corporate Engineering Memory MCP Server  
> **Stack:** Python 3.12+, FastMCP 4.x, Pydantic, PostgreSQL  
> **Architecture:** Pragmatic DDD organized by business domain, with `mcp/` adapters and shared `core/`

---

# 1. IDEA

`harness-memory` is a corporate engineering memory server exposed through MCP.

Its purpose is to maintain shared knowledge about the organization's software ecosystem so AI agents and engineering tools can understand relationships between projects, services, APIs, events, teams, and dependencies.

The main problem it solves is that a development agent usually understands only the repository it is currently working on.

`harness-memory` adds organization-level context.

Example questions:

```text
Which services consume this API?

How does Project A integrate with Service B?

What projects are affected if this contract changes?

Who owns this dependency?

What evidence supports this relationship?
```

---

# 2. PROJECT GOAL

The MVP must provide three capabilities:

```text
1. Publish corporate knowledge from projects.
2. Query relationships between corporate software entities.
3. Analyze cross-project impact of changes.
```

Everything else is secondary.

---

# 3. RELATIONSHIP WITH HARNESS KIT

```text
harness-kit
    │
    ├── project-memory
    │       local repository knowledge
    │
    └── corporate-memory
            MCP client behavior
                │
                ▼
        harness-memory
            corporate knowledge
```

Responsibility boundary:

```text
project-memory
    understands one repository

harness-memory
    understands relationships across repositories
```

`harness-memory` is independent and must not require `harness-kit` to operate.

---

# 4. IMPORTANT DESIGN DECISIONS

## 4.1 PostgreSQL is the database

PostgreSQL is the persistence technology for the project.

It stores:

```text
projects
entities
relations
snapshots
evidence
provenance
ownership
audit information
```

There is no requirement to support multiple database providers in the MVP.

---

## 4.2 Pragmatic DDD

Use DDD organized by business domain. Keep `mcp/` as the external adapter and group shared domain, application, and infrastructure code under `core/`.

Core dependency direction:

```text
mcp/server and mcp/tools
  ↓
core/application/<domain>
  ↓
core/domain/<domain>

core/infrastructure
  → application/domain ports
```

The domain must not depend on FastMCP, HTTP, SQLAlchemy, PostgreSQL drivers, or infrastructure implementations.

---

## 4.3 Snapshot-based publication

Projects publish complete versioned snapshots.

```text
Project
   ↓
ProjectKnowledgeSnapshot
   ↓
publish_project_snapshot
   ↓
PostgreSQL
   ↓
Corporate Graph
```

Agents do not directly create arbitrary nodes and edges.

---

## 4.4 Evidence and provenance

Important relationships must explain where they came from.

Supported provenance kinds:

```text
declared
inferred
observed
manual
```

The MVP focuses primarily on:

```text
declared
manual
```

---

# 5. CORE DOMAIN

## 5.1 Entity types

Initial types:

```text
project
system
service
api
event
library
team
```

## 5.2 Relation types

Initial relations:

```text
part_of
owned_by
provides
consumes
depends_on
publishes
subscribes_to
implements
```

Keep the initial model small.

---

# 6. DOMAIN MODEL

Core concepts:

```text
Project
Entity
Relation
Snapshot
Evidence
Provenance
DependencyPath
Change
ImpactReport
```

The domain layer must not import:

```text
FastMCP
SQLAlchemy
Alembic
PostgreSQL drivers
```

Application contracts and domain boundaries:

```text
core/domain/<domain>/
    entities/
    value_objects/
    services/
    ports/

core/application/<domain>/use_cases/<use_case>/
    handler.py
    inbound.py
    outbound.py
```

Pydantic validates `inbound.py` and `outbound.py` application contracts. Domain entities, value objects, and services enforce business invariants after contract validation. Do not pass persistence models or unvalidated dictionaries into domain behavior.

---

# 7. PROJECT KNOWLEDGE SNAPSHOT

The main write contract is `ProjectKnowledgeSnapshot`.

Example:

```json
{
  "schema_version": "1.0",
  "project": {
    "key": "github.com/company/payments-api",
    "name": "payments-api"
  },
  "revision": "abc123",
  "generated_at": "2026-09-17T12:00:00Z",
  "entities": [],
  "relations": [],
  "evidence": []
}
```

Properties:

```text
immutable
versioned
idempotent
revision-aware
validated before activation
```

Publication flow:

```text
receive
  ↓
validate
  ↓
persist snapshot
  ↓
replace previous active project facts
  ↓
activate new project facts
```

---

# 8. POSTGRESQL MODEL

Initial tables:

```text
projects
snapshots
entities
relations
evidence
```

Suggested structure:

```text
projects
    id
    key
    name
    active_snapshot_id

snapshots
    id
    project_id
    revision
    schema_version
    generated_at
    created_at
    payload_hash

entities
    id
    project_id
    snapshot_id
    entity_type
    entity_key
    name
    metadata JSONB

relations
    id
    snapshot_id
    source_entity_id
    relation_type
    target_entity_id
    provenance_kind
    metadata JSONB

evidence
    id
    snapshot_id
    relation_id nullable
    kind
    content
    source
    metadata JSONB
```

Useful PostgreSQL features:

```text
JSONB
unique constraints
indexes
recursive CTEs
transactions
full-text search
```

Persistence layout:

```text
core/infrastructure/postgres/
    config.py
    models/
    repositories/
```

`models/` maps PostgreSQL tables and JSONB fields. `repositories/` implements application or domain ports, including snapshot activation, entity lookup, graph traversal, tenant filtering, and transaction boundaries. Do not create separate infrastructure `queries/` or `session` modules.

---

# 9. MIGRATIONS

Use Alembic.

Expected commands:

```text
harness-memory migrate
harness-memory migrate --status
```

Requirements:

```text
versioned migrations
upgrade tested in CI
startup schema compatibility check
no implicit production schema creation
```

---

# 10. MCP SERVER

FastMCP is the project interface.

Production:

```text
MCP over HTTP
```

Development/tests:

```text
FastMCP in-process client
```

Expose:

```text
Tools
Resources
Prompts
```

Register the server in `mcp/server/`. Keep one public tool per file under `mcp/tools/`. Use `mcp/services/` for authentication, tenant context, and response mapping.

---

# 11. MCP TOOLS — MVP

## `publish_project_snapshot`

Publishes and activates a complete project snapshot.

Implementation boundary: `mcp/tools/publish_project_snapshot.py` delegates to a domain-grouped application use case with `handler.py`, `inbound.py`, and `outbound.py`.

## `search_entities`

Search entities by:

```text
key
name
type
project
```

## `get_context`

Returns bounded context around an entity:

```text
entity
project
owner
relations
dependencies
evidence
```

## `get_dependencies`

Returns inbound/outbound dependencies.

## `find_integration_paths`

Finds known paths between corporate entities.

Returns:

```text
path
ownership
provenance
evidence
```

## `analyze_impact`

Analyzes the effect of a structured change.

Returns:

```text
direct consumers
indirect consumers
affected projects
affected teams
dependency paths
evidence
unknowns
```

---

# 12. MCP RESOURCES — MVP

```text
memory://entities/{entity_id}
memory://projects/{project_key}
memory://snapshots/{snapshot_id}
```

Optional:

```text
memory://schema/entities
memory://schema/relations
memory://schema/snapshot
```

---

# 13. MCP PROMPTS — MVP

## `load_corporate_context`

Used before planning cross-system work.

## `analyze_integration`

Used when one project needs to integrate with another.

## `review_change_impact`

Used before changing a shared contract.

Prompts guide tool usage but do not contain business logic.

---

# 14. DOMAIN-GROUPED PROJECT STRUCTURE

Keep `mcp/` as the adapter package. Group reusable business code by domain under `core/`.

```text
harness-memory/
├── pyproject.toml
├── alembic.ini
├── mcp/
│   ├── server/                     # FastMCP registration and runtime.
│   ├── tools/                      # One file per public MCP tool.
│   │   ├── publish_project_snapshot.py
│   │   ├── search_entities.py
│   │   ├── get_context.py
│   │   ├── get_dependencies.py
│   │   ├── find_integration_paths.py
│   │   └── analyze_impact.py
│   ├── services/                   # Auth, tenant context, response mapping.
│   ├── config.py
│   └── cli.py
├── core/
│   ├── domain/<domain>/             # Entities, value objects, services, domain ports.
│   ├── application/<domain>/        # Use cases, services, application ports.
│   │   └── use_cases/<use_case>/    # handler.py, inbound.py, outbound.py.
│   └── infrastructure/postgres/
│       ├── config.py
│       ├── models/                  # PostgreSQL models.
│       └── repositories/            # Port implementations and transactions.
├── migrations/                     # Alembic migrations.
└── tests/
    ├── unit/
    ├── integration/
    └── e2e/
```

Responsibilities:

```text
mcp/server and mcp/tools
    FastMCP registration, transport, tool adapters

mcp/services
    authentication, tenant context, response mapping

core/domain/<domain>
    entities, value objects, domain services, invariants

core/application/<domain>
    use-case handlers, inbound/outbound contracts, ports

core/infrastructure/postgres
    configuration, models, repositories, transaction boundaries
```

---

# 15. DEPENDENCY RULES

Allowed:

```text
mcp/server and mcp/tools → core/application/<domain>
core/application/<domain> → core/domain/<domain>
core/infrastructure → application/domain ports
```

Prohibited:

```text
domain → mcp
domain → FastMCP
domain → SQLAlchemy
domain → PostgreSQL

application → FastMCP
application → concrete PostgreSQL repositories
```

---

# 16. AUTHENTICATION

Production MCP requires authentication.

Initial scopes:

```text
memory:read
memory:publish
memory:impact
```

Tenant identity must come from authenticated context.

---

# 17. AUDIT AND OBSERVABILITY

Audit:

```text
snapshot publication
impact analysis
authentication failures
authorization failures
```

Use OpenTelemetry where useful.

Do not build a separate observability subsystem in the MVP.

---

# 18. TEST STRATEGY

## Unit

```text
domain entities
value objects
domain services
application handlers
inbound/outbound contract validation
```

## Integration

```text
PostgreSQL persistence
PostgreSQL models
PostgreSQL repositories
snapshot activation
dependency traversal
transactions
tenant isolation
migrations
```

## MCP

```text
list_tools
call_tool
list_resources
read_resource
list_prompts
get_prompt
```

End-to-end tests cover HTTP MCP transport when production transport is enabled.

---

# 19. MVP DELIVERY PLAN

## Phase 1 — Core

```text
project bootstrap
FastMCP server
PostgreSQL
Alembic
domain model
publish_project_snapshot
search_entities
```

## Phase 2 — Graph queries

```text
get_context
get_dependencies
find_integration_paths
```

## Phase 3 — Impact

```text
analyze_impact
direct impact
transitive impact
affected projects
evidence
```

## Phase 4 — Production

```text
HTTP MCP
authentication
tenant isolation
audit
Docker
CI
```

---

# 20. MVP ACCEPTANCE CRITERIA

1. MCP runs over HTTP.
2. PostgreSQL is the only required database.
3. Alembic migrates an empty database.
4. Projects publish versioned snapshots.
5. Snapshot publication is idempotent.
6. Invalid snapshots are rejected.
7. Entities can be searched.
8. Dependencies can be queried.
9. Transitive dependencies can be traversed.
10. Integration paths can be returned.
11. Change impact can identify direct consumers.
12. Indirect impact is distinguishable.
13. Important relations expose provenance.
14. Evidence is available with the relation context.
15. Tenant boundaries are enforced.
16. Domain code does not depend on FastMCP/PostgreSQL internals.
17. MCP schemas are covered by tests.

---

# 21. NON-GOALS

Not part of MVP:

```text
multiple database providers
Neo4j
S3
MinIO
bucket storage
vector database
RAG
GraphRAG
full repository indexing
runtime graph ingestion
Backstage integration
OpsLevel integration
web UI
generic chatbot
binary evidence storage
```

---

# 22. PUBLIC MCP CATALOG

## Tools

```text
publish_project_snapshot
search_entities
get_context
get_dependencies
find_integration_paths
analyze_impact
```

## Resources

```text
memory://entities/{entity_id}
memory://projects/{project_key}
memory://snapshots/{snapshot_id}
```

## Prompts

```text
load_corporate_context
analyze_integration
review_change_impact
```

---

# 23. KEY PRINCIPLES

```text
PostgreSQL only.

Keep the graph small.

Store bounded evidence in PostgreSQL.

Publish snapshots instead of arbitrary graph mutations.

FastMCP is the external interface.

Use DDD pragmatically, organized by business domain.

Keep `mcp/` as adapter boundary and `core/` as shared business code.

Keep one public MCP tool per file under `mcp/tools/`.

Keep use-case contracts in `inbound.py` and `outbound.py`.

Keep PostgreSQL models under `models/` and port implementations under `repositories/`.

Do not create infrastructure `queries/` or `session` modules.

Impact comes from graph relationships, not LLM guesses.

Avoid infrastructure that is not required by the MVP.
```
