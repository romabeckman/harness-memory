# DevOps Playbook

Operate Harness Memory as part of the software delivery platform. This guide covers
service bootstrap, credentials, CI/CD publication, environment configuration, rollout,
and incident response.

## 1. Operating model

Harness Memory has two separate boundaries:

| Boundary | Main users | Responsibility | Write access |
| --- | --- | --- | --- |
| REST API | Platform administrators and CI/CD | Manage identities, issue tokens, and publish snapshots | Management and publication only |
| MCP over Streamable HTTP | Developers and AI agents | Search, inspect, compare, and analyze stored knowledge | Read-only |

The Snapshot Publisher SDK runs in a pipeline. It collects Git context, invokes a local
LLM, validates the generated graph, calculates a deterministic SHA-256, and publishes
through `POST /v1/knowledge-publications`.

The API creates a project and environment record during the first trusted publication.
There is no standalone project-creation route. A successful publication also creates an
immutable snapshot and promotes it as the environment's current snapshot. Historical
snapshots remain available for comparison and investigation.

Never use MCP as a publication channel. Never write graph facts directly to PostgreSQL.

## 2. Target topology

Local Docker Compose exposes these services:

| Service | Local address | Purpose |
| --- | --- | --- |
| PostgreSQL | `localhost:5432` | Shared persistence. Keep private in production. |
| REST API | `http://localhost:8080` | Management and CI/CD publication. |
| MCP server | `http://localhost:8000/mcp` | Read-only developer and agent access. |

Production deployments must use HTTPS for API and MCP traffic, private PostgreSQL
networking, secret management, explicit schema migration, and authenticated HTTP mode.
The API and MCP services must not share a management credential with users or pipelines.

## 3. Bootstrap the platform

### 3.1 Prepare configuration

Set a unique high-entropy administrator secret before starting Compose. Keep it in a
secret manager or private environment configuration.

```bash
export API_ADMIN_TOKEN='replace-with-a-high-entropy-secret'
docker compose up --build -d
```

Compose starts PostgreSQL, runs the explicit migration service, then starts the API and
MCP services. The application does not upgrade the production schema at runtime.

Verify the services:

```bash
curl --fail http://localhost:8080/health
```

The API exposes interactive documentation at `http://localhost:8080/docs` and an OpenAPI
schema at `http://localhost:8080/openapi.json`. The MCP server is available at
`http://localhost:8000/mcp`; verify MCP connectivity from an authenticated client.

Before production rollout, verify that the database revision equals Alembic `head`, the
API admin secret is present, `MCP_AUTH_MODE=database` has a working `DATABASE_URL`, and
the MCP server is running with production authentication enabled.

### 3.2 Establish tenant identity

Every project, environment, snapshot, graph fact, user token, and service-account token
belongs to one tenant. Tenant identity must come from an authenticated owner; it must
never come from a request header, CLI flag, or graph payload.

For a service account, use the tenant UUID assigned by the platform or organization.
Do not invent a tenant UUID. A service account keeps its tenant binding for its entire
lifetime.

For a first local bootstrap, a user UUID can supply the tenant identity for a user-owned
token. Use a service account with an approved tenant UUID for automation and production
publication.

## 4. Manage users, service accounts, and tokens

All management routes require the independent `API_ADMIN_TOKEN`:

```bash
export API_BASE_URL='http://localhost:8080'
export API_ADMIN_TOKEN='replace-with-admin-secret'
```

Use the admin token only in the `Authorization` header for management calls. Never put
it in an MCP client configuration or `HARNESS_MEMORY_API_TOKEN`.

### 4.1 Register a human user

Create one user per human identity. Email values are normalized to lowercase and must be
unique.

```bash
curl --fail --request POST "$API_BASE_URL/v1/users" \
  --header "Authorization: Bearer $API_ADMIN_TOKEN" \
  --header 'Content-Type: application/json' \
  --data '{"name":"Ada Lovelace","email":"ada@example.com"}'
```

Save the returned `id` as `USER_ID`. Deleting a user also revokes tokens owned by that
user. Renaming or changing email does not change the user UUID or tenant identity.

List and inspect users when an operator needs to verify ownership:

```bash
curl --fail "$API_BASE_URL/v1/users" \
  --header "Authorization: Bearer $API_ADMIN_TOKEN"

curl --fail "$API_BASE_URL/v1/users/$USER_ID" \
  --header "Authorization: Bearer $API_ADMIN_TOKEN"
```

