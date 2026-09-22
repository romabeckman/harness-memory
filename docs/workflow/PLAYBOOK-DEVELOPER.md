# Developer Playbook

Use Harness Memory through MCP to answer engineering questions with stored facts,
relationships, provenance, evidence, and environment context. This guide focuses on
connecting a developer tool and getting reliable answers through conversation with an
LLM.

## 1. What developers get

Harness Memory stores knowledge published from verified project snapshots. The MCP
server exposes bounded, tenant-scoped read operations:

- Find projects, services, APIs, events, libraries, teams, and other known entities.
- Read ownership, dependencies, relationships, provenance, and evidence.
- Trace integration paths between two entities.
- Analyze downstream impact of a proposed change.
- Read an environment's active snapshot.
- Compare active snapshots across environments.

MCP does not mutate projects, snapshots, entities, relations, or environments. CI/CD
publishes complete snapshots through the REST API and SDK.

## 2. Prerequisites

Ask a platform administrator for:

- MCP URL, for example `https://mcp.example.com/mcp` or `http://localhost:8000/mcp`.
- A user-owned API token with `memory:read`.
- `memory:impact` when you need change-impact analysis.

Never request or use `API_ADMIN_TOKEN` in an MCP client. It manages REST identities; it
does not authenticate MCP reads.

Set the plaintext API token in the process environment that starts your LLM client:

```bash
export HARNESS_MEMORY_TOKEN='replace-with-user-token'
```

The token is returned only once by the token-creation API. Do not commit it, put it in a
prompt, paste it into a repository, or include it in screenshots.

## 3. Configure an MCP client

### OpenAI Codex

Add this entry to `~/.codex/config.toml`:

```toml
[mcp_servers.harness-memory]
url = "https://mcp.example.com/mcp"
bearer_token_env_var = "HARNESS_MEMORY_TOKEN"
```

For local Docker Compose:

```toml
[mcp_servers.harness-memory]
url = "http://localhost:8000/mcp"
bearer_token_env_var = "HARNESS_MEMORY_TOKEN"
```

Restart Codex after changing its configuration. Verify the connection with `codex mcp
list` or `/mcp` in the Codex TUI.

### Claude Code

Add this server to the project `.mcp.json` or the approved user configuration:

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

Start Claude Code only after `HARNESS_MEMORY_TOKEN` is available in its parent process.
Use `/mcp` to confirm that the server is connected.

### Other MCP clients

Configure Streamable HTTP with:

```text
URL:    https://mcp.example.com/mcp
Header: Authorization: Bearer <user-token>
```

Use a secret-reference mechanism when the client supports one. Do not place the raw
token in a shared configuration file.

## 4. Understand scope boundaries

| Scope | Available capabilities |
| --- | --- |
| `memory:read` | Search, context, dependencies, integration paths, environments, comparisons, resources, and prompts. |
| `memory:impact` | Change-impact analysis. Request together with `memory:read` for normal investigation. |
| `memory:publish` | REST publication by a tenant-bound service account. Not an MCP write capability. |

The server derives subject and tenant from the verified token owner. Do not add a tenant
ID, tenant header, or tenant argument to an MCP request. A missing or invalid token gives
`401`; a valid token without the required scope gives `403`.

## 5. The conversation method

Give the LLM enough context to choose the correct project, environment, and question.
Use this sequence:

1. Name the project or repository.
2. Name the environment when the question concerns deployment state.
3. Ask the LLM to search before making a conclusion.
4. Ask it to inspect context, dependencies, evidence, or paths for returned entities.
5. Ask for unknowns, truncation, provenance, and evidence in the answer.
6. Ask it to distinguish stored facts from engineering judgment.

Reusable request template:

```text
Use Harness Memory for this investigation.
Project: <project-key>
Environment: <environment, if relevant>
Question: <specific engineering question>

Search first. Inspect the matching entities and evidence. State unknowns or truncated
results. Do not infer a relationship that the graph does not contain.
```

### Example: locate a service

```text
In project com.example.payments, find the service or API related to checkout.
Return entity IDs, names, types, owners, and evidence. Search before answering.
```

The LLM should use `search_entities` with a project and name/key filter, then use the
returned entity UUID with `get_context`.

### Example: inspect a dependency

```text
For the Checkout API in project com.example.payments, identify outbound dependencies.
Show relation type, target, provenance, evidence, and any truncated or unknown results.
```

The LLM should use `get_dependencies` with `direction: outbound`. Use `inbound` to find
consumers or `both` for a complete bounded view.

### Example: find an integration path

```text
Find evidence-backed paths from checkout-api to payments-event in project
com.example.payments. Limit the search to four hops and list ownership on each step.
```

The LLM needs the source and target entity UUIDs before calling
`find_integration_paths`. The server bounds depth, path count, owners, and evidence.

### Example: review a change

```text
Before changing the Payments API contract, analyze downstream impact.
Project: com.example.payments
Change type: contract
Changed fields: currency, payment_status
Description: Add currency and change payment_status from free text to an enum.

Return direct and indirect consumers, affected teams and projects, paths, evidence, and
unknowns. Do not claim no impact when data is missing or truncated.
```

The LLM should use `analyze_impact` with `memory:impact`. Impact analysis is evidence-led;
it does not guess consumers that are absent from the graph.

### Example: compare environments

```text
Compare project com.example.payments between staging and production.
Show added, removed, modified, and unchanged entities. Explain that the comparison uses
the active snapshot in each environment and call out missing environments.
```

