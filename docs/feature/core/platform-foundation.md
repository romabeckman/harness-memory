---
doc_type: feature
domain: platform_foundation
stack: [Python 3.12+, FastMCP 4.x, Pydantic 2.x, SQLAlchemy 2.x, PostgreSQL, Alembic]
node_id: "feature:platform-foundation"
tags: [platform, foundation, persistence, migrations]
edges:
  - relation: implements
    target: "adr:architecture"
  - relation: tested_by
    target: "adr:tests"
  - relation: references
    target: "adr:mcp"
  - relation: references
    target: "feature:tenant-foundation"
updated: 2026-09-26
---
# Platform Foundation
Provide the runnable DDD structure, PostgreSQL schema, migration boundary, and MCP registration base for Harness Memory.

```graph
{"node_id":"feature:platform-foundation","domain":"platform_foundation","implements":["adr:architecture"],"tested_by":["adr:tests"],"entrypoints":["harness_memory_mcp/cli.py","harness_memory_mcp/server/app.py"],"registration_files":["harness_memory_mcp/server/factory.py","pyproject.toml"],"reference_files":["core/infrastructure/postgres/engine_factory.py","core/infrastructure/architecture/validator.py"],"code_files":["harness_memory_mcp/config.py","harness_memory_mcp/migration_cli.py","harness_memory_mcp/migration_mode.py","core/infrastructure/architecture/rules.py","core/infrastructure/architecture/violation.py","core/infrastructure/postgres/alembic_runtime.py","core/infrastructure/postgres/config.py","core/infrastructure/postgres/create_postgres_engine.py","core/infrastructure/postgres/inspect_migration_status.py","core/infrastructure/postgres/migrations.py","core/infrastructure/postgres/migrations_status.py","core/infrastructure/postgres/upgrade_database.py","core/infrastructure/postgres/models/base.py","core/infrastructure/postgres/models/entity.py","core/infrastructure/postgres/models/evidence.py","core/infrastructure/postgres/models/foundation_id.py","core/infrastructure/postgres/models/metadata.py","core/infrastructure/postgres/models/metadata_type.py","core/infrastructure/postgres/models/project.py","core/infrastructure/postgres/models/relation.py","core/infrastructure/postgres/models/snapshot.py","core/infrastructure/postgres/models/types.py","migrations/env.py","migrations/versions/001_foundation.py","migrations/versions/003_default_workspace.py","migrations/versions/002_indexes_and_relationships.py"],"test_files":["tests/unit/architecture/test_rules.py","tests/unit/core/infrastructure/postgres/test_config.py","tests/unit/core/infrastructure/postgres/test_engine_factory.py","tests/unit/core/infrastructure/postgres/test_migrations.py","tests/unit/core/infrastructure/postgres/models/test_schema.py","tests/unit/core/infrastructure/postgres/models/test_types.py","tests/unit/mcp/test_cli.py","tests/unit/mcp/test_config.py","tests/unit/mcp/server/test_factory.py","tests/unit/core/infrastructure/postgres/migrations/test_default_workspace.py","tests/unit/core/infrastructure/postgres/migrations/test_consolidated_migrations.py","tests/integration/migrations/test_initial_foundation.py","tests/integration/migrations/test_default_workspace.py","tests/integration/migrations/test_service_accounts.py","tests/e2e/mcp/test_catalog.py","tests/e2e/mcp/test_import.py"],"knowledge":{"schema_version":1,"entities":[{"id":"capability:manage-platform-schema","type":"capability","label":"Manage platform schema","definition":"Configure PostgreSQL persistence and apply versioned Alembic revisions.","aliases":[]},{"id":"rule:explicit-migrations","type":"rule","label":"Explicit migrations","definition":"Run schema upgrades through the migration command rather than server construction.","aliases":[]},{"id":"contract:migration-status","type":"contract","label":"Migration status","definition":"Inspect current and head revisions without mutating the database.","aliases":[]}],"claims":[{"id":"claim:explicit-schema-upgrade","subject":"capability:manage-platform-schema","relation":"constrained_by","object":"rule:explicit-migrations","statement":"The migration CLI dispatches schema upgrades to Alembic; server construction composes the MCP runtime without calling the upgrade operation.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"harness_memory_mcp/migration_cli.py","locator":"MigrationCLI.dispatch","snapshot":null},{"kind":"code","source":"core/infrastructure/postgres/upgrade_database.py","locator":"UpgradeDatabase.execute","snapshot":null},{"kind":"code","source":"harness_memory_mcp/server/factory.py","locator":"create_mcp_server composition","snapshot":null}],"derived_from":[],"gap":null},{"id":"claim:read-only-migration-status","subject":"capability:manage-platform-schema","relation":"exposes","object":"contract:migration-status","statement":"The migration status path reports current and head revisions without issuing an upgrade.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"core/infrastructure/postgres/inspect_migration_status.py","locator":"migration status inspection","snapshot":null}],"derived_from":[],"gap":null},{"id":"claim:consolidated-schema-history","subject":"capability:manage-platform-schema","relation":null,"object":null,"statement":"Fresh databases use 001 for final tables and table constraints, 002 for indexes and foreign keys, and 003 for default workspace data. Historical installations require a separate transition because revision numbers are reused.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"migrations/versions/001_foundation.py","locator":"upgrade and downgrade","snapshot":null},{"kind":"code","source":"migrations/versions/002_indexes_and_relationships.py","locator":"upgrade and downgrade","snapshot":null},{"kind":"code","source":"migrations/versions/003_default_workspace.py","locator":"upgrade and downgrade","snapshot":null}],"derived_from":[],"gap":null}]}}
```

