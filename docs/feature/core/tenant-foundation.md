---
doc_type: feature
domain: tenant_foundation
stack: [Python 3.12+, SQLAlchemy 2.x, PostgreSQL, Alembic]
node_id: "feature:tenant-foundation"
tags: [tenant, uuid, foundation, persistence, migrations]
edges:
  - relation: implements
    target: "adr:architecture"
  - relation: tested_by
    target: "adr:tests"
  - relation: depends_on
    target: "feature:platform-foundation"
  - relation: references
    target: "adr:security"
updated: 2026-09-26
---
# Tenant Foundation
Provide first-class tenant persistence, strict UUID foreign keys, deterministic legacy slug compatibility, and isolated provisioning savepoints.

```graph
{"node_id":"feature:tenant-foundation","domain":"tenant_foundation","implements":["adr:architecture"],"tested_by":["adr:tests"],"entrypoints":["core/infrastructure/postgres/models/tenant.py"],"registration_files":["core/infrastructure/postgres/models/__init__.py"],"reference_files":["core/infrastructure/postgres/models/tenant_id.py","core/infrastructure/postgres/models/tenant_uuid.py"],"code_files":["core/infrastructure/postgres/repositories/api_user_repository.py","migrations/versions/010_tenant_foundation_forward.py","migrations/versions/001_foundation.py","core/infrastructure/postgres/models/project.py"],"test_files":["tests/unit/core/infrastructure/postgres/migrations/test_tenant_foundation_forward.py","tests/unit/core/infrastructure/postgres/models/test_tenant_id.py","tests/unit/core/infrastructure/postgres/models/test_tenant_schema.py","tests/unit/core/infrastructure/postgres/models/test_tenant_uuid.py","tests/unit/core/infrastructure/postgres/repositories/test_api_user_repository.py","tests/unit/core/infrastructure/postgres/migrations/test_foundation_key_uniqueness.py"],"knowledge":{"schema_version":1,"entities":[{"id":"capability:persist-tenant-identity","type":"capability","label":"Persist tenant identity","definition":"Store tenant records and enforce tenant ownership through UUID foreign keys.","aliases":[]},{"id":"rule:strict-tenant-identity","type":"rule","label":"Strict tenant identity","definition":"Reject blank tenant identifiers and map supported legacy slugs deterministically.","aliases":[]},{"id":"contract:tenant-id-mapping","type":"contract","label":"Tenant ID mapping","definition":"Convert UUID values or legacy slug strings to the database UUID representation.","aliases":[]}],"claims":[{"id":"claim:tenant-id-coercion","subject":"capability:persist-tenant-identity","relation":"constrained_by","object":"rule:strict-tenant-identity","statement":"TenantId rejects blank strings, accepts UUID values, and maps valid legacy slugs with UUID5.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"core/infrastructure/postgres/models/tenant_id.py","locator":"TenantId.bind_processor","snapshot":null}],"derived_from":[],"gap":null},{"id":"claim:tenant-id-mapping-contract","subject":"capability:persist-tenant-identity","relation":"exposes","object":"contract:tenant-id-mapping","statement":"TenantId binds UUID values and valid slugs to UUID columns and rejects other string formats.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"core/infrastructure/postgres/models/tenant_id.py","locator":"TenantId.bind_processor","snapshot":null}],"derived_from":[],"gap":null},{"id":"claim:savepoint-tenant-provisioning","subject":"capability:persist-tenant-identity","relation":null,"object":null,"statement":"ApiUserRepository provisions a missing tenant inside a nested transaction and catches duplicate-tenant failures without aborting the outer transaction.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"core/infrastructure/postgres/repositories/api_user_repository.py","locator":"ApiUserRepository._ensure_tenant","snapshot":null}],"derived_from":[],"gap":null},{"id":"claim:global-tenant-project-keys","subject":"capability:persist-tenant-identity","relation":null,"object":null,"statement":"Fresh schemas enforce globally unique tenant keys and globally unique project keys. The project composite constraint remains available for tenant-scoped upserts. Editing revision 001 does not update databases where it has already run.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"migrations/versions/001_foundation.py","locator":"upgrade","snapshot":null},{"kind":"code","source":"core/infrastructure/postgres/models/project.py","locator":"Project.__table_args__","snapshot":null}],"derived_from":[],"gap":null}]}}
```

## OVERVIEW

The Tenant Foundation establishes first-class multi-tenancy in PostgreSQL. It promotes tenant identity from a loose string into a dedicated `tenants` table with strict UUID primary and foreign keys, transparent slug-to-UUID5 mapping, and savepoint-isolated database provisioning.

## FOLDER STRUCTURE

```text
core/infrastructure/postgres/
├── models/                   # Tenant model, TenantId type decorator, TenantUUID value object
├── repositories/             # ApiUserRepository with nested savepoint tenant provisioning
└── migrations/versions/      # 010_tenant_foundation_forward schema revision
tests/unit/core/infrastructure/postgres/
├── models/                   # Unit tests for TenantId and TenantUUID behaviors
├── repositories/             # Concurrency and savepoint tests for ApiUserRepository
└── migrations/               # Forward migration tests verifying foreign keys
```

