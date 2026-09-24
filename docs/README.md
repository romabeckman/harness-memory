# Project Documentation

Index of project technical documentation for **harness-memory**. Use the links below to navigate project documents and graph topology.

## Documentation Index

| Document | Description | Reading |
|----------|-------------|----------|
| [**.digest.md**](./.digest.md) | Fast-path machine-readable orientation for stack, commands, and constraints. | **Mandatory** |
| [**.graph.json**](./.graph.json) | Macro relation graph for document topology and one-hop routing. | **Mandatory** |
| [**ARCHITECTURE.md**](./adr/ARCHITECTURE.md) | Global architecture, folder organization, and dependency rules. | **Mandatory** |
| [**API.md**](./adr/API.md) | FastAPI boundaries, route registration, persistence reuse, and token handoff. | Optional |
| [**SECURITY.md**](./adr/SECURITY.md) | Authentication, token boundaries, tenant isolation, and operational security controls. | Optional |
| [**MCP.md**](./adr/MCP.md) | MCP tools, resources, prompts, transport, and security boundaries. | Optional |
| [**TESTS.md**](./adr/TESTS.md) | Test tiers, commands, patterns, and coverage policy. | **Mandatory** |
| [**BUSINESS.md**](./BUSINESS.md) | Product objective and global rules for contextual corporate memory. | Optional |
| [**workflow/README.md**](./workflow/README.md) | Role-based setup, daily use, MCP conversations, credentials, and SDK publication. | Recommended |
| [**knowledge-reads.md**](./feature/api/knowledge-reads.md) | Scoped REST reads and filters, including reconstructed snapshot payloads. | Optional |
| [**knowledge-publication.md**](./feature/api/knowledge-publication.md) | REST publication, normalized snapshot persistence, and environment baselines. | Optional |
| [**scopes.md**](./feature/api/scopes.md) | API and MCP scope permissions, credential boundaries, and current route exceptions. | Optional |
| [**service-accounts.md**](./feature/api/service-accounts.md) | Tenant-bound automation identities and their lifecycle rules. | Optional |
| [**tokens.md**](./feature/api/tokens.md) | Opaque token issuance, storage, revocation, and MCP handoff. | Optional |
| [**users.md**](./feature/api/users.md) | User identity, normalization, tenant derivation, and CRUD contract. | Optional |
| [**entity-discovery.md**](./feature/core/entity-discovery.md) | Project listing, filtered lookup, and bounded entity discovery from current environment snapshots. | Optional |
| [**environment-snapshots.md**](./feature/core/environment-snapshots.md) | Environment context, pipeline publication, and snapshot comparison. | Optional |
| [**impact-analysis.md**](./feature/core/impact-analysis.md) | Structured change-impact analysis over bounded consumers. | Optional |
| [**integration-paths.md**](./feature/core/integration-paths.md) | Bounded dependency path discovery with provenance. | Optional |
| [**platform-foundation.md**](./feature/core/platform-foundation.md) | PostgreSQL foundation, migrations, and platform runtime boundaries. | Optional |
| [**production-delivery.md**](./feature/core/production-delivery.md) | Containers, startup schema gates, CI, and telemetry. | Optional |
| [**relationship-context.md**](./feature/core/relationship-context.md) | Tenant-scoped entity context, ordered context listings, and dependency queries. | Optional |
| [**snapshot-publication.md**](./feature/core/snapshot-publication.md) | Immutable normalized snapshots, payload reconstruction, hashing, and activation. | Optional |
| [**tenant-foundation.md**](./feature/core/tenant-foundation.md) | First-class tenant persistence, strict UUID foreign keys, and isolated provisioning. | Optional |
| [**mcp-access-surface.md**](./feature/mcp/mcp-access-surface.md) | MCP resources and deterministic workflow prompts. | Optional |
| [**tenant-security.md**](./feature/mcp/tenant-security.md) | Tenant isolation, scopes, audit behavior, and security policy. | Optional |
| [**token-authentication.md**](./feature/mcp/token-authentication.md) | Database-backed bearer authentication for MCP clients. | Optional |
| [**snapshot-publisher.md**](./feature/sdk/snapshot-publisher.md) | SDK target preflight, publication, document comparison, and line-level revision history. | Optional |

## Recommended Reading Order

If an exact path is supplied, read it directly. Otherwise use this order:

1. **.digest.md** — fast AI orientation for architecture, stack, commands, and rules.
2. **.graph.json** — macro document graph for one-hop document lookup.
3. **ARCHITECTURE.md** and **TESTS.md** — foundational project constraints.
4. Read the selected ADR or feature document only when its design context is required.