## OVERVIEW

Use **pragmatic DDD organized by business domain**. Keep FastMCP at the adapter edge, PostgreSQL and Alembic in infrastructure, and dependencies pointed inward.

## FOLDER STRUCTURE

```text
harness_memory_mcp/                          # Runtime, CLI, and transport adapters
core/application/             # Feature use cases and ports
core/domain/                  # Business invariants and value objects
core/infrastructure/postgres/ # Database configuration and adapters
migrations/                   # Versioned schema revisions
tests/{unit,integration,e2e}/ # Mirrored verification tiers
```

## MAIN CONCEPTS / COMPONENTS

- **Runtime boundary**: Build the FastMCP server without database connections, migrations, or transport startup.
- **Persistence boundary**: Keep five tenant-scoped foundation tables: projects, snapshots, entities, relations, and evidence.
- **Snapshot storage**: Create normalized graph facts and snapshot header fields directly; no redundant snapshot payload column is created.
- **Migration boundary**: Use explicit Alembic revisions through the CLI; keep startup schema creation disabled.
- **Default workspace seed**: Revision 003 inserts the default tenant, `Admin` API user, `Default Project`, and its production environment. Seed downgrade retains referenced or modified workspace rows.
- **Service accounts**: Revision 001 creates tenant-bound API service accounts and token ownership/scopes columns; revision 002 installs their foreign keys.
- **Dependency boundary**: Let `mcp` call application code, application code use domain rules and ports, and infrastructure implement ports.

## MIGRATION LAYOUT

- **001** creates all 12 final tables, columns, primary keys, unique constraints, and check constraints.
- **002** creates 25 foreign keys and 34 explicit indexes, including PostgreSQL trigram search indexes.
- **003** loads the default workspace data.

REQUIRED: Use this consolidated history only for a fresh database. Old revision numbers overlap the new history; do not stamp or upgrade an existing installation with these files. Preserve existing databases and plan a separate, verified transition when needed.

## HOW TO OPERATE

1. Set `MCP_HOST` and `MCP_PORT`; keep `DATABASE_URL` optional until database work starts.
2. Run `harness-memory migrate` to upgrade the PostgreSQL schema through Alembic head and apply the default workspace seed.
3. Run `harness-memory migrate --status` to inspect current and head revisions without mutation.
4. Add each feature under its domain packages and mirror its tests under `unit`, `integration`, and `e2e`.

## PARAMETERS / CONFIGURATIONS

| Name | Type | Required | Description | Default |
|------|------|----------|-------------|---------|
| `MCP_HOST` | string | No | Non-empty MCP bind host. | `127.0.0.1` |
| `MCP_PORT` | integer | No | Port from 1 through 65535. | `8000` |
| `DATABASE_URL` | secret URL | Database commands only | PostgreSQL `psycopg2` connection URL. | unset |

## BEST PRACTICES

REQUIRED: Keep tenant, project, and snapshot ownership in composite PostgreSQL constraints.
REQUIRED: Keep ORM models in infrastructure and map future domain objects explicitly.
REQUIRED: Use the seeded user's UUID as the default project's tenant identity.
REQUIRED: Redact credentials and connection details from migration diagnostics.
PROHIBITED: Run migrations or create schema during MCP server construction.
PROHIBITED: Treat the seeded `Admin` identity as a privileged role or assume it has an API token.
PROHIBITED: Import FastMCP, SQLAlchemy, or PostgreSQL drivers into domain code.

## TIPS

Use `--status` before an upgrade when diagnosing a deployment database; it performs read-only revision inspection.


## REFERENCES

- [**ARCHITECTURE.md**](../../adr/ARCHITECTURE.md): Defines layer ownership and dependency direction.
- [**TESTS.md**](../../adr/TESTS.md): Defines test tiers and coverage policy.
- [**MCP.md**](../../adr/MCP.md): Defines server and adapter boundaries.
- [**tenant-foundation.md**](./tenant-foundation.md): Establishes first-class tenant records, UUID foreign keys, and isolated provisioning.
