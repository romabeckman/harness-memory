![Harness Memory](docs/assets/harness-memory-banner.png)

# Harness Memory

**Harness Memory** is an open-source MCP server for sharing structured engineering knowledge across software projects.

It gives AI agents and engineering tools organization-level context about projects, services, APIs, events, teams, dependencies, ownership, and change impact — instead of limiting them to the repository currently in context.

> A repository explains itself. Harness Memory helps explain how repositories relate to each other.

## Why Harness Memory?

Development agents are usually effective inside a single codebase, but cross-project questions are harder:

- Which services consume this API?
- What depends on this library or contract?
- How does Project A integrate with Service B?
- Which projects may be affected by this change?
- Who owns this dependency?
- What evidence supports a known relationship?

Harness Memory stores these relationships as structured, versioned knowledge and exposes them through the **Model Context Protocol (MCP)**.

## Core Capabilities

The initial scope focuses on three capabilities:

1. **Publish project knowledge** as immutable, versioned snapshots.
2. **Query relationships** between projects and engineering entities.
3. **Analyze change impact** across project boundaries.

Knowledge can represent entities such as projects, systems, services, APIs, events, libraries, and teams, connected through relationships such as `depends_on`, `consumes`, `provides`, `publishes`, `subscribes_to`, and `owned_by`.

## How It Works

```text
Project / Agent
      │
      │ ProjectKnowledgeSnapshot
      ▼
 Harness Memory MCP
      │
      ├── validate
      ├── version
      ├── persist
      └── activate
      │
      ▼
   PostgreSQL
      │
      ▼
Corporate engineering graph
```

Projects publish complete snapshots rather than directly mutating arbitrary graph nodes and edges. This keeps publication versioned, auditable, and idempotent.

Important relationships can also carry **provenance** and **evidence**, making it possible to understand not only what is known, but where that knowledge came from.

## MCP Interface

The MVP exposes the following tools:

| Tool | Purpose |
| --- | --- |
| `publish_project_snapshot` | Publish and activate a project's knowledge snapshot. |
| `search_entities` | Search known entities by key, name, type, or project. |
| `get_context` | Retrieve bounded context around an entity. |
| `get_dependencies` | Query inbound and outbound dependencies. |
| `find_integration_paths` | Find known paths between engineering entities. |
| `analyze_impact` | Identify direct and indirect impact of a structured change. |

Resources:

```text
memory://entities/{entity_id}
memory://projects/{project_key}
memory://snapshots/{snapshot_id}
```

Prompts:

```text
load_corporate_context
analyze_integration
review_change_impact
```

## Tech Stack

- Python 3.12+
- FastMCP 4.x
- Pydantic
- PostgreSQL 17
- Alembic
- Docker Compose

## Architecture

Harness Memory uses pragmatic Domain-Driven Design. Business rules remain independent from MCP transport and PostgreSQL implementation details.

```text
mcp ────────► core/application ────────► core/domain
                    │
                    ▼
             application ports
                    ▲
                    │
          core/infrastructure
```

Application code is organized by business domain and use case:

```text
core/application/<domain>/
├── use_cases/
│   └── <use_case>/
│       ├── handler.py
│       ├── inbound.py
│       └── outbound.py
├── services/
└── ports/
```

- `handler.py` orchestrates the use case.
- `inbound.py` defines its Pydantic input contract.
- `outbound.py` defines its stable Pydantic result contract.
- Domain objects own business invariants.
- Infrastructure implements persistence and external adapters.

See [`ARCHITECTURE.md`](docs/adr/ARCHITECTURE.md) for detailed architecture and dependency rules.

## Getting Started

### Requirements

- Docker
- Docker Compose
- Python 3.12+ for local development

### Start the services

```bash
docker compose up --build
```

Startup order:

```text
PostgreSQL
    ↓
Alembic migrations
    ↓
MCP server
```

The MCP server is exposed at:

```text
http://localhost:8000
```

### Stop the services

```bash
docker compose down
```

To also remove the local PostgreSQL volume:

```bash
docker compose down -v
```

> This permanently removes the local database data stored by Docker Compose.

The production image runs as `appuser` (UID `10001`). The `migrate` service runs
`alembic upgrade head` before the MCP service accepts traffic. The server checks
that the database revision equals Alembic `head`; it never runs implicit migrations.

## Database Migrations

Schema migrations are managed by Alembic and run automatically before the MCP service starts.

To run migrations manually:

```bash
docker compose run --rm migrate
```

## Development

The default Compose configuration builds the application into the Docker image. After changing Python code, rebuild the MCP service:

```bash
docker compose up -d --build mcp
```

For hot reload, use a development-specific Compose override with a source bind mount and an appropriate Python reload/watch mechanism.

For a local virtual environment:

```bash
python3 -m venv venv
./venv/bin/pip install -e ".[test]"
```

Set `DATABASE_URL` to a PostgreSQL `postgresql+psycopg2://` URL before running
`alembic upgrade head` or `harness-memory migrate`. Read-only migration status is
available with `harness-memory migrate --status`.

Run the test tiers in source order:

```bash
./venv/bin/python -m pytest tests/unit
./venv/bin/python -m pytest tests/integration
./venv/bin/python -m pytest tests/e2e
./venv/bin/python -m pytest --cov=core --cov=mcp --cov-branch --cov-fail-under=80
```

The 80% global branch coverage gate is required in CI. Ruff format and lint must
also pass. Windows virtual environments use `venv\\Scripts\\python.exe` and
`venv\\Scripts\\pip.exe`.

### Authentication and tenancy

Production HTTP mode uses a bearer token verifier configured with `MCP_ISSUER`,
`MCP_JWKS_URI`, `MCP_AUDIENCE`, and `MCP_TENANT_CLAIM`. Every tool request is
bound to the authenticated tenant; tenant identity is never accepted from a tool
payload. Scope checks protect publishing, reads, and impact analysis. Security
audit records keep bounded safe identifiers and optional W3C trace correlation.

### MCP example

After startup, an MCP client can discover the catalog with `tools/list`, then call
`search_entities` with a tenant-scoped query:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {"name": "search_entities", "arguments": {"query": "billing"}}
}
```

## Design Principles

- Keep business logic out of MCP adapters.
- Keep the domain independent from FastMCP, SQLAlchemy, and PostgreSQL drivers.
- Publish versioned snapshots instead of arbitrary graph mutations.
- Preserve evidence and provenance for important relationships.
- Derive impact from known graph relationships rather than LLM guesses.
- Keep the initial graph and infrastructure intentionally small.

## Project Status

Harness Memory is currently under active development. The initial implementation is focused on the MCP interface, snapshot publication, relationship queries, dependency traversal, and cross-project impact analysis.

The project is independent and does not require Harness Kit to operate.

## Contributing

Contributions are welcome.

If you want to propose a feature or architectural change, open an issue or pull request with a clear description of the problem, expected behavior, and relevant tests.

When contributing, preserve the dependency boundaries described in [`ARCHITECTURE.md`](docs/adr/ARCHITECTURE.md), keep one class per file, and add tests in the matching `unit`, `integration`, or `e2e` tree.

## License

Harness Memory is open-source software licensed under the **MIT License**.

See [`LICENSE`](LICENSE) for details.
