# Harness Memory Workflow

This directory contains practical guides for operating Harness Memory. Start here when
you need to install the platform, configure a pipeline, connect an MCP client, or ask
engineering questions through an LLM.

## Choose a guide

| Audience | Start here | Main outcome |
| --- | --- | --- |
| DevOps | [PLAYBOOK-DEVOPS.md](./PLAYBOOK-DEVOPS.md) | Prepare API/MCP, credentials, CI/CD, and SDK publication. |
| Developer | [PLAYBOOK-DEVELOPER.md](./PLAYBOOK-DEVELOPER.md) | Connect MCP and investigate projects, dependencies, and impact. |
| Common user | [PLAYBOOK-USER.md](./PLAYBOOK-USER.md) | Ask questions through an LLM and understand evidence and limitations. |
| Everyone | This README | Understand the complete daily operating model. |

Additional technical references:

- [SETUP.md](./SETUP.md): First-time local installation and credential bootstrap.
- [SDK README](../../sdk/README.md): CLI, configuration, dry runs, and programmatic use.
- [API README](../../api/README.md): REST management and publication endpoints.
- [MCP README](../../harness_memory_mcp/README.md): MCP catalog, transport, and runtime configuration.
- [Security architecture](../adr/SECURITY.md): Token, scope, tenant, and secret rules.
- [API architecture](../adr/API.md): REST boundaries and credential handoff.
- [MCP interface](../adr/MCP.md): Tools, resources, prompts, and scopes.
- [Knowledge publication](../feature/api/knowledge-publication.md): CI/CD publication contract.
- [Environment snapshots](../feature/core/environment-snapshots.md): Environment lifecycle and comparison.
- [Snapshot publication](../feature/core/snapshot-publication.md): Immutable snapshot and idempotency rules.

## Global operating model

Harness Memory is a governed knowledge lifecycle, not a free-form document store:

```text
Administrator provisions identities and credentials
        |
DevOps publishes a complete project snapshot after deployment
        |
API validates tenant, project, environment, facts, and evidence
        |
MCP exposes bounded read-only context to developers and LLMs
        |
Users ask questions, inspect evidence, and request impact analysis
```

The platform has two deliberate boundaries:

| Boundary | Responsibility | Write access |
| --- | --- | --- |
| REST API | Manage users, service accounts, tokens, and CI/CD publications. | Management and complete snapshot publication. |
| MCP over Streamable HTTP | Search, inspect, compare, and analyze stored knowledge. | Read-only. |

MCP cannot create projects, users, tokens, resources, graph facts, or snapshots. The
first trusted publication creates a project and environment pair. MCP resources then
read the active or historical snapshot; they are not independent records to register.

Never publish through MCP. Never mutate individual graph facts in PostgreSQL.

## First-use sequence

1. DevOps starts PostgreSQL, runs explicit migrations, and starts the API and MCP server.
2. An administrator sets `API_ADMIN_TOKEN`, verifies API health, and tests MCP connectivity.
3. The administrator creates a human user or a tenant-bound service account.
4. The administrator issues a least-privilege API token and stores its plaintext once.
5. The developer or user configures an MCP client with the MCP URL and token.
6. DevOps runs the SDK after a successful deployment with stable project and environment
   identifiers.
7. Developers and users query the active snapshot and verify provenance, evidence,
   freshness, and unknowns.

Use these scopes:

| Scope | Use |
| --- | --- |
| `memory:read` | Search, context, dependencies, paths, environments, comparisons, resources, and prompts. |
| `memory:impact` | Analyze downstream consumers and change impact. |
| `memory:publish` | REST publication by a tenant-bound service account. MCP has no write tool. |

## Register users and generate tokens

Management routes require the separate `API_ADMIN_TOKEN`. Never use it as an MCP or SDK
publication token.

```bash
export API_BASE_URL='http://localhost:8080'
export API_ADMIN_TOKEN='replace-with-admin-secret'
```

### Human user

```bash
curl --fail --request POST "$API_BASE_URL/v1/users" \
  --header "Authorization: Bearer $API_ADMIN_TOKEN" \
  --header 'Content-Type: application/json' \
  --data '{"name":"Example User","email":"example@example.com"}'
```

Copy the returned `id` as `<USER_ID>`, then create an expiring read token:

```bash
curl --fail --request POST "$API_BASE_URL/v1/tokens" \
  --header "Authorization: Bearer $API_ADMIN_TOKEN" \
  --header 'Content-Type: application/json' \
  --data '{
    "user_id":"<USER_ID>",
    "name":"Example MCP access",
    "expires_at":"2026-12-15T23:59:59Z",
    "scopes":["memory:read", "memory:impact"]
  }'
```

User tokens require `expires_at`; finite lifetime cannot exceed 90 days. Plaintext is
returned only in the creation response. Store it in a secret manager or private client
environment.

### CI service account

Use an organization-approved tenant UUID. Do not invent one or pass tenant identity to
MCP or publication payloads.

```bash
curl --fail --request POST "$API_BASE_URL/v1/service-accounts" \
  --header "Authorization: Bearer $API_ADMIN_TOKEN" \
  --header 'Content-Type: application/json' \
  --data '{
    "name":"Project publication automation",
    "tenant_id":"<TENANT_UUID>"
  }'
```

Use the returned account ID to create its publication token:

```bash
curl --fail --request POST "$API_BASE_URL/v1/tokens" \
  --header "Authorization: Bearer $API_ADMIN_TOKEN" \
  --header 'Content-Type: application/json' \
  --data '{
    "service_account_id":"<SERVICE_ACCOUNT_ID>",
    "name":"CI publication",
    "expires_at":"2026-12-15T23:59:59Z",
    "scopes":["memory:publish"]
  }'
```

