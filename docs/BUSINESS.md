# Harness Memory — Product Objective

## OVERVIEW

Harness Memory is a corporate engineering memory platform. It connects software knowledge across repositories, projects, services, APIs, events, teams, dependencies, evidence, and ownership.

## PRODUCT OBJECTIVE

Make organizational software knowledge **discoverable, explainable, and reusable**. Preserve not only known facts, but also their evidence, provenance, lifecycle status, and revision history.

## BUSINESS VALUE

Use persistent corporate memory to reduce architectural rediscovery and improve engineering decisions. Support questions about API consumers, change impact, dependency ownership, evidence, and knowledge freshness.

## INTERFACE RULES

| Consumer | Interface | Responsibility |
|----------|-----------|----------------|
| Developer or AI agent | MCP Read | Query, compare, and analyze contextual knowledge. |
| CI/CD pipeline | Publish API or CLI | Declare a successful deployment and its evidence. |
| Authorized governance agent | Future MCP Write | Propose controlled knowledge refinement. |

REQUIRED: Separate interactive MCP reads from deterministic CI/CD publication.
REQUIRED: Keep pipeline publication independent from any CI/CD provider.
PROHIBITED: Use MCP as the initial pipeline publication path.
PROHIBITED: Treat discovered information as trusted corporate knowledge without evidence or governance.

## KNOWLEDGE LIFECYCLE

1. Deploy a project version to an environment.
2. Publish the successful deployment through the Publish API or CLI.
3. Validate project, environment, deployment identity, facts, and evidence.
4. Create a snapshot and promote it as the environment's current state.
5. Expose the contextual state through MCP queries and comparisons.

REQUIRED: Contextualize current knowledge by tenant, project, and environment.
REQUIRED: Create a traceable snapshot for each valid publication.
REQUIRED: Preserve publications, snapshots, evidence, provenance, status, and revision history.
REQUIRED: Make retries idempotent by deployment identity.
REQUIRED: Keep historical snapshots after a newer snapshot becomes current.
PROHIBITED: Assume one global current state when environments contain different versions.
PROHIBITED: Mutate individual graph facts outside complete publication or governed write flows.

## PRODUCT BOUNDARIES

The MVP combines an MCP interface for contextual knowledge access with a persistent database-backed memory layer. MCP Write remains a future capability and is not required for initial pipeline publication.

## CURRENT IMPLEMENTATION

The API accepts active user or service-account tokens for tenant-scoped reads and
complete snapshot publication. `memory:read` grants data reads; `memory:publish`
grants publication. API and MCP accept the same bearer token. `API_ADMIN_TOKEN` grants
full admin REST access. `HARNESS_MEMORY_API_KEY` grants global `memory:read` only. Other
credentials must match active rows in `tokens`, use stored scopes, and remain limited to
the token owner's tenant.

REQUIRED: Keep ordinary tokens tenant-bound and reserve management for the admin token.
PROHIBITED: Treat an unauthenticated tenant header or the default tenant as trusted authorization.

## REFERENCES

- `docs/specs/harness-memory-environment-snapshots-v2.md`: Product scope for environment snapshots and publication.
- `docs/feature/core/environment-snapshots.md`: Environment context, publication flow, and snapshot comparison.
- `docs/feature/core/snapshot-publication.md`: Immutable snapshot activation and history rules.
- `docs/feature/api/knowledge-publication.md`: Implemented REST publication contract.
