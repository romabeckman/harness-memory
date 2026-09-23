# Harness Memory REST API

The `api/` module provides the REST management interface for Harness Memory. It creates and manages users, tenant-bound service accounts, and bearer tokens for MCP clients. It does not provide the engineering knowledge tools; those are exposed by [`harness_memory_mcp`](../harness_memory_mcp/README.md).

## Start the API

Run these commands from the repository root. Docker Compose starts PostgreSQL and applies migrations before it starts the API:

```bash
docker compose up --build -d api
```

The API listens at `http://localhost:8080`.

- Health: <http://localhost:8080/health>
- Interactive API documentation: <http://localhost:8080/docs>
- OpenAPI schema: <http://localhost:8080/openapi.json>

To start the complete application, including the MCP server, run `docker compose up --build` instead.

## HTTP endpoints

All routes use JSON unless the response has no body (`204`). API and MCP accept the same
`Authorization: Bearer <API_TOKEN>` value. If it matches `API_ADMIN_TOKEN`, it grants full
REST access. Otherwise, it must match an active row in `tokens`; access then uses stored
scopes and owner tenant. Management routes require `API_ADMIN_TOKEN`. Admin data reads span
all tenants. Admin publication requires a `tenant_id` destination in the JSON body.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Check that the API process is running. |
| `POST`, `GET` | `/v1/users` | Create a user or list users. |
| `GET`, `PATCH`, `DELETE` | `/v1/users/{user_id}` | Read, update, or delete a user. Deleting a user also deletes its tokens. |
| `POST`, `GET` | `/v1/service-accounts` | Create or list service accounts. Add `?tenant_id={tenant_id}` to filter by tenant. |
| `GET`, `PATCH`, `DELETE` | `/v1/service-accounts/{account_id}` | Read, rename, or delete a service account. Deleting it also revokes its tokens. |
| `POST`, `GET` | `/v1/tokens` | Issue a token or list token metadata. Filter with `user_id` or `service_account_id`. |
| `GET`, `PATCH`, `DELETE` | `/v1/tokens/{token_id}` | Read metadata, update the name or expiration, or revoke a token. |
| `POST` | `/v1/knowledge-publications` | Publish and activate a tenant-scoped environment snapshot. |
| `POST`, `GET` | `/v1/tenants` | Admin creates tenants; credentials read within their scope. |
| `GET`, `PATCH`, `DELETE` | `/v1/tenants/{tenant_id}` | Read tenant; admin updates or deletes an empty tenant. |
| `GET` | `/v1/tenants/current` | Read authenticated tenant metadata. |
| `POST`, `GET` | `/v1/projects` | Admin creates projects; credentials read within their scope. |
| `GET`, `PATCH`, `DELETE` | `/v1/projects/{project_key}` | Read project; admin updates or deletes a project without dependent data. |
| `GET` | `/v1/projects/{project_key}/snapshots`, `/v1/snapshots/{snapshot_id}` | Read snapshot history or one stored payload; snapshots have no write methods. |

Management endpoints use the `/v1` prefix. Health, Swagger UI, and OpenAPI routes remain unversioned. API-issued tokens do not authorize management calls. Ordinary data calls derive tenant from the authenticated owner. Admin data reads span all tenants; `?tenant_id=` can disambiguate duplicate project keys or publication baselines. Ordinary tokens cannot use that parameter to change their tenant.

## Create an MCP credential

Create a user:

```bash
curl -X POST http://localhost:8080/v1/users \
  -H 'Content-Type: application/json' \
  -d '{"name":"Example user","email":"example@example.com"}'
```

Copy the returned `id`, then issue a user token. Set `expires_at` to a future UTC timestamp no more than 90 days away:

```bash
curl -X POST http://localhost:8080/v1/tokens \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"<USER_ID>","name":"Local MCP client","expires_at":"<FUTURE_UTC_TIMESTAMP>","scopes":["memory:read"]}'
```

The create response contains the plaintext token once. Save it in a secret store or your MCP client's private configuration. The database stores only its SHA-256 digest. Token list and read responses never return the plaintext or digest. Delete the token to revoke it.

### Service-account token

Create a service account with the tenant UUID used by Harness Memory:

```bash
curl -X POST http://localhost:8080/v1/service-accounts \
  -H 'Content-Type: application/json' \
  -d '{"name":"Build agent","tenant_id":"<TENANT_UUID>"}'
```

Copy the service account `id`, then issue a token without `expires_at` for a non-expiring credential:

```bash
curl -X POST http://localhost:8080/v1/tokens \
  -H 'Content-Type: application/json' \
  -d '{"service_account_id":"<SERVICE_ACCOUNT_ID>","name":"CI automation","scopes":["memory:publish"]}'
```

User tokens still require an expiration. Service-account tokens may omit `expires_at`; any finite expiration must be within 90 days. A service account's tenant binding is immutable. Create another service account to use a different tenant.

Use the token when connecting an MCP client:

- URL: `http://localhost:8000/mcp`
- Header: `Authorization: Bearer <token>`

See the [MCP module README](../harness_memory_mcp/README.md) for connection and authentication details.

## Configuration

`DATABASE_URL` selects the shared PostgreSQL database. `API_ADMIN_TOKEN` is the admin
bearer secret and is required by Docker Compose. The API validates other bearer tokens
against the shared `tokens` table. No separate static read credential exists. See
`.env-example` for the environment variable format.

The API uses the shared database schema. Run migrations before starting it; the API does not migrate the database at runtime. Docker Compose handles this startup order for you.

## Module layout

- `adapters/http/`: FastAPI routes and request/response schemas.
- `application/`: user, service-account, and token services plus repository interfaces.
- `domain/`: user, service-account, token, and token-expiration rules.
- `server/app.py`: FastAPI application and dependency composition.
- `core/infrastructure/postgres/`: shared PostgreSQL models and repository implementations.

Keep routes focused on HTTP input/output. Put business rules in the application or domain layer, and keep database details in the shared infrastructure module.

## Contribute

From the repository root, run the API unit tests with:

```bash
./venv/bin/python -m pytest tests/unit/api
```

On Windows, use `venv\Scripts\python.exe` in place of `./venv/bin/python`. See the [project README](../README.md) for the full setup and test commands, and [API architecture](../docs/adr/API.md) for design boundaries.