Service-account tokens may omit `expires_at`, but finite expiry and regular rotation are
recommended. Store plaintext as `HARNESS_MEMORY_API_TOKEN` in the CI secret store.

## Register projects, environments, and resources

There is no standalone `POST /v1/projects` route. The first trusted SDK publication
creates the missing project and environment:

```text
project_key:   com.example.payments
environment:   staging
deployment_id: build-2026-09-22-001
version:       <commit SHA or release version>
```

The SDK sends complete `entities`, `relations`, and `evidence` arrays. The API validates
the payload, creates an immutable snapshot, and activates it for the selected environment.

Keep `project_key` and environment names stable. Use a unique `deployment_id` for every
CI execution. Repeating the same deployment with the same content returns
`ALREADY_PUBLISHED`; changing content under the same deployment identity returns `409
Conflict`.

MCP resources are read-only projections of published knowledge:

| URI | Meaning |
| --- | --- |
| `memory://projects/{project_key}` | Active facts for one project. |
| `memory://entities/{entity_id}` | Bounded context and relationships for one entity. |
| `memory://snapshots/{snapshot_id}` | Facts and metadata for one historical snapshot. |
| `memory://schema/entities` | Entity schema reference, when available. |
| `memory://schema/relations` | Relation schema reference, when available. |
| `memory://schema/snapshot` | Snapshot schema reference, when available. |

Do not register resources manually. If one is missing, verify tenant, project key, URI
encoding, active snapshot, publication status, and token scope.

## Daily work by role

### DevOps

- Check API health and MCP connectivity after deployment.
- Confirm database schema compatibility before serving traffic.
- Keep admin, user, and publication credentials separate.
- Publish through the SDK only after the target deployment succeeds.
- Capture JSON status, snapshot ID, version, counts, and payload hash.
- Treat `401`, `403`, `409`, and validation errors as actionable failures.
- Rotate tokens when runners, owners, or environments change.

### Developer

- Start with `search_entities` using a project, key, name, or type filter.
- Follow entity IDs with `get_context` and `get_dependencies`.
- Use `find_integration_paths` for a bounded route between entities.
- Use `analyze_impact` before changing shared contracts or dependencies.
- Use `get_environment` and `compare_environments` for deployment state.
- Read provenance, evidence, unknowns, and truncation before deciding.

### Common user

- State project and environment in every question when known.
- Ask the LLM to search first and show evidence.
- Ask it to distinguish stored facts from assumptions.
- Treat stale, empty, or truncated data as a request for verification.
- Ask the project owner or DevOps to publish missing knowledge.

## Daily conversation pattern

Use this prompt shape in any connected LLM:

```text
Use Harness Memory.
Project: <project-key>
Environment: <environment>
Question: <specific question>

Search first. Inspect context and evidence. State provenance, snapshot/version context,
unknowns, and truncation. Do not invent relationships that are not stored.
```

Good questions include:

```text
Find services related to checkout in project com.example.payments. Return owners,
dependencies, evidence, and any unknowns.
```

```text
Before changing the Payments API contract, analyze direct and indirect consumers.
Changed fields: currency and payment_status. Show paths, affected teams, evidence, and
missing knowledge. Do not guess.
```

```text
Compare the active snapshots for com.example.payments between staging and production.
Show added, removed, modified, and unchanged entities, with version context.
```

An empty path does not prove that no integration exists. A missing entity does not prove
that the system does not exist. Distinguish “no known result in this bounded snapshot”
from “no impact exists.”

## Evidence and freshness rules

Before relying on a relationship:

1. Confirm the expected project, environment, and tenant context.
2. Read provenance and evidence.
3. Check snapshot version and publication status.
4. Note `unknowns` and `truncated: true`.
5. Verify high-risk decisions against the source repository or contract.

Use “the active snapshot records…” for stored facts. Use “the graph does not establish…”
when evidence is missing. Do not ask the LLM to invent an owner, consumer, dependency,
or impact.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| MCP cannot connect | MCP URL, server status, bearer header, and client environment. |
| `401 Unauthorized` | Token missing, expired, revoked, or unknown. Issue a replacement. |
| `403 Forbidden` | Token lacks `memory:read` or `memory:impact`. Request the minimum scope. |
| Search returns nothing | Project key, tenant, required filter, and active snapshot. |
| Result is truncated | Narrow filters or paginate before making a decision. |
| Environment is empty | Confirm a snapshot was published for that environment. |
| Publication is rejected | Check schema, enums, endpoints, evidence refs, token, and deployment ID. |
| Project resource is missing | Verify project key encoding and current snapshot status. |

## Related documents

- [DevOps Playbook](./PLAYBOOK-DEVOPS.md)
- [Developer Playbook](./PLAYBOOK-DEVELOPER.md)
- [User Playbook](./PLAYBOOK-USER.md)
- [Setup guide](./SETUP.md)
- [SDK guide](../../sdk/README.md)
- [API guide](../../api/README.md)
- [MCP guide](../../harness_memory_mcp/README.md)
- [Security architecture](../adr/SECURITY.md)
- [API architecture](../adr/API.md)
- [MCP interface](../adr/MCP.md)
- [Knowledge publication contract](../feature/api/knowledge-publication.md)
- [Environment snapshots](../feature/core/environment-snapshots.md)
- [Snapshot publication](../feature/core/snapshot-publication.md)
