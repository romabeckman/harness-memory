---
doc_type: feature
domain: api-tokens
stack: [Python 3.12+, FastAPI, Pydantic 2.x, SQLAlchemy 2.x, PostgreSQL, SHA-256]
node_id: "feature:api-tokens"
tags: [api, tokens, credentials, mcp]
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
    target: "feature:mcp-token-authentication"
    read: optional
    when: "Read when changing bearer verification, token ownership mapping, or MCP tenant context."
updated: 2026-09-29
---
# API Tokens
Issue and revoke scoped opaque credentials while keeping plaintext outside persistence.

Empty, null, omitted, or explicit `project_keys: ["*"]` grants authorize every current and future project across all tenants. Token creation persists these grants as `["*"]`; explicit project keys are validated globally. Blank-only keys remain invalid. No tenant filter is required: empty or null `tenant_id` is accepted as an ignored extra field. Exactly one existing owner remains required and supplies the token identity.

```graph
{"node_id":"feature:api-tokens","domain":"api-tokens","implements":["adr:architecture"],"tested_by":["adr:tests"],"entrypoints":["api/adapters/http/token_routes.py"],"registration_files":["api/server/app.py"],"reference_files":["api/application/services/token_service.py","api/domain/services/token_expiration_policy.py","core/infrastructure/postgres/repositories/api_token_repository.py"],"code_files":["api/domain/entities/access_token.py","api/domain/entities/issued_token.py","api/application/ports/token_repository.py","api/adapters/http/schemas/token_create.py","api/adapters/http/schemas/token_update.py","api/adapters/http/schemas/token_response.py","api/adapters/http/schemas/token_created_response.py","core/infrastructure/postgres/models/api_access_token.py","migrations/versions/001_foundation.py","core/infrastructure/postgres/repositories/tenant_project_management_repository.py"],"test_files":["tests/unit/api/domain/test_token_policy.py","tests/unit/api/application/test_token_service.py","tests/unit/api/adapters/http/test_api_authentication.py","tests/integration/api/infrastructure/test_repositories.py","tests/e2e/api/test_user_token_crud.py","tests/e2e/mcp/test_api_token_authentication.py","tests/unit/core/infrastructure/postgres/repositories/test_tenant_project_management_repository.py","tests/unit/api/adapters/http/test_token_create.py"],"knowledge":{"schema_version":1,"entities":[{"id":"capability:issue-api-tokens","type":"capability","label":"Issue API tokens","definition":"Issue scoped bearer credentials for one user or service-account owner.","aliases":[]},{"id":"rule:token-owner-and-lifetime","type":"rule","label":"Token owner and lifetime","definition":"Require exactly one owner and user-token expiry; cap finite user tokens at 365 days and service-account tokens at 90 days.","aliases":[]},{"id":"contract:token-creation-response","type":"contract","label":"Token creation response","definition":"Return plaintext on creation and expose only token metadata on later reads and updates.","aliases":[]}],"claims":[{"id":"claim:token-owner-lifetime","subject":"capability:issue-api-tokens","relation":"constrained_by","object":"rule:token-owner-and-lifetime","statement":"TokenService rejects zero or two owners, requires user expiry, allows service-account expiry to be null, and enforces 365-day user and 90-day service-account limits on create and update.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"api/application/services/token_service.py","locator":"TokenService.create: owner and expiry validation","snapshot":null},{"kind":"code","source":"api/domain/services/token_expiration_policy.py","locator":"TokenExpirationPolicy.validate","snapshot":null}],"derived_from":[],"gap":null},{"id":"claim:plaintext-creation-contract","subject":"capability:issue-api-tokens","relation":"exposes","object":"contract:token-creation-response","statement":"Creation returns hm_ plaintext while persistence stores its SHA-256 digest; list, get, and update return metadata only.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"api/application/services/token_service.py","locator":"TokenService.create: plaintext and digest","snapshot":null},{"kind":"code","source":"api/adapters/http/token_routes.py","locator":"create_token, list_tokens, get_token, update_token","snapshot":null}],"derived_from":[],"gap":null},{"id":"claim:global-token-project-access","subject":"capability:issue-api-tokens","relation":"exposes","object":"contract:token-creation-response","statement":"Empty, null, omitted, or wildcard project grants are persisted as * for global access. Blank-only keys are rejected. Explicit keys are validated globally; exactly one owner remains required.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"api/application/services/token_service.py","locator":"TokenService.create: wildcard canonicalization and global project validation","snapshot":null},{"kind":"code","source":"core/domain/tenant_security/value_objects/authenticated_principal.py","locator":"AuthenticatedPrincipal.can_access_project","snapshot":null},{"kind":"code","source":"core/infrastructure/postgres/repositories/tenant_project_management_repository.py","locator":"PostgresTenantProjectManagementRepository.get_project_by_key","snapshot":null}],"derived_from":[],"gap":null}]}}
```

