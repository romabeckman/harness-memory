# Daily Use Playbook

Use Harness Memory from Claude Code, Codex, Antigravity, or another MCP client to look up engineering context, assess changes, and publish verified project knowledge.

## Start the server

For local work, start PostgreSQL, migrations, and the MCP server with:

```sh
docker compose up --build
```

The local MCP endpoint is `http://localhost:8000/mcp`. Before first use, replace the example `MCP_ISSUER`, `MCP_JWKS_URI`, and `MCP_AUDIENCE` values in `docker-compose.yml` with your identity provider's settings. For a remote deployment, use its reachable HTTPS endpoint.

Configure the client with the endpoint and a bearer token. See the client examples in the root [README](../../README.md).

## Obtain an access token

Harness Memory does not issue tokens or provide a login page. Obtain an access token from the identity provider configured by `MCP_ISSUER` and `MCP_JWKS_URI`.

1. Register an OAuth client or service identity in your identity provider.
2. Grant the client only the Harness Memory scopes it needs.
3. Use the provider's supported flow to request an access token. Use the client credentials flow for unattended service automation when your provider allows it; use your organization's interactive flow for developer sessions. The exact command and token endpoint depend on the provider.
4. Configure the provider to issue `aud` matching `MCP_AUDIENCE`, a tenant identifier under the configured tenant claim, and the requested `scope` values. The provider must sign the JWT with RS256 and publish the matching public key through its JWKS endpoint.
5. Keep the token private. Put it in your client's secret store or environment variable; do not commit it to the repository.

The verified token needs a non-empty `sub`, a non-empty tenant claim, an accepted `iss` and `aud`, a valid expiry, and the scope claim. The default tenant claim is `tenant_id`; set `MCP_TENANT_CLAIM` when your provider uses another claim name.

| Scope | Use |
| --- | --- |
| `memory:read` | Search entities, read context, dependencies, paths, resources, and read prompts. |
| `memory:impact` | Analyze changes and review impact. |
| `memory:publish` | Publish project snapshots. |

Send the token as `Authorization: Bearer <access-token>`. Client configuration steps for Claude Code, Codex, and Antigravity are in the root [README](../../README.md).

## Read memory during a task

1. Search with `search_entities`. Supply at least one filter: entity `key`, name prefix, type, or project key. Use the returned entity UUID for follow-up calls.
2. Call `get_context` to inspect project, owner, relations, provenance, and evidence.
3. Call `get_dependencies` with `inbound`, `outbound`, or `both` to inspect direct dependency relations.
4. Call `find_integration_paths` with source and target entity UUIDs to trace a cross-project connection.
5. Call `analyze_impact` with the changed entity, change type, description, and affected fields before changing a shared contract or dependency.

Search returns entity identity, not relationship context. Search requires at least one filter. Follow `next_cursor` with the same filters when more results are available.

Review provenance and evidence before using a relationship to justify a decision. Treat an empty path as no known path in the active graph, not proof that no integration exists. Treat `unknowns` as knowledge gaps and `truncated: true` as incomplete analysis.

## Send project data to memory

Use `publish_project_snapshot` after verifying a change in the project's source records. Publication replaces the project's active snapshot atomically; send the complete current project snapshot, not only the changed rows. The authenticated token supplies tenant identity. Never add `tenant_id` to the request.

Call the tool with one `request` object. This example records an API-to-service dependency and links evidence to that relation:

```json
{
  "request": {
    "schema_version": "1.0",
    "project": {"key": "payments", "name": "Payments"},
    "revision": 2,
    "generated_at": "2026-09-20T12:00:00Z",
    "entities": [
      {"key": "payments-api", "type": "api", "name": "Payments API"},
      {"key": "billing-service", "type": "service", "name": "Billing Service"}
    ],
    "relations": [
      {
        "ref": "payments-api-consumes-billing",
        "source_entity_key": "payments-api",
        "type": "consumes",
        "target_entity_key": "billing-service",
        "provenance": "declared"
      }
    ],
    "evidence": [
      {
        "source": "openapi.yaml",
        "excerpt": "Payments API calls Billing Service to create charges.",
        "relation_ref": "payments-api-consumes-billing"
      }
    ]
  }
}
```

Use a positive revision, an offset-aware `generated_at` timestamp, supported entity and relation types, and evidence references that match relation `ref` values. Include all current entities, relations, and evidence for the project. The full request is limited to 10 MiB.

Check the result before retrying. `ACTIVATED` means the new snapshot became active. `ALREADY_PUBLISHED` means the same revision and content were already published. A stale revision or a changed payload at the same revision needs correction before publishing again.

## Use workflow prompts

Ask for `load_corporate_context` when starting work in an unfamiliar project. Use `analyze_integration` to trace a relationship and `review_change_impact` before a cross-project change. These prompts guide the assistant; the assistant still needs to call the tools and inspect their results.

## Troubleshoot common responses

| Result | Check |
| --- | --- |
| `401 Unauthorized` | Token expiry, issuer, audience, RS256 signing key, and JWKS URL. |
| `403 Forbidden` | The token lacks the scope required by that tool or resource. |
| No search results | Confirm a required filter and use the project's exact key or a name prefix. The entity may not exist in the active snapshot. |
| Entity not found | Confirm the UUID came from current search results; stale and inaccessible entities are intentionally indistinguishable. |
| `truncated: true` | The result is bounded. Narrow the query or raise supported limits, then rerun the analysis. |

Never report "no impact" when required graph data is missing or the result is truncated. Verify a relationship in its source system before publishing it as project knowledge.
