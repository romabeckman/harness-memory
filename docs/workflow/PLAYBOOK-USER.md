# User Playbook

Harness Memory helps people ask engineering questions in natural language and receive
answers grounded in published project knowledge. You do not need to know SQL, PostgreSQL,
the graph schema, or MCP protocol details to use it.

## 1. What Harness Memory is

Harness Memory preserves software knowledge with its project, environment, snapshot,
source, provenance, and evidence context. It can help answer questions such as:

- What services and APIs belong to a project?
- Who owns a service or relationship?
- Which systems consume an API or event?
- How does one service integrate with another?
- What could be affected by a contract change?
- What differs between staging and production?
- Which version is active in an environment?

The answer is limited to knowledge that has been published and that your token is allowed
to read. Harness Memory does not replace code review, production monitoring, security
approval, or the system of record for a deployment.

## 2. The basic concepts

| Concept | Meaning |
| --- | --- |
| Tenant | Isolated organization context derived from your authenticated identity. |
| User | Human identity managed by the REST API. |
| Service account | Non-human identity for CI/CD or shared automation. |
| Project | Logical software system identified by a stable `project_key`. |
| Environment | Deployment target such as development, staging, or production. |
| Snapshot | Immutable graph state published for one project and environment version. |
| Entity | A known project, system, service, API, event, library, or team. |
| Relation | A typed connection such as `depends_on`, `owned_by`, or `consumes`. |
| Evidence | Source, excerpt, and optional relation reference supporting a fact. |
| MCP resource | Read-only URI exposing bounded project, entity, or snapshot context. |

Projects and environments are created by the first trusted publication. Users and tokens
are created through the REST management API. MCP resources are read-only views; they are
not registered with a separate create-resource request.

## 3. Getting access

Ask your platform administrator for:

1. MCP URL, for example `https://mcp.example.com/mcp`.
2. A user-owned API token.
3. `memory:read` for normal questions.
4. `memory:impact` when you need change-impact analysis.

The administrator must not send you `API_ADMIN_TOKEN`. That credential manages users,
service accounts, and tokens. It is not a user or MCP credential.

The token plaintext is shown once when created. Store it in your password manager or the
secret store approved by your organization. Do not put it in a repository, ticket, prompt,
chat message, or shared screenshot.

## 4. Administrator onboarding

This section is for a platform administrator setting up a human user. Management calls
require `API_ADMIN_TOKEN`.

```bash
export API_BASE_URL='https://memory-api.example.com'
export API_ADMIN_TOKEN='replace-with-admin-secret'
```

### 4.1 Create the user

```bash
curl --fail --request POST "$API_BASE_URL/v1/users" \
  --header "Authorization: Bearer $API_ADMIN_TOKEN" \
  --header 'Content-Type: application/json' \
  --data '{"name":"Example User","email":"example.user@example.com"}'
```

Copy the returned user `id` as `<USER_ID>`. Email addresses are normalized to lowercase
and must be unique.

### 4.2 Create a read token

User tokens require an expiration. A finite expiration cannot exceed 90 days from
issuance.

```bash
curl --fail --request POST "$API_BASE_URL/v1/tokens" \
  --header "Authorization: Bearer $API_ADMIN_TOKEN" \
  --header 'Content-Type: application/json' \
  --data '{
    "user_id":"<USER_ID>",
    "name":"Example user MCP access",
    "expires_at":"2026-12-15T23:59:59Z",
    "scopes":["memory:read"]
  }'
```

For impact analysis, issue both scopes:

```json
"scopes": ["memory:read", "memory:impact"]
```

Return the create response to the user through an approved secure channel. The API
stores only a SHA-256 digest and never returns the plaintext again.

### 4.3 Create a service-account token instead

Use a service account for automation, not a personal user token. The service account
requires an organization-approved tenant UUID:

```bash
curl --fail --request POST "$API_BASE_URL/v1/service-accounts" \
  --header "Authorization: Bearer $API_ADMIN_TOKEN" \
  --header 'Content-Type: application/json' \
  --data '{
    "name":"Project publication automation",
    "tenant_id":"<TENANT_UUID>"
  }'
```

Copy the returned account `id` as `<SERVICE_ACCOUNT_ID>`, then issue its token:

```bash
curl --fail --request POST "$API_BASE_URL/v1/tokens" \
  --header "Authorization: Bearer $API_ADMIN_TOKEN" \
  --header 'Content-Type: application/json' \
  --data '{
    "service_account_id":"<SERVICE_ACCOUNT_ID>",
    "name":"Project publication token",
    "scopes":["memory:publish"]
  }'
```

Service-account tokens may omit `expires_at`, but finite expiry and regular rotation are
recommended. `memory:publish` is for the REST publication pipeline; it does not provide
MCP read access unless `memory:read` is also issued.

## 5. Configure your LLM client

Set the token in the environment visible to the client:

```bash
export HARNESS_MEMORY_TOKEN='replace-with-your-user-token'
```

### Codex

Add this to `~/.codex/config.toml`:

```toml
[mcp_servers.harness-memory]
url = "https://mcp.example.com/mcp"
bearer_token_env_var = "HARNESS_MEMORY_TOKEN"
```

Then restart Codex and check `/mcp` or `codex mcp list`.

### Claude Code

Add this to the approved `.mcp.json`:

```json
{
  "mcpServers": {
    "harness-memory": {
      "type": "http",
      "url": "https://mcp.example.com/mcp",
      "headers": {
        "Authorization": "Bearer ${HARNESS_MEMORY_TOKEN}"
      }
    }
  }
}
```

