# Developer Setup

Harness Memory stores versioned project knowledge in PostgreSQL. The **REST API** owns
administration and publication; the **MCP server** is a read-only interface for developers
and agents. This setup uses Docker Compose and does not require a local PostgreSQL install.

## REQUIREMENTS

- **Docker Desktop** with Compose v2.
- **Git**.
- **Python 3.12+** and a virtual environment for local tests.
- A terminal that can send HTTP requests (`curl` is included on modern Windows, macOS,
  and Linux installations).

## START THE LOCAL STACK

1. Clone the repository and enter its root directory.
2. Copy `.env-example` to `.env`.
3. Replace `API_ADMIN_TOKEN` with a long random value. Keep `.env` private.
4. Start PostgreSQL, migrations, API, and MCP:

```bash
# CORRECT: start the complete local stack
docker compose up --build
```

The services expose PostgreSQL on `localhost:5432`, the API on `localhost:8080`, and MCP
over Streamable HTTP on `http://localhost:8000/mcp`. Migrations run before API and MCP.

Verify the API from another terminal:

```bash
# CORRECT: health does not require an administrative credential
curl http://localhost:8080/health
```

## CREATE DEVELOPMENT CREDENTIALS

Management routes require `API_ADMIN_TOKEN`. Use a **user token with `memory:read`** for
interactive MCP work. Use a **tenant-bound service-account token with
`memory:publish`** only in a CI pipeline that must publish snapshots.

1. Export the administrator secret in the current shell:

```bash
# CORRECT: keep the secret in an environment variable
export API_ADMIN_TOKEN='replace-this-with-the-value-from-.env'
```

2. Create a local user and copy the returned `id` into `USER_ID`:

```bash
# CORRECT: administrator authorization protects credential management
curl -X POST http://localhost:8080/v1/users \
  -H "Authorization: Bearer $API_ADMIN_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"name":"Local Developer","email":"developer@example.com"}'
export USER_ID='paste-the-returned-user-id'
```

3. Issue a read-only token and save the plaintext value returned once:

```bash
# CORRECT: request the minimum scope for MCP exploration
curl -X POST http://localhost:8080/v1/tokens \
  -H "Authorization: Bearer $API_ADMIN_TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{\"user_id\":\"$USER_ID\",\"name\":\"Local MCP\",\"expires_at\":\"2030-01-01T00:00:00Z\",\"scopes\":[\"memory:read\"]}"
```

Do not use an API-issued token for management routes. Do not put a tenant ID in MCP tool
arguments; the server derives tenant identity from the token owner.

For a local publication smoke test, create a separate service account. Copy the returned
account ID into `SERVICE_ACCOUNT_ID`, then keep the returned token as `PUBLISH_TOKEN`:

```bash
# CORRECT: bind automation to one tenant and grant publication only
export TENANT_ID="$(python3 -c 'import uuid; print(uuid.uuid4())')"
curl -X POST http://localhost:8080/v1/service-accounts \
  -H "Authorization: Bearer $API_ADMIN_TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{\"name\":\"Local Publisher\",\"tenant_id\":\"$TENANT_ID\"}"
export SERVICE_ACCOUNT_ID='paste-the-returned-service-account-id'
curl -X POST http://localhost:8080/v1/tokens \
  -H "Authorization: Bearer $API_ADMIN_TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{\"service_account_id\":\"$SERVICE_ACCOUNT_ID\",\"name\":\"Local Publisher\",\"scopes\":[\"memory:publish\"]}"
export PUBLISH_TOKEN='paste-the-returned-publisher-token'
```

## CONNECT AN MCP CLIENT

Set `HARNESS_MEMORY_TOKEN` to the plaintext read token, then configure the client with:

```text
# CORRECT: use the MCP endpoint and bearer header
URL: http://localhost:8000/mcp
Authorization: Bearer ${HARNESS_MEMORY_TOKEN}
```

Use `search_entities` first, then pass returned entity IDs to `get_context`,
`get_dependencies`, `find_integration_paths`, or `analyze_impact`. Use
`get_environment` and `compare_environments` to inspect environment snapshots. MCP does
not expose a publication tool.

## PUBLISH FROM CI/CD

Create a tenant-bound service account and issue a token with only `memory:publish` using
the administrator credential. Send complete project facts to the REST publication route:

```bash
# CORRECT: publish through the governed API boundary
curl -X POST http://localhost:8080/v1/knowledge-publications \
  -H "Authorization: Bearer $PUBLISH_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "project_key": "payments",
    "environment": "staging",
    "deployment_id": "build-2026-09-21-001",
    "version": "1.4.0",
    "entities": [{"key":"payments-api","type":"api","name":"Payments API"}],
    "relations": [],
    "evidence": []
  }'
```

The first publication creates the project/environment pair when needed. An equivalent
retry returns `ALREADY_PUBLISHED`; reusing a deployment ID with different content returns
`409 Conflict`. The authenticated token supplies the tenant, so omit `tenant_id` and
`X-Tenant-ID`.

## RUN TESTS LOCALLY

```bash
# CORRECT: create and use the repository virtual environment
python3 -m venv venv
./venv/bin/python -m pip install -r requirements.txt
./venv/bin/python -m pytest -q -p no:cacheprovider
./venv/bin/python -m pytest tests/unit tests/integration tests/e2e \
  --cov=api --cov=core --cov=harness_memory_mcp --cov-branch \
  --cov-fail-under=80 -q -p no:cacheprovider
```

On Windows, replace `./venv/bin/python` with `venv\Scripts\python.exe`. PostgreSQL
integration tests run when `TEST_DATABASE_URL` points to a disposable database.

## STOP AND RESET LOCAL DATA

```bash
# CORRECT: stop services but preserve the PostgreSQL volume
docker compose down

# CORRECT: remove local database data only when a clean reset is intended
docker compose down -v
```

## TROUBLESHOOTING

| Symptom | Action |
| --- | --- |
| API returns `503` for management calls | Set the same `API_ADMIN_TOKEN` in `.env` and the request header, then recreate the API container. |
| MCP returns `401` | Check token expiry, plaintext value, and `MCP_AUTH_MODE=database`. |
| MCP returns `403` | Issue a token containing the scope required by the selected tool. |
| API publication returns `409` | Keep one deployment ID tied to one exact payload; use a new deployment ID for new content. |
| Empty search results | Publish a complete snapshot, use an exact project key, and verify the token's tenant. |

## REFERENCES

- [API README](../../api/README.md): REST routes, credential lifecycle, and configuration.
- [MCP README](../../harness_memory_mcp/README.md): MCP catalog and client authentication.
- [Workflow README](./README.md): day-to-day search, analysis, and publication workflow.
- [Project README](../../README.md): repository overview and development commands.