## OVERVIEW

Expose token lifecycle operations under `/v1/tokens`. The API owns issuance, explicit
scope assignment, metadata updates, and revocation. MCP consumes read/impact credentials;
the publication API consumes `memory:publish` credentials for the selected tenant.

## FOLDER STRUCTURE

```text
api/adapters/http/              # Token routes and request/response schemas
api/application/                # Token service and repository ports
api/domain/                     # Access-token entity and expiry policy
core/infrastructure/postgres/  # Digest persistence and active-token lookup
tests/{unit,integration,e2e}/   # Policy, repository, API, and MCP checks
```

## HTTP CONTRACT

| Method | Path | Success | Rule |
|--------|------|---------|------|
| POST | `/v1/tokens` | 201 | Issue for exactly one owner and return plaintext once. |
| GET | `/v1/tokens` | 200 | Return metadata; filter by `user_id` or `service_account_id`. |
| GET | `/v1/tokens/{token_id}` | 200 | Return metadata only. |
| PATCH | `/v1/tokens/{token_id}` | 200 | Update name or expiration. |
| DELETE | `/v1/tokens/{token_id}` | 204 | Revoke token by deletion. |

## LIFECYCLE RULES

REQUIRED: Set exactly one owner: `user_id` or `service_account_id`.
REQUIRED: Require `expires_at` for user tokens.
REQUIRED: Allow a null `expires_at` only for service-account tokens.
REQUIRED: Keep finite user-token lifetimes between one second and 365 days from issuance. Keep finite service-account lifetimes between one second and 90 days.
REQUIRED: Enforce expiration rules in the API through `TokenExpirationPolicy`; PostgreSQL does not enforce an expiration-window constraint in the foundation migration.

Existing databases retain previously applied constraints. Editing `001_foundation.py` does not remove them. To align an existing database without a new migration, an operator must execute `ALTER TABLE tokens DROP CONSTRAINT IF EXISTS ck_token_expiration_window;`. Preserve token rows and the owner constraint.

REQUIRED: Generate opaque plaintext with the `hm_` prefix.
REQUIRED: Persist and return only explicitly requested valid scopes.
REQUIRED: Persist only the 64-character SHA-256 digest.
REQUIRED: Return plaintext only in the successful create response.
REQUIRED: Return metadata without plaintext or digest from list, get, and update responses.
PROHIBITED: Use these credentials to authenticate REST management routes.
PROHIBITED: Accept a second owner or silently select an owner.

## MCP HANDOFF

The token repository locates active records by digest and expiry. Either owner's tenant
binding supplies tenant identity. User and service-account tokens have the same eligible
scopes. The verifier grants only persisted scopes; it never expands them implicitly.

## REFERENCES

- [**API.md**](../../adr/API.md): Defines route boundaries and token handoff responsibilities.
- [**TESTS.md**](../../adr/TESTS.md): Defines token policy, persistence, and E2E checks.
- [**token-authentication.md**](../mcp/token-authentication.md): Consumes active token records for MCP bearer authentication.
