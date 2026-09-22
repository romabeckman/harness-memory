# Daily Use Playbook

Use Harness Memory as a two-boundary system: the **API** governs users, tokens, tenants,
and CI/CD publication; the **MCP server** provides read-only engineering context to
developers and agents.

For first-time installation, follow [SETUP.md](./SETUP.md). This playbook assumes the
local or remote MCP endpoint and a valid token already exist.

## AUTHENTICATION MODEL

The API uses two credential classes:

| Credential | Scope | Use |
| --- | --- | --- |
| `API_ADMIN_TOKEN` | Management only | Create users, service accounts, and tokens. |
| API-issued token | Persisted exact scopes | Read MCP data or publish through the API. |

MCP derives `sub` and tenant identity from the token owner. Never send `tenant_id` in a
tool argument. Request only the scopes required for the task:

| Scope | Operations |
| --- | --- |
| `memory:read` | Search, context, dependencies, paths, environments, resources, and prompts. |
| `memory:impact` | Analyze downstream consumers and change impact. |
| `memory:publish` | REST publication only; MCP does not expose a write tool. |

## TOKEN TYPES AND BOUNDARIES

The codebase has one persisted **API access-token model** and one separate configuration
secret. “MCP token” describes where an API-issued token is used; it is not a third token
class in the database.

| Name | Where it is defined | Owner and tenant | Intended use |
| --- | --- | --- | --- |
| **User token** | `POST /v1/tokens` with `user_id`; stored in `tokens` | `User.id` is also the user tenant | Developer MCP reads and impact analysis; request an expiry. |
| **MCP token** | No separate model; any active API token sent as `Authorization: Bearer` to `/mcp` | `DatabaseTokenVerifier` loads the stored owner and scopes | Read-only MCP catalog access according to persisted scopes. |
| **Service-account token** | `POST /v1/tokens` with `service_account_id` | Immutable `ServiceAccount.tenant_id` | CI/CD publication with `memory:publish`; expiry may be omitted. |
| **`API_ADMIN_TOKEN`** | Environment configuration, compared by `ApiSecurity` | No database owner or tenant | REST management routes only; never use it for MCP or publication. |

The boundary is enforced in code: `api/server/app.py` applies `require_admin` to user,
service-account, and token management routers; `ApiSecurity.require_publisher` performs
an active database-token lookup and requires `memory:publish`; and
`DatabaseTokenVerifier` copies only the scopes persisted on the API token into the MCP
principal. `API_ADMIN_TOKEN` is not persisted and is not accepted by the MCP verifier.

REQUIRED: Use a user token with `memory:read` for interactive development.
REQUIRED: Use a tenant-bound service-account token with `memory:publish` for CI/CD writes.
PROHIBITED: Treat “MCP token” as an independent credential or use `API_ADMIN_TOKEN` in a
client configuration.

## READ MEMORY DURING DEVELOPMENT

1. Start with `search_entities`. Supply `key`, `name_prefix`, `entity_type`, or
   `project_key`; the query must include at least one filter.
2. Pass a returned entity UUID to `get_context` to inspect ownership, relations,
   provenance, and evidence.
3. Use `get_dependencies` with `inbound`, `outbound`, or `both` for direct relations.
4. Use `find_integration_paths` to trace a bounded route between two entity UUIDs.
5. Call `analyze_impact` before changing a shared contract, API, library, or dependency.
6. Use `get_environment` for one environment and `compare_environments` to inspect
   added, removed, modified, and unchanged entity fingerprints.

Search returns entity identity, not full relationship context. Follow `next_cursor` with
the same filters when a page is truncated. Treat `unknowns` or `truncated: true` as
missing evidence, never as proof that no impact exists.

## REVIEW EVIDENCE

- Confirm that the entity belongs to the expected project and tenant.
- Read provenance and evidence before treating a relationship as authoritative.
- Distinguish an empty path from an unavailable or truncated result.
- Verify important relationships in the source repository or contract before publication.
- Record the source, excerpt, and relation reference when publishing evidence.

## PUBLISH PROJECT KNOWLEDGE

Publish through `POST /v1/knowledge-publications` using a tenant-bound service-account
token with exactly `memory:publish`. Do not call a publication MCP tool and do not write
directly to PostgreSQL from a developer workflow.

1. Collect the complete current entity, relation, and evidence set from the project.
2. Choose a unique `deployment_id`, the target `environment`, and the artifact `version`.
3. Send the payload through the API without `tenant_id` or `X-Tenant-ID`.
4. Confirm the response status before retrying.

```jsonc
// CORRECT: REST publication owns tenant and environment governance
{
  "project_key": "payments",
  "environment": "staging",
  "deployment_id": "build-2026-09-21-001",
  "version": "1.4.0",
  "entities": [
    {"key": "payments-api", "type": "api", "name": "Payments API"}
  ],
  "relations": [],
  "evidence": []
}
```

The first trusted publication provisions a missing project/environment pair. An equivalent
retry returns `ALREADY_PUBLISHED`. Reusing a deployment ID with different facts returns
`409 Conflict`; fix the payload or use a new deployment ID.

## INTERPRET RESPONSES

| Result | Meaning and next action |
| --- | --- |
| `401 Unauthorized` | Token is missing, expired, revoked, or not recognized. Issue a new token. |
| `403 Forbidden` | The token lacks the exact scope required by the operation. |
| `404 Not Found` | The entity, environment, or snapshot is absent or outside the tenant. |
| `409 Conflict` | Deployment identity was reused with different content. Do not overwrite silently. |
| `422 Unprocessable Entity` | Correct unsupported entity/relation/provenance data or missing references. |
| `truncated: true` | Narrow filters or inspect another bounded page before making a decision. |

Never report “no impact” when graph data is missing, unknown, or truncated.

## LOCAL DEVELOPMENT LOOP

1. Start or reuse the Compose stack from [SETUP.md](./SETUP.md).
2. Query the current graph with a read-only `memory:read` token.
3. Implement the change in the project repository.
4. Run the matching unit, integration, and E2E tests.
5. Publish a complete snapshot from CI/CD when the project state is verified.
6. Compare staging and production, then run `analyze_impact` for changed shared entities.

```bash
# CORRECT: run the complete local test suite through the project virtual environment
./venv/bin/python -m pytest -q -p no:cacheprovider
```

## TROUBLESHOOTING

| Symptom | Check |
| --- | --- |
| Empty search page | Add a required filter, verify the project key, and check tenant ownership. |
| Environment appears empty | Confirm the environment has an active snapshot and the token can read it. |
| Modified content is not found | Compare the correct environment snapshots and inspect `modified_entities`. |
| Publication is rejected | Validate enums, entity keys, relation endpoints, evidence references, and token scope. |
| Client cannot connect | Confirm the `/mcp` URL, `Authorization` header, and server health endpoint. |

## REFERENCES

- [Developer Setup](./SETUP.md): first-time local installation and credential bootstrap.
- [API README](../../api/README.md): management and publication route contracts.
- [MCP README](../../harness_memory_mcp/README.md): catalog, resources, and authentication.
- [Project README](../../README.md): architecture, commands, and client configuration.