Local Docker Compose uses `http://localhost:8000/mcp`. Production deployments must use
the HTTPS address supplied by the platform team.

## 6. Ask questions in natural language

State the project and environment when known. Ask the LLM to search first and show
evidence. These examples can be copied and adapted.

### Discover a project

```text
Use Harness Memory. In project com.example.payments, find the services related to
checkout. Return names, types, entity IDs, owners, and source evidence. Search first and
state whether the result is truncated.
```

### Understand one service

```text
Use Harness Memory to inspect the Checkout API in project com.example.payments.
Summarize its owner, inbound consumers, outbound dependencies, relation provenance, and
evidence. Separate stored facts from assumptions.
```

### Find dependencies

```text
Which systems consume the Payments API? Search the project first, then inspect inbound
dependencies. Include relation types, evidence, and unknowns.
```

### Review impact

```text
Before changing the Payments API contract, identify direct and indirect consumers.
Changed fields: currency and payment_status.
Description: payment_status will become a controlled enum.
Return affected projects, teams, paths, evidence, and missing knowledge. Do not guess.
```

Impact analysis requires `memory:impact`. If the client reports insufficient scope, ask an
administrator for a new token instead of using an admin credential.

### Compare environments

```text
Compare the active snapshots for project com.example.payments between staging and
production. Show added, removed, modified, and unchanged entities. Include the snapshot
or version context and explain missing data.
```

### Verify an active deployment

```text
What snapshot is active for com.example.payments in production? Return the environment,
current snapshot ID, and then inspect the snapshot resource for available version,
publication context, and evidence of freshness.
```

## 7. Projects, environments, and resources

There are three registration paths:

### Project and environment

DevOps publishes a complete snapshot with `project_key`, `environment`, `deployment_id`,
and `version`. The API creates the project and environment if they do not exist. The
first successful publication activates the snapshot.

Users cannot create a project from an MCP conversation. Ask the project owner or DevOps
operator to run the SDK publication pipeline.

### Entities, relations, and evidence

The SDK's local LLM synthesizes a graph from repository context. The SDK validator checks
schema version, entity types, relation endpoints, provenance, uniqueness, and size
limits. The API stores the complete snapshot atomically.

Do not ask a developer to add one isolated graph fact manually. Correct the source or
publisher input and publish a new complete snapshot.

### MCP resources

After a snapshot is active, the MCP catalog can expose:

| Resource | Use |
| --- | --- |
| `memory://projects/{project_key}` | Read active project facts. |
| `memory://entities/{entity_id}` | Read one entity's bounded context. |
| `memory://snapshots/{snapshot_id}` | Inspect a tenant-owned historical snapshot. |
| `memory://schema/entities` | Understand valid entity fields, when available. |
| `memory://schema/relations` | Understand valid relationship fields, when available. |
| `memory://schema/snapshot` | Understand snapshot structure, when available. |

Resources are read-only. Their absence normally means the project has no active snapshot,
the key is wrong, or the token belongs to another tenant.

## 8. Understand answers and limitations

Harness Memory returns bounded stored knowledge, not a guarantee about the entire company.
Use these rules:

- A result with evidence is stronger than an unsupported statement.
- `declared`, `observed`, `inferred`, and `manual` provenance have different confidence
  meanings; ask the LLM to show which one applies.
- `unknowns` or `truncated: true` means the result is incomplete.
- An empty integration path does not prove that no integration exists.
- A missing environment may mean that no snapshot has been published there.
- An old active snapshot may not reflect the current code or production state.
- High-risk changes still require source, owner, security, and operational review.

Ask the LLM to use phrases such as “the active snapshot records” and “the graph does not
establish” instead of presenting guesses as facts.

## 9. Token lifecycle for users

When a token expires or is suspected to be exposed:

1. Stop using the old token.
2. Ask an administrator to issue a replacement with the minimum scopes.
3. Update `HARNESS_MEMORY_TOKEN` in the client environment.
4. Restart the LLM client if it caches environment variables.
5. Ask the administrator to delete the old token.

The administrator can list token metadata without seeing plaintext:

```bash
curl --fail "$API_BASE_URL/v1/tokens?user_id=<USER_ID>" \
  --header "Authorization: Bearer $API_ADMIN_TOKEN"
```

Never put a token in a bug report. Report the time, client, project, and suspected scope
without including the credential itself.

## 10. Common problems

| Problem | Meaning | Next action |
| --- | --- | --- |
| Client cannot connect | URL, process, or transport problem | Check MCP URL, server health, and client config. |
| `401 Unauthorized` | Token missing, expired, revoked, or invalid | Request a replacement token. |
| `403 Forbidden` | Token lacks requested scope | Request `memory:read` or `memory:impact`. |
| Search returns nothing | Wrong project, tenant, filter, or no publication | Verify project key and ask DevOps to check publication. |
| Result is truncated | Bounded response reached its limit | Narrow the query or ask the LLM to paginate. |
| Snapshot is stale | Pipeline has not published recent deployment | Ask the owner to publish the current version. |
| Project resource is missing | No active snapshot or incorrect URI encoding | Verify key and current environment snapshot. |

## Related documentation

- [Workflow README](./README.md): Global workflow and operating model.
- [Developer Playbook](./PLAYBOOK-DEVELOPER.md): Detailed MCP and investigation patterns.
- [DevOps Playbook](./PLAYBOOK-DEVOPS.md): Pipeline, credential, and publication operations.
- [API README](../../api/README.md): Endpoint and credential contracts.
- [MCP README](../../harness_memory_mcp/README.md): Client connection and catalog reference.
