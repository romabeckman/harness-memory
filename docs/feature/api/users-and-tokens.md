---
doc_type: feature
domain: api-access-management
stack: [Python 3.12+, FastAPI, Pydantic 2.x, SQLAlchemy 2.x, PostgreSQL, Alembic]
node_id: "feature:api-users-tokens"
tags: [api, users, tokens, fastapi, security]
edges:
  - relation: implements
    target: "adr:architecture"
  - relation: references
    target: "adr:api"
  - relation: tested_by
    target: "adr:tests"
updated: 2026-09-20
---
# API Users and Tokens

```graph
{
  "node_id": "feature:api-users-tokens",
  "domain": "api-access-management",
  "implements": ["adr:architecture"],
  "references": ["adr:api"],
  "tested_by": ["adr:tests"],
  "entrypoints": ["api/server/app.py"],
  "registration_files": ["core/infrastructure/postgres/models/__init__.py", "migrations/env.py", "docker-compose.yml"],
  "reference_files": ["api/application/services/token_service.py", "core/infrastructure/postgres/repositories/api_token_repository.py"],
  "code_files": ["api/__init__.py", "api/adapters/__init__.py", "api/adapters/http/__init__.py", "api/adapters/http/user_routes.py", "api/adapters/http/token_routes.py", "api/adapters/http/schemas/__init__.py", "api/adapters/http/schemas/user_create.py", "api/adapters/http/schemas/user_update.py", "api/adapters/http/schemas/user_response.py", "api/adapters/http/schemas/token_create.py", "api/adapters/http/schemas/token_update.py", "api/adapters/http/schemas/token_response.py", "api/adapters/http/schemas/token_created_response.py", "api/application/__init__.py", "api/application/ports/__init__.py", "api/application/ports/user_repository.py", "api/application/ports/token_repository.py", "api/application/services/__init__.py", "api/application/services/user_service.py", "api/domain/__init__.py", "api/domain/entities/__init__.py", "api/domain/entities/user.py", "api/domain/entities/access_token.py", "api/domain/entities/issued_token.py", "api/domain/services/__init__.py", "api/domain/services/token_expiration_policy.py", "api/server/__init__.py", "core/infrastructure/postgres/models/api_user.py", "core/infrastructure/postgres/models/api_access_token.py", "core/infrastructure/postgres/repositories/api_user_repository.py", "migrations/versions/005_api_users_and_tokens.py"],
  "test_files": ["tests/unit/api/domain/test_token_policy.py", "tests/unit/api/application/test_user_service.py", "tests/unit/api/application/test_token_service.py", "tests/integration/api/infrastructure/test_repositories.py", "tests/e2e/api/test_user_token_crud.py"]
}
```

## OVERVIEW

Expose user and access-token CRUD through **FastAPI**. Keep API domain and application code independent from SQLAlchemy; implement persistence with shared `core/infrastructure/postgres` adapters.

## FOLDER STRUCTURE

<folder_structure>
```text
api/
├── domain/              # User, token, and expiry rules
├── application/         # CRUD services and repository ports
├── adapters/http/       # FastAPI routes and request/response schemas
└── server/              # Runtime composition
core/infrastructure/postgres/ # Shared SQLAlchemy models and repositories
```
</folder_structure>

## HTTP CONTRACT

| Method | Path | Success | Purpose |
|--------|------|---------|---------|
| GET | `/health` | 200 | Report API process health. |
| POST | `/users` | 201 | Create user. |
| GET | `/users` | 200 | List users. |
| GET | `/users/{id}` | 200 | Get user. |
| PATCH | `/users/{id}` | 200 | Update name or email. |
| DELETE | `/users/{id}` | 204 | Delete user and owned tokens. |
| POST | `/tokens` | 201 | Create token; return plaintext once. |
| GET | `/tokens` | 200 | List token metadata; filter by `user_id`. |
| GET | `/tokens/{id}` | 200 | Get token metadata. |
| PATCH | `/tokens/{id}` | 200 | Update token name or expiration. |
| DELETE | `/tokens/{id}` | 204 | Delete token. |

OpenAPI is available at `/openapi.json`; Swagger UI is available at `/docs`.

## TOKEN RULES

REQUIRED: Set expiration after issuance and no later than **90 days** after issuance.
REQUIRED: Store only the SHA-256 token digest; return plaintext only from `POST /tokens`.
REQUIRED: Delete a user's tokens through database cascade when deleting that user.
REQUIRED: Use issued tokens only to authenticate MCP clients.
PROHIBITED: Return token hashes from read or update endpoints.
PROHIBITED: Treat issued tokens as REST API authentication credentials.

## CONFIGURATION

| Name | Type | Required | Description | Default |
|------|------|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL URL | Docker: Yes | Shared database connection. | Local PostgreSQL URL |
| `APP_PORT` | Integer | No | Docker image health-check port. | `8000` |

## DOCUMENT MAP

```mermaid
graph TD
    API["API Users and Tokens"] -->|implements| ARCH["Project Architecture"]
    API -->|references| APIARCH["API Architecture"]
    API -->|tested_by| TESTS["Testing Protocol"]
    click APIARCH "../../adr/API.md"
    click ARCH "../../adr/ARCHITECTURE.md"
    click TESTS "../../adr/TESTS.md"
```

## REFERENCES

- [**ARCHITECTURE.md**](../../adr/ARCHITECTURE.md): Defines hexagonal boundaries and shared infrastructure.
- [**API.md**](../../adr/API.md): Defines the FastAPI module layers and its shared PostgreSQL adapters.
- [**TESTS.md**](../../adr/TESTS.md): Defines unit, integration, E2E, and coverage gates.
- [**token-authentication.md**](../mcp/token-authentication.md): Consumes active API tokens for MCP authentication.
