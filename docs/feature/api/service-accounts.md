---
doc_type: feature
domain: api-service-accounts
stack: [Python 3.12+, FastAPI, Pydantic 2.x, SQLAlchemy 2.x, PostgreSQL]
node_id: "feature:api-service-accounts"
tags: [api, service-accounts, tenants, automation]
edges:
  - relation: implements
    target: "adr:architecture"
    read: must
  - relation: references
    target: "adr:api"
    read: must
  - relation: tested_by
    target: "adr:tests"
    read: must
  - relation: references
    target: "feature:api-tokens"
    read: optional
    when: "Read when changing service-account ownership, deletion, or non-expiring MCP credentials."
updated: 2026-09-26
---
# API Service Accounts
Manage tenant-bound non-human identities for automation and MCP client credentials.

```graph
{"node_id":"feature:api-service-accounts","domain":"api-service-accounts","implements":["adr:architecture"],"tested_by":["adr:tests"],"entrypoints":["api/adapters/http/service_account_routes.py"],"registration_files":["api/server/app.py"],"reference_files":["api/application/services/service_account_service.py","api/domain/entities/service_account.py","core/infrastructure/postgres/repositories/api_service_account_repository.py"],"code_files":["api/adapters/http/schemas/service_account_create.py","api/adapters/http/schemas/service_account_update.py","api/adapters/http/schemas/service_account_response.py","api/application/ports/service_account_repository.py","core/infrastructure/postgres/models/api_service_account.py","migrations/versions/001_foundation.py"],"test_files":["tests/unit/api/application/test_service_account_service.py","tests/integration/migrations/test_service_accounts.py","tests/e2e/api/test_user_token_crud.py","tests/unit/core/infrastructure/postgres/models/test_api_service_account.py"],"knowledge":{"schema_version":1,"entities":[{"id":"capability:manage-service-accounts","type":"capability","label":"Manage service accounts","definition":"Create and manage tenant-bound automation identities through REST.","aliases":[]},{"id":"rule:immutable-account-tenant","type":"rule","label":"Immutable account tenant","definition":"Bind a service account to its creation tenant and do not change that binding during rename.","aliases":[]},{"id":"contract:service-account-management","type":"contract","label":"Service-account lifecycle","definition":"REST lifecycle for a tenant-bound account with a normalized name.","aliases":[]}],"claims":[{"id":"claim:account-tenant-binding","subject":"capability:manage-service-accounts","relation":"constrained_by","object":"rule:immutable-account-tenant","statement":"Creation requires tenant_id; update passes only name and the repository changes only the stored name.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"api/application/services/service_account_service.py","locator":"ServiceAccountService.create and update","snapshot":null},{"kind":"code","source":"core/infrastructure/postgres/repositories/api_service_account_repository.py","locator":"ApiServiceAccountRepository.update","snapshot":null}],"derived_from":[],"gap":null},{"id":"claim:account-creation-contract","subject":"capability:manage-service-accounts","relation":"exposes","object":"contract:service-account-management","statement":"Repository creation rejects a missing or disabled tenant when its lookup succeeds; service names are trimmed and blank names rejected.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"core/infrastructure/postgres/repositories/api_service_account_repository.py","locator":"ApiServiceAccountRepository.add: tenant status check","snapshot":null},{"kind":"code","source":"api/application/services/service_account_service.py","locator":"ServiceAccountService._normalize_name","snapshot":null}],"derived_from":[],"gap":null},{"id":"claim:token-owner-dependency","subject":"capability:manage-service-accounts","relation":"depends_on","object":"feature:api-tokens#capability:issue-api-tokens","statement":"TokenService accepts a service-account owner only when that account exists in its repository.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"api/application/services/token_service.py","locator":"TokenService.create: service-account owner lookup","snapshot":null}],"derived_from":[],"gap":null},{"id":"claim:optional-persisted-account-tenant","subject":"capability:manage-service-accounts","relation":null,"object":null,"statement":"The service_accounts tenant_id column accepts NULL in migration 001 and the ORM model. Non-null values retain the tenant foreign key with RESTRICT deletion. REST creation still requires a tenant UUID.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"core/infrastructure/postgres/models/api_service_account.py","locator":"ApiServiceAccount.tenant_id","snapshot":null},{"kind":"code","source":"migrations/versions/001_foundation.py","locator":"upgrade: service_accounts","snapshot":null},{"kind":"code","source":"api/application/services/service_account_service.py","locator":"ServiceAccountService.create","snapshot":null}],"derived_from":[],"gap":null}]}}
```

## OVERVIEW

Expose tenant-bound service-account CRUD under `/v1/service-accounts`. Keep `tenant_id` immutable after creation and use the service account as the owner of automation tokens.

## FOLDER STRUCTURE

```text
api/adapters/http/              # Service-account routes and schemas
api/application/                # Service-account service and repository port
api/domain/                     # Tenant-bound service-account entity
core/infrastructure/postgres/  # SQLAlchemy model and repository adapter
tests/{unit,integration,e2e}/   # Service, migration, and HTTP checks
```

## HTTP CONTRACT

| Method | Path | Success | Rule |
|--------|------|---------|------|
| POST | `/v1/service-accounts` | 201 | Create with name and tenant UUID. |
| GET | `/v1/service-accounts` | 200 | List all accounts or filter by `tenant_id`. |
| GET | `/v1/service-accounts/{account_id}` | 200 | Return one account or 404. |
| PATCH | `/v1/service-accounts/{account_id}` | 200 | Rename account only. |
| DELETE | `/v1/service-accounts/{account_id}` | 204 | Delete account and cascade owned tokens. |

## DOMAIN RULES

REQUIRED: Trim account names and reject empty values.
REQUIRED: Require a UUID `tenant_id` at creation.
REQUIRED: Preserve `tenant_id` for the account lifetime.
REQUIRED: Filter list queries by tenant when `tenant_id` is supplied.
REQUIRED: Delete owned tokens with the service account.
PROHIBITED: Accept `tenant_id` in update semantics.
PROHIBITED: Treat account name as tenant identity.

The update schema forbids extra fields. A client attempting to change `tenant_id` receives validation failure before the application service runs.

## PERSISTENCE

The `service_accounts.tenant_id` column is nullable in migration `001` and the ORM model. A supplied UUID must reference an existing tenant; `ON DELETE RESTRICT` remains enforced. REST creation still requires `tenant_id`. Editing migration `001` does not alter databases where that revision is already applied.

## TOKEN RELATION

Service-account tokens identify the assigned tenant during MCP authentication. They may omit `expires_at`; finite lifetimes still follow the 90-day token policy.

## REFERENCES

- [**API.md**](../../adr/API.md): Defines API layers and service-account route registration.
- [**TESTS.md**](../../adr/TESTS.md): Defines migration, unit, and HTTP verification tiers.
- [**tokens.md**](./tokens.md): Defines service-account token ownership and lifetime.