## MAIN CONCEPTS / COMPONENTS

- **Tenant Model**: Backed by `tenants` table. Enforces non-empty string `key` with unique constraint `uq_tenants_key`, valid status constraint `ck_tenants_status_valid` (`active` or `disabled`), and JSON object validator `ck_tenants_metadata_object`.
- **Global Keys**: Fresh schemas enforce unique tenant keys (`uq_tenants_key`) and project keys across all tenants (`uq_projects_key`). Preserve `uq_projects_tenant_key` for existing tenant-scoped upserts. Revision 001 is edited in place; databases that already applied it are unchanged.
- **TenantId SQLAlchemy Type Decorator**: Subclasses `Uuid(as_uuid=True)`. Normalizes and validates incoming values: rejects empty strings or whitespace; passes existing UUID objects directly; deterministically converts valid alphanumeric slugs using `uuid5(NAMESPACE_DNS, slug)`.
- **TenantUUID Value Object**: Subclasses Python's standard `UUID`. Overrides `__eq__` to match valid string UUIDs and legacy slugs, allowing backward-compatible equality comparisons in domain services and test suites.
- **Savepoint-Isolated Provisioning**: In `ApiUserRepository.add()`, tenant insertion runs inside `session.begin_nested()`. Concurrent attempts to register the same tenant catch `IntegrityError` safely and roll back only the inner savepoint, leaving the outer transaction active.
- **Migration 010 (Forward Foundation)**: Adds foreign key constraints referencing `tenants.id` across all tables: `projects`, `snapshots`, `entities`, `relations`, `evidence`, `api_users`, `api_service_accounts`, `environments`, and `knowledge_publications`.

## HOW TO MANAGE TENANTS

### Prerequisites
1. PostgreSQL upgraded to migration `010_tenant_foundation_forward`.
2. Active SQLAlchemy session bound to target engine.

### Steps
1. Use `TenantId` type on all model columns representing tenant boundaries.
2. Rely on `ApiUserRepository` or explicit provisioning with nested savepoints.

```python
# CORRECT: Safe tenant provisioning using nested savepoint
def ensure_tenant(session, tenant_id: UUID, tenant_name: str) -> None:
    try:
        with session.begin_nested():
            tenant = Tenant(
                id=tenant_id,
                key=f"user-{tenant_id}",
                name=tenant_name,
                status="active",
            )
            session.add(tenant)
            session.flush()
    except IntegrityError:
        pass  # Tenant already provisioned by concurrent transaction


```

## PARAMETERS / CONFIGURATIONS

| Column / Constraint | Type / Value | Required | Description |
|---------------------|--------------|----------|-------------|
| `id` | `UUID` (PK) | Yes | Unique tenant primary key. Generated via `uuid4()` by default. |
| `key` | `VARCHAR(255)` | Yes | Unique human-readable key (`uq_tenants_key`). Non-empty string. |
| `name` | `VARCHAR(255)` | Yes | Display name of the tenant organization. |
| `status` | `VARCHAR(32)` | Yes | Status enum: `active` or `disabled`. Default: `active`. |
| `metadata` | `JSON_OBJECT` | Yes | JSON object with tenant metadata. Default: `{}`. |
| `created_at` | `TIMESTAMPTZ` | Yes | Timestamp of creation. Default: `func.now()`. |
| `updated_at` | `TIMESTAMPTZ` | Yes | Timestamp of last modification. Default: `func.now()`. |

## BEST PRACTICES

REQUIRED: Define all tenant foreign key references as `TenantId(as_uuid=True)` targeting `tenants.id`.
REQUIRED: Wrap automatic tenant creation inside `session.begin_nested()` to protect the outer transaction from rollback aborts.
REQUIRED: Reject blank or empty string values in `TenantId` processors with a `ValueError`.
REQUIRED: Preserve deterministic `uuid5(NAMESPACE_DNS, slug)` mapping for legacy string slugs.
PROHIBITED: Defining models with unconstrained string columns for tenant identity.
PROHIBITED: Catching `IntegrityError` without a savepoint during tenant provisioning.
PROHIBITED: Inserting tenants with status other than `active` or `disabled`.

## TIPS

When writing tests with legacy tenant strings, pass the string directly to queries; the `TenantId` processor automatically generates the deterministic `TenantUUID` representation.


## REFERENCES

- [**ARCHITECTURE.md**](../../adr/ARCHITECTURE.md): Architectural boundaries and PostgreSQL infrastructure rules.
- [**TESTS.md**](../../adr/TESTS.md): Migration and PostgreSQL integration test protocols.
- [**platform-foundation.md**](./platform-foundation.md): Foundation schema, tables, and Alembic CLI operations.
- [**SECURITY.md**](../../adr/SECURITY.md): Multi-tenant isolation and security audit policies.