The LLM should use `compare_environments`. A comparison is only meaningful when both
environments have an active snapshot.

### Example: inspect deployment state

```text
What is the active snapshot for com.example.payments in production?
Return environment metadata and current snapshot ID. Then read the snapshot resource for
available version, schema, fact, and publication context.
```

The LLM should use `get_environment`, then `memory://snapshots/{snapshot_id}` when a
snapshot ID exists. If no current snapshot exists, ask DevOps to verify the publication
pipeline rather than treating the environment as empty by design.

## 6. MCP catalog reference

### Tools

| Tool | Scope | Use it for |
| --- | --- | --- |
| `search_entities` | `memory:read` | Find entities by key, name, type, or project. At least one filter is required. |
| `get_context` | `memory:read` | Read one entity's project, owners, relations, dependencies, and evidence. |
| `get_dependencies` | `memory:read` | Read inbound, outbound, or both dependency directions. |
| `find_integration_paths` | `memory:read` | Find bounded evidence-backed paths between two entities. |
| `analyze_impact` | `memory:impact` | Analyze downstream consumers for a proposed change. |
| `get_environment` | `memory:read` | Read one project's environment and current snapshot. |
| `compare_environments` | `memory:read` | Compare active snapshots between two environments. |

Useful bounds:

- `get_context` and `get_dependencies`: result limit up to 100; default 25.
- `find_integration_paths`: depth up to 8; path count up to 25; default depth 4.
- `analyze_impact`: depth up to 8; consumers up to 500; result size up to 16 MiB.
- Resource reads: bounded facts and evidence; a truncation flag is meaningful.

Ask the LLM to narrow filters or paginate when a result is truncated. Large unbounded
requests reduce clarity and do not prove completeness.

### Resources

MCP resources are read-only projections created from published snapshots:

| URI | Meaning |
| --- | --- |
| `memory://entities/{entity_id}` | Entity context and bounded relationships. |
| `memory://projects/{project_key}` | Facts from the project's active snapshot. |
| `memory://snapshots/{snapshot_id}` | Tenant-owned snapshot facts and metadata. |
| `memory://schema/entities` | Entity schema reference, when registered. |
| `memory://schema/relations` | Relation schema reference, when registered. |
| `memory://schema/snapshot` | Snapshot schema reference, when registered. |

Percent-encode a project key containing `/` before placing it in a project resource URI.
Resources do not create or modify anything.

### Prompts

Use these deterministic prompts when the client exposes them:

- `load_corporate_context`: plan relevant context-loading searches.
- `analyze_integration`: guide entity, ownership, path, and evidence research.
- `review_change_impact`: guide impact and evidence review.

Prompts guide tool selection. They do not replace authorization, validation, or domain
logic.

## 7. Interpret evidence correctly

Treat every answer as a bounded view of stored knowledge:

- `declared`: explicitly provided by a source or publication.
- `observed`: recorded from an observation or runtime source.
- `inferred`: derived by the publisher from available context.
- `manual`: explicitly entered by an approved process.

Before relying on a relationship:

1. Check that it belongs to the expected project and tenant context.
2. Read provenance and evidence.
3. Check snapshot, environment, version, and freshness.
4. Note `unknowns`, missing evidence, and `truncated: true`.
5. Verify high-risk decisions against the source repository or contract.

Use precise language:

- “The active snapshot records…” for stored facts.
- “The result contains no known…” when the query is complete and bounded.
- “The result cannot establish…” when data is missing, stale, or truncated.
- “Engineering review is still required…” for decisions beyond graph evidence.

Never turn an empty path into proof that no integration exists. Never ask the LLM to
invent an owner, consumer, dependency, or impact.

## 8. Publication handoff

Developers do not publish through MCP. When knowledge is missing or stale:

1. Identify the project and environment.
2. Record the source repository, version, and deployment that should be represented.
3. Ask the service owner or DevOps operator to run the SDK publication pipeline.
4. Re-run the MCP query after the API returns `ACTIVATED` or `ALREADY_PUBLISHED`.

For a new project, the first trusted SDK publication creates the project/environment
pair. Graph resources become available after the snapshot is active.

## 9. Troubleshooting

| Symptom | Likely cause | Action |
| --- | --- | --- |
| MCP connection fails | Wrong URL, server down, or missing header | Check endpoint, health, and environment variable. |
| `401 Unauthorized` | Missing, expired, revoked, or unknown token | Ask admin for a replacement token. |
| `403 Forbidden` | Missing `memory:read` or `memory:impact` | Ask admin to issue the minimum required scope. |
| Search rejects request | No filter supplied | Include project, key, name, or type. |
| No matching entity | Wrong project, tenant, or snapshot | Verify key and environment; do not infer absence. |
| Result is truncated | Query exceeds bounds | Narrow filters or paginate. |
| Environment has no snapshot | Publication did not run or target is wrong | Ask DevOps to inspect publication output. |
| Project resource not found | No active snapshot or wrong encoded key | Verify project key and publication status. |

## Related documentation

- [Workflow README](./README.md): Cross-role workflow and registration model.
- [DevOps Playbook](./PLAYBOOK-DEVOPS.md): API, tokens, and SDK pipeline setup.
- [User Playbook](./PLAYBOOK-USER.md): Onboarding and non-technical usage.
- [MCP README](../../harness_memory_mcp/README.md): Runtime and client configuration.
- [MCP interface](../adr/MCP.md): Tool, resource, prompt, and scope contracts.
- [Security architecture](../adr/SECURITY.md): Authentication and tenant isolation.