### 4.2 Issue a human read token

User tokens require an expiration. A finite expiration must be no more than 90 days from
issuance. Request only the scopes needed by the user.

```bash
curl --fail --request POST "$API_BASE_URL/v1/tokens" \
  --header "Authorization: Bearer $API_ADMIN_TOKEN" \
  --header 'Content-Type: application/json' \
  --data '{
    "user_id":"<USER_ID>",
    "name":"Ada local MCP",
    "expires_at":"2026-12-15T23:59:59Z",
    "scopes":["memory:read"]
  }'
```

Add `memory:impact` for change-impact analysis:

```json
{
  "user_id": "<USER_ID>",
  "name": "Ada engineering MCP",
  "expires_at": "2026-12-15T23:59:59Z",
  "scopes": ["memory:read", "memory:impact"]
}
```

The create response returns plaintext `token` exactly once. Store it in the user's
approved secret store. List, get, and update responses never return plaintext or the
stored digest.

### 4.3 Register a CI service account

Create a non-human identity for each automation boundary or trust domain. Use the
organization-approved tenant UUID.

```bash
curl --fail --request POST "$API_BASE_URL/v1/service-accounts" \
  --header "Authorization: Bearer $API_ADMIN_TOKEN" \
  --header 'Content-Type: application/json' \
  --data '{
    "name":"Payments production publisher",
    "tenant_id":"<TENANT_UUID>"
  }'
```

Save the returned `id` as `SERVICE_ACCOUNT_ID`. The tenant binding cannot be changed.
Delete and recreate the account only through an approved identity-lifecycle process when
its tenant association must change.

### 4.4 Issue a publication token

Issue the minimum scope required by the SDK. `memory:publish` authorizes REST publication;
it does not grant MCP read access.

```bash
curl --fail --request POST "$API_BASE_URL/v1/tokens" \
  --header "Authorization: Bearer $API_ADMIN_TOKEN" \
  --header 'Content-Type: application/json' \
  --data '{
    "service_account_id":"<SERVICE_ACCOUNT_ID>",
    "name":"Payments CI publication",
    "expires_at":"2026-12-15T23:59:59Z",
    "scopes":["memory:publish"]
  }'
```

Service-account tokens may omit `expires_at`, but finite lifetimes are safer and remain
subject to the 90-day policy. The plaintext token is returned once. Store it as a CI
secret named `HARNESS_MEMORY_API_TOKEN`.

### 4.5 Rotate and revoke credentials

Rotate by issuing a replacement token, updating the secret store, validating the next
request, then deleting the old token:

```bash
curl --fail --request DELETE "$API_BASE_URL/v1/tokens/<TOKEN_ID>" \
  --header "Authorization: Bearer $API_ADMIN_TOKEN"
```

Deleting a user or service account also revokes its owned tokens. Treat a lost plaintext
token as compromised: issue a replacement and revoke the old credential. The plaintext
cannot be recovered from the API.

## 5. Register projects and environments

Project and environment registration is publication-driven:

1. Select a stable `project_key`, such as `com.example.payments`.
2. Select a stable environment name, such as `staging` or `production`.
3. Publish a complete graph through the API or SDK.
4. The API creates the missing project/environment pair in the authenticated tenant.
5. The API creates and activates the immutable snapshot.

Use the same project key across environments. Use one environment name per deployment
target. Do not create separate project keys for every release.

Each publication needs:

| Field | Rule |
| --- | --- |
| `project_key` | Stable identifier for the logical software project. |
| `environment` | Deployment target, for example `development`, `staging`, or `production`. |
| `deployment_id` | Unique CI/CD deployment execution identity. Required for idempotency. |
| `version` | Release version, image digest, or commit SHA. |
| `entities` | Complete validated entity facts for the snapshot. |
| `relations` | Complete validated relationships with existing endpoints. |
| `evidence` | Sources and excerpts supporting facts or relationships. |

An identical retry returns `200 ALREADY_PUBLISHED`. Reusing the same deployment identity
with different content returns `409 Conflict`; do not overwrite or silently reuse it.

## 6. Configure the Snapshot Publisher SDK

### 6.1 Build the SDK

From the Harness Memory repository:

