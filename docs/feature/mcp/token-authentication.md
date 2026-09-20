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
    target: "feature:api-users-tokens"
    read: must
updated: 2026-09-20
---
# MCP Token Authentication

Authenticate MCP clients with opaque bearer tokens issued by the REST API.

```graph
{
  "node_id": "feature:mcp-token-authentication",
  "domain": "mcp-token-authentication",
  "implements": ["adr:architecture"],
  "tested_by": ["adr:tests"],
  "references": ["adr:mcp", "adr:api"],
  "depends_on": ["feature:api-users-tokens"],
  "entrypoints": ["mcp/server/app.py"],
  "registration_files": ["mcp/server/factory.py", "docker-compose.yml"],
  "reference_files": ["mcp/services/database_token_verifier.py", "core/infrastructure/postgres/repositories/api_token_repository.py"],
  "code_files": ["mcp/config.py", "api/application/ports/token_repository.py", "core/domain/tenant_security/types/memory_scope.py"],
  "test_files": ["tests/unit/mcp/services/test_database_token_verifier.py", "tests/unit/mcp/server/test_factory.py", "tests/unit/mcp/test_config.py", "tests/integration/api/infrastructure/test_repositories.py", "tests/e2e/mcp/test_api_token_authentication.py"]
}
```

## OVERVIEW

Use an API-issued token only as **MCP bearer authentication**. Hash every presented token, load its active database record, then create the FastMCP identity without exposing the stored digest.

## FOLDER STRUCTURE

<folder_structure>
```text
mcp/
├── services/             # Opaque-token verification adapter
├── server/               # Authentication composition
└── config.py             # Authentication mode selection
core/infrastructure/postgres/ # Active-token lookup
```
</folder_structure>

## AUTHENTICATION FLOW

1. Create a user through `POST /users`.
2. Create a token through `POST /tokens` and retain its one-time plaintext value.
3. Configure the MCP client with `Authorization: Bearer <token>`.
4. Connect the client to `http://localhost:8000/mcp`.

The verifier maps the user ID to both `sub` and `tenant_id`. Each user therefore receives an isolated tenant context. Current API tokens receive `memory:read`, `memory:publish`, and `memory:impact` scopes because role management is outside this feature.

## CONFIGURATION

| Name | Type | Required | Description | Default |
|------|------|----------|-------------|---------|
| `MCP_AUTH_MODE` | `database` or `jwt` | No | Select opaque database tokens or external JWT verification. | `jwt` |
| `DATABASE_URL` | PostgreSQL URL | Database mode: Yes | Load active token and user records. | None |

## SECURITY RULES

REQUIRED: Compare only SHA-256 token digests in persistence.
REQUIRED: Reject unknown, deleted, or expired tokens with HTTP 401.
REQUIRED: Resolve subject and tenant from the stored token owner.
PROHIBITED: Accept user or tenant identity from MCP request payloads.
PROHIBITED: Use API tokens to authenticate REST API endpoints.

## DOCUMENT MAP

```mermaid
graph TD
    AUTH["MCP Token Authentication"] -->|implements| ARCH["Project Architecture"]
    AUTH -->|tested_by| TESTS["Testing Protocol"]
    AUTH -->|references| MCP["MCP Interface"]
    AUTH -->|references| APIARCH["API Architecture"]
    AUTH -->|depends_on| API["API Users and Tokens"]
    click ARCH "../../adr/ARCHITECTURE.md"
    click TESTS "../../adr/TESTS.md"
    click MCP "../../adr/MCP.md"
    click APIARCH "../../adr/API.md"
    click API "../api/users-and-tokens.md"
```

## REFERENCES

- [**ARCHITECTURE.md**](../../adr/ARCHITECTURE.md): Defines adapter and persistence boundaries.
- [**TESTS.md**](../../adr/TESTS.md): Defines verification tiers.
- [**MCP.md**](../../adr/MCP.md): Defines MCP transport and component contracts.
- [**API.md**](../../adr/API.md): Defines issuance and ownership of MCP bearer tokens.
- [**users-and-tokens.md**](../api/users-and-tokens.md): Defines token issuance and lifecycle.
