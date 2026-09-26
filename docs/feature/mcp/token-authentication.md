---
doc_type: feature
domain: mcp-token-authentication
stack: [Python 3.12+, FastMCP 4.x, SQLAlchemy 2.x, PostgreSQL]
node_id: "feature:mcp-token-authentication"
tags: [mcp, authentication, tokens, bearer, database]
edges:
  - relation: implements
    target: "adr:architecture"
  - relation: tested_by
    target: "adr:tests"
  - relation: references
    target: "adr:mcp"
  - relation: references
    target: "adr:api"
  - relation: depends_on
    target: "feature:api-tokens"
    read: must
updated: 2026-09-26
---
# MCP Token Authentication

Authenticate MCP clients with opaque bearer tokens issued by the REST API.

```graph
{"node_id":"feature:mcp-token-authentication","domain":"mcp-token-authentication","implements":["adr:architecture"],"tested_by":["adr:tests"],"references":["adr:mcp","adr:api"],"depends_on":["feature:api-tokens"],"entrypoints":["harness_memory_mcp/server/app.py"],"registration_files":["harness_memory_mcp/server/factory.py","docker-compose.yml"],"reference_files":["harness_memory_mcp/services/database_token_verifier.py","harness_memory_mcp/services/admin_token_verifier.py","core/infrastructure/postgres/repositories/api_token_repository.py","core/infrastructure/postgres/repositories/api_service_account_repository.py"],"code_files":["harness_memory_mcp/config.py","api/application/ports/token_repository.py","api/domain/entities/service_account.py","api/domain/entities/access_token.py","core/infrastructure/postgres/models/api_service_account.py","core/domain/tenant_security/types/memory_scope.py"],"test_files":["tests/unit/mcp/services/test_database_token_verifier.py","tests/unit/mcp/services/test_admin_token_verifier.py","tests/unit/mcp/server/test_factory.py","tests/unit/mcp/test_config.py","tests/integration/api/infrastructure/test_repositories.py","tests/e2e/api/test_user_token_crud.py","tests/e2e/mcp/test_api_token_authentication.py"],"knowledge":{"schema_version":1,"entities":[{"id":"capability:authenticate-mcp-tokens","type":"capability","label":"Authenticate MCP tokens","definition":"Verify API-issued opaque bearer tokens for MCP requests.","aliases":[]},{"id":"rule:token-owner-principal","type":"rule","label":"Token owner principal","definition":"Derive principal subject, tenant, and scopes from an active stored token and its owner.","aliases":[]},{"id":"contract:mcp-bearer-token","type":"contract","label":"MCP bearer token","definition":"An active opaque token maps to an authenticated principal; invalid or expired tokens are rejected.","aliases":[]}],"claims":[{"id":"claim:token-digest-lookup","subject":"capability:authenticate-mcp-tokens","relation":"constrained_by","object":"rule:token-owner-principal","statement":"Database verification hashes the presented token and queries only for an active matching digest.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"harness_memory_mcp/services/database_token_verifier.py","locator":"DatabaseTokenVerifier.verify_token","snapshot":null},{"kind":"code","source":"core/infrastructure/postgres/repositories/api_token_repository.py","locator":"ApiTokenRepository.find_active_by_hash","snapshot":null}],"derived_from":[],"gap":null},{"id":"claim:principal-from-token-owner","subject":"capability:authenticate-mcp-tokens","relation":"exposes","object":"contract:mcp-bearer-token","statement":"The verifier builds the principal from the stored token owner and persisted scopes; request payload identity is not used.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"harness_memory_mcp/services/database_token_verifier.py","locator":"DatabaseTokenVerifier.verify_token","snapshot":null}],"derived_from":[],"gap":null}]}}
```

## OVERVIEW

Use API-issued user or service-account tokens as bearer credentials with persisted
scopes. Both owner types have the same eligible permissions. MCP read operations span
tenants with `memory:read`; impact operations retain the owner's tenant context.
MCP also accepts `API_ADMIN_TOKEN` for cross-tenant data reads in both auth modes.

## FOLDER STRUCTURE

<folder_structure>
```text
harness_memory_mcp/
├── services/             # Opaque-token verification adapter
├── server/               # Authentication composition
└── config.py             # Authentication mode selection
core/infrastructure/postgres/ # Active-token lookup
```
</folder_structure>

## AUTHENTICATION FLOW

1. Create either a user through `POST /v1/users` or a service account through `POST /v1/service-accounts`.
2. Create a token through `POST /v1/tokens` for exactly one owner. Omit `expires_at` for a non-expiring service-account token.
3. Configure the MCP client with `Authorization: Bearer <token>`.
4. Connect the client to `http://localhost:8000/mcp`.

The verifier maps the token owner's ID to `sub` and the owner's tenant binding to
`tenant_id`. A principal receives exactly the scopes persisted for that token.
An admin principal receives all current memory scopes with global tenant access. Existing
MCP component scope checks remain active.

## CONFIGURATION

| Name | Type | Required | Description | Default |
|------|------|----------|-------------|---------|
| `MCP_AUTH_MODE` | `database` or `jwt` | No | Select opaque database tokens or external JWT verification. | `jwt` |
| `DATABASE_URL` | PostgreSQL URL | Database mode: Yes | Load active token and its user or service-account owner. | None |
| `API_ADMIN_TOKEN` | Secret | No | Grant all MCP scopes while preserving component scope checks. | None |

## SECURITY RULES

REQUIRED: Compare only SHA-256 token digests in persistence.
REQUIRED: Reject unknown, deleted, or expired tokens with HTTP 401; treat a null expiry as non-expiring.
REQUIRED: Resolve subject and tenant from the stored token owner.
REQUIRED: Reject active token records with missing token or owner data before creating a principal.
PROHIBITED: Accept user or tenant identity from MCP request payloads.
PROHIBITED: Use API tokens to authenticate REST management endpoints.


## REFERENCES

- [**ARCHITECTURE.md**](../../adr/ARCHITECTURE.md): Defines adapter and persistence boundaries.
- [**TESTS.md**](../../adr/TESTS.md): Defines verification tiers.
- [**MCP.md**](../../adr/MCP.md): Defines MCP transport and component contracts.
- [**API.md**](../../adr/API.md): Defines issuance and ownership of MCP bearer tokens.
- [**tokens.md**](../api/tokens.md): Defines token issuance and lifecycle.