```bash
npm --prefix sdk ci
npm --prefix sdk run build
```

The compiled CLI is `sdk/dist/cli/index.js`. The SDK requires Node.js 20+, Git, and a
local LLM command. Its default LLM command is `codex`; configure another executable with
`--llm-command` or `HARNESS_MEMORY_LLM_COMMAND`.

### 6.2 Required pipeline settings

Provide the token through a secret environment variable. Do not pass `--token`, write a
token into `.harness-memory.json`, or echo the token in logs.

```bash
export HARNESS_MEMORY_API_URL='https://memory-api.example.com'
export HARNESS_MEMORY_API_TOKEN='from-ci-secret-store'
export HARNESS_MEMORY_ENVIRONMENT='production'
export HARNESS_MEMORY_PROJECT_KEY='com.example.payments'
export HARNESS_MEMORY_DEPLOYMENT_ID="$CI_PIPELINE_ID"
export HARNESS_MEMORY_VERSION="$CI_COMMIT_SHA"
```

Required execution values are `model`, `effort`, `environment`, `project-key`,
`deployment-id`, and `version`. Real publication also requires `api-url` and a token.
Use `low`, `medium`, `high`, or `xhigh` for `effort`.

### 6.3 Publish from a pipeline

Run publication after the deployment succeeds and the deployed artifact identity is
known. `--repository` points to the source checkout that the SDK must analyze.

```bash
node /workspace/harness-memory/sdk/dist/cli/index.js publish \
  --repository "$CI_PROJECT_DIR" \
  --model gpt-5 \
  --effort high \
  --environment "$HARNESS_MEMORY_ENVIRONMENT" \
  --project-key "$HARNESS_MEMORY_PROJECT_KEY" \
  --deployment-id "$HARNESS_MEMORY_DEPLOYMENT_ID" \
  --version "$HARNESS_MEMORY_VERSION" \
  --api-url "$HARNESS_MEMORY_API_URL" \
  --output json
```

The API URL is an origin. The SDK sends the request to
`/v1/knowledge-publications`. Non-local URLs must use HTTPS.

### 6.4 GitLab pipeline pattern

The following pattern assumes the Harness Memory SDK is available in the runner at
`$HARNESS_MEMORY_SDK_DIR`. Adapt the checkout or package-install step to the approved
internal artifact process.

```yaml
harness_memory_publish:
  stage: publish-memory
  image: node:20
  needs:
    - job: deploy_production
      artifacts: false
  variables:
    HARNESS_MEMORY_API_URL: "https://memory-api.example.com"
    HARNESS_MEMORY_ENVIRONMENT: "production"
    HARNESS_MEMORY_PROJECT_KEY: "com.example.payments"
    HARNESS_MEMORY_DEPLOYMENT_ID: "$CI_PIPELINE_ID"
    HARNESS_MEMORY_VERSION: "$CI_COMMIT_SHA"
  script:
    - npm --prefix "$HARNESS_MEMORY_SDK_DIR" ci
    - npm --prefix "$HARNESS_MEMORY_SDK_DIR" run build
    - |
      node "$HARNESS_MEMORY_SDK_DIR/dist/cli/index.js" publish \
        --repository "$CI_PROJECT_DIR" \
        --model gpt-5 \
        --effort high \
        --environment "$HARNESS_MEMORY_ENVIRONMENT" \
        --project-key "$HARNESS_MEMORY_PROJECT_KEY" \
        --deployment-id "$HARNESS_MEMORY_DEPLOYMENT_ID" \
        --version "$HARNESS_MEMORY_VERSION" \
        --api-url "$HARNESS_MEMORY_API_URL" \
        --output json
  environment:
    name: production
  rules:
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
  secrets:
    HARNESS_MEMORY_API_TOKEN:
      vault: production/harness-memory/api-token
```

The exact secret syntax depends on the CI provider. The token must be injected only into
the publication process and must not be included in artifacts, cache keys, or debug logs.

### 6.5 Dry-run validation

Run dry run in merge requests or pre-merge checks. It collects Git context, runs the LLM,
validates the graph, and computes the payload hash without changing Harness Memory.

```bash
node sdk/dist/cli/index.js publish \
  --repository "$CI_PROJECT_DIR" \
  --model gpt-5 \
  --effort medium \
  --environment staging \
  --project-key "$HARNESS_MEMORY_PROJECT_KEY" \
  --deployment-id "dry-run-$CI_PIPELINE_ID" \
  --version "$CI_COMMIT_SHA" \
  --dry-run \
  --output json \
  --verbose
```

