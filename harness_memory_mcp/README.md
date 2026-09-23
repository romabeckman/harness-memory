# Harness Memory MCP

The `harness_memory_mcp/` module exposes organizational engineering knowledge through
the Model Context Protocol (MCP). It is read-only: AI agents query known relationships,
compare environments, and analyze impact. The REST API owns publication and governance;
see the [`api/` module README](../api/README.md).

## Start the MCP server

From the repository root, start the full Docker Compose stack:

```bash
docker compose up --build
```

Compose starts PostgreSQL, applies database migrations, then starts the MCP server and REST API. The MCP endpoint is:

```text
http://localhost:8000/mcp
```

The server uses Streamable HTTP. For a remote deployment, use its HTTPS endpoint.

## Connect an MCP client

1. Create a user token or a tenant-bound service-account token through the REST API at `http://localhost:8080`. Use the same `API_TOKEN` bearer value for API and MCP. Follow the [API instructions](../api/README.md#create-an-mcp-credential).
2. Save the plaintext token from the token creation response. It is returned only once.
3. Configure your MCP client with the server URL and bearer token:

   - URL: `http://localhost:8000/mcp`
   - Header: `Authorization: Bearer <token>`

The server verifies the token against the database and derives its subject and tenant from its owner. User tokens use the user ID as tenant ID. Service-account tokens use the service account's assigned tenant ID. Do not send tenant identity in tool arguments. Keep the token private and revoke it through `DELETE /v1/tokens/{token_id}` when it is no longer needed.

## MCP catalog

### Tools

| Tool | Purpose |
| --- | --- |
| `search_projects` | Find project keys by exact key or partial key/name query, including projects without snapshots. |
| `search_entities` | Search active-snapshot entities by exact key/project, name prefix, type, or metadata phrase. |
| `get_context` | Read bounded context, relationships, and evidence for an entity. |
| `get_dependencies` | Query inbound or outbound dependencies. |
| `find_integration_paths` | Find known paths between engineering entities. |
| `analyze_impact` | Identify known direct and indirect effects of a structured change. |
| `get_environment` | Read an environment and its active snapshot. |
| `compare_environments` | Compare active entity fingerprints between environments. |

MCP clients cannot publish or make arbitrary graph edits. Impact results come from stored relationships and evidence; the server does not guess missing relationships.

### Resources

| URI | Content |
| --- | --- |
| `memory://entities/{entity_id}` | Entity context and bounded relationships. |
| `memory://projects/{project_key}` | Project facts from its active snapshot. |
| `memory://snapshots/{snapshot_id}` | Tenant-owned snapshot facts and metadata. |

Resource reads are tenant-scoped and bounded. URL-encode project keys that contain `/` so the key stays within one URI segment.

### Prompts

| Prompt | Purpose |
| --- | --- |
| `load_corporate_context` | Guide an agent through loading relevant organizational context. |
| `analyze_integration` | Guide integration and ownership research. |
| `review_change_impact` | Guide evidence review for a proposed change. |

Prompts provide guidance only. Tools and application services perform validation, authorization, and business operations.

## Authentication and configuration

Production HTTP requests require bearer authentication. Docker Compose uses database token authentication with tokens issued by the REST API.

| Variable | Purpose |
| --- | --- |
| `MCP_HOST` | Bind address. Defaults to `127.0.0.1`; Compose sets `0.0.0.0` inside the container. |
| `MCP_PORT` | HTTP port. Defaults to `8000`. |
| `MCP_AUTH_MODE` | `database` for API-issued tokens or `jwt` for an external identity provider. |
| `DATABASE_URL` | Shared PostgreSQL connection. Required for database token authentication. |
| `API_ADMIN_TOKEN` | Optional global administrator bearer token accepted by API and MCP. |
| `HARNESS_MEMORY_API_KEY` | Optional global bearer token with `memory:read` only. |
| `MCP_ISSUER` | HTTPS issuer URL for external JWT authentication. |
| `MCP_JWKS_URI` | HTTPS JWKS URL for external JWT authentication. |
| `MCP_AUDIENCE` | Expected JWT audience. |
| `MCP_TENANT_CLAIM` | JWT claim containing tenant identity. Defaults to `tenant_id`. |

When using JWT mode, configure the issuer, JWKS URL, audience, and tenant claim. Never trust tenant identity from a request payload. Database-mode MCP accepts user or service-account tokens with their issued scopes. `HARNESS_MEMORY_API_KEY` grants global `memory:read` only. `API_ADMIN_TOKEN` works in both modes with global admin access; MCP tool scope checks remain enforced.

The startup migration service applies schema changes before the server starts. The MCP server checks the schema version and does not run migrations automatically.

## Module layout

- `server/`: FastMCP server setup, component registration, and HTTP security.
- `tools/`: MCP tool adapters.
- `resources/`: MCP resource adapters.
- `prompts/`: deterministic agent guidance.
- `services/`: authentication, tenant context, authorization, auditing, and response mapping.
- `core/application/` and `core/domain/`: use cases and business rules called by the adapters.

Keep MCP adapters thin. Add business behavior in the appropriate application use case or domain service. Keep reads bounded and tenant-scoped, and include provenance or evidence where the result provides it.

## Contribute

Run the MCP unit and end-to-end tests from the repository root:

```bash
./venv/bin/python -m pytest tests/unit/mcp
./venv/bin/python -m pytest tests/e2e/mcp
```

On Windows, use `venv\Scripts\python.exe` in place of `./venv/bin/python`. See the [project README](../README.md) for environment setup and all test tiers, and [MCP architecture](../docs/adr/MCP.md) for the full interface contract.