Dry run does not need `HARNESS_MEMORY_API_URL` or `HARNESS_MEMORY_API_TOKEN`. It still
needs the model command, required deployment metadata, and a valid Git repository.

## 7. Tune repository collection safely

The SDK reads tracked text files only. It excludes `.git`, `node_modules`, `dist`,
`build`, `coverage`, `venv`, `.venv`, common private-key files, `.env*`, and files with
`.secret` or `.credential` in their names. Binary files are skipped.

Symlink targets must remain inside the repository. Path escapes, file-count limits, and
context-byte limits fail closed before publication.

Defaults:

| Setting | Default | Override |
| --- | ---: | --- |
| Maximum tracked files | 2,000 | `--max-files` / `HARNESS_MEMORY_MAX_FILES` |
| Maximum context bytes | 10 MiB | `--max-bytes` / `HARNESS_MEMORY_MAX_BYTES` |
| LLM timeout | 600 seconds | `--timeout` / `HARNESS_MEMORY_TIMEOUT` |
| Git head | `HEAD` | `--head-ref` / `HARNESS_MEMORY_HEAD_REF` |

Use `--base-ref` to include added, modified, deleted, and renamed paths between refs.
Increase limits only after checking repository size and runner memory.

## 8. Handle results and failures

Use `--output json` in CI. Exit codes are stable:

| Code | Meaning | Operator action |
| ---: | --- | --- |
| `0` | Activated or already published | Record result and continue. |
| `2` | Invalid configuration or forbidden flag | Fix required values or flag usage. |
| `3` | Git collection failure | Check checkout, refs, symlinks, and limits. |
| `4` | LLM failure | Check executable, model, timeout, and JSON stdout. |
| `5` | Graph validation failure | Fix schema, types, keys, endpoints, or evidence refs. |
| `6` | Authentication or scope failure | Issue an active tenant-bound token with `memory:publish`. |
| `7` | Deployment conflict | Preserve the original deployment ID/content or use a new identity. |
| `8` | API failure or exhausted retries | Check health, network, HTTPS, and server logs. |
| `130` | Interrupted process | Retry only after checking whether the deployment completed. |

The REST client retries HTTP 408, 429, 5xx, and timeouts. It does not retry 400, 401,
403, 409, or validation failures. A 409 is an integrity signal, not a transient error.

## 9. Security controls

- Keep `API_ADMIN_TOKEN`, publication tokens, database URLs, and model credentials in a
  secret manager.
- Use separate admin, human, and service-account credentials.
- Give developers `memory:read` and, only when needed, `memory:impact`.
- Give CI publication accounts `memory:publish`; do not use admin tokens in pipelines.
- Use HTTPS outside localhost and keep PostgreSQL private.
- Never pass tenant identity in CLI flags, HTTP headers, or payloads.
- Rotate and revoke tokens after ownership, runner, or project changes.
- Review logs for accidental token output after changing CI scripts.

## 10. DevOps readiness checklist

Before enabling production publication, verify:

- API health and MCP connectivity checks pass.
- Database schema matches Alembic `head`.
- `API_ADMIN_TOKEN` is configured separately from API-issued tokens.
- A service account has the correct immutable tenant UUID.
- A publication token has `memory:publish` and is stored in CI secrets.
- Project key and environment names are stable.
- Deployment ID and version are deterministic and unique per deployment.
- The runner has Node.js 20+, Git, and the configured LLM command.
- Dry run succeeds from the real source checkout.
- The pipeline publishes only after successful deployment.
- JSON output and exit codes are captured by the pipeline.
- Rotation and revocation procedures are tested.

## Related documentation

- [Workflow README](./README.md): Cross-role operating flow.
- [Developer Playbook](./PLAYBOOK-DEVELOPER.md): MCP usage and conversational investigation.
- [User Playbook](./PLAYBOOK-USER.md): Onboarding, tokens, projects, and resources.
- [SDK guide](../../sdk/README.md): Complete CLI and programmatic reference.
- [API README](../../api/README.md): Management and publication endpoint reference.
- [Security architecture](../adr/SECURITY.md): Token and tenant invariants.
