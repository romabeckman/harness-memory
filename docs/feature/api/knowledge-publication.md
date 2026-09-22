---
doc_type: feature
domain: api-knowledge-publication
stack: [Python 3.12+, FastAPI, Pydantic 2.x, SQLAlchemy 2.x, PostgreSQL]
node_id: "feature:api-knowledge-publication"
tags: [api, publication, environments, snapshots, ci-cd]
edges:
  - relation: implements
    target: "adr:architecture"
    read: must
  - relation: references
    target: "adr:api"
    read: must
  - relation: tested_by
    target: "adr:tests"
    read: must
  - relation: depends_on
    target: "feature:environment-snapshots"
    read: must
  - relation: depends_on
    target: "feature:snapshot-publication"
    read: optional
    when: "Read when changing snapshot construction, activation, idempotency, or publication persistence."
updated: 2026-09-21
---
# API Knowledge Publication
Accept a CI/CD deployment declaration, build a knowledge snapshot, and activate it for a project environment.

```graph
{
  "node_id": "feature:api-knowledge-publication",
  "domain": "api-knowledge-publication",
  "implements": ["adr:architecture"],
  "tested_by": ["adr:tests"],
  "entrypoints": ["api/adapters/http/knowledge_publication_routes.py"],
  "registration_files": ["api/server/app.py"],
  "reference_files": [
    "api/adapters/http/api_security.py",
    "core/application/knowledge_publication/use_cases/publish_knowledge/handler.py",
    "core/infrastructure/postgres/repositories/knowledge_publication_repository.py",
    "core/infrastructure/postgres/repositories/environment_repository.py"
  ],
  "code_files": [
    "api/adapters/http/schemas/knowledge_publication_request.py",
    "api/adapters/http/schemas/knowledge_publication_response.py",
    "core/application/knowledge_publication/use_cases/publish_knowledge/inbound.py",
    "core/application/knowledge_publication/use_cases/publish_knowledge/outbound.py",
    "core/domain/knowledge_publication/aggregates/knowledge_publication.py",
    "core/domain/knowledge_publication/types/publication_status.py",
    "core/domain/knowledge_publication/value_objects/deployment_id.py",
    "core/domain/knowledge_publication/value_objects/publication_id.py",
    "core/infrastructure/postgres/models/knowledge_publication.py",
    "core/infrastructure/postgres/models/environment.py",
    "migrations/versions/008_create_environments_and_publications.py",
    "migrations/versions/009_token_scopes_and_environment_revisions.py"
  ],
  "test_files": [
    "tests/unit/api/adapters/http/test_knowledge_publication_routes.py",
    "tests/unit/api/adapters/http/test_api_authentication.py",
    "tests/unit/core/application/knowledge_publication/use_cases/test_publish_knowledge.py",
    "tests/unit/core/domain/knowledge_publication/test_knowledge_publication.py",
    "tests/unit/core/infrastructure/postgres/repositories/test_knowledge_publication_repository.py"
  ]
}
```

## OVERVIEW

Expose `POST /v1/knowledge-publications` as the deterministic CI/CD write boundary. The handler resolves the target environment, records the deployment, creates a snapshot, and promotes the environment pointer atomically.

## FOLDER STRUCTURE

```text
api/adapters/http/                         # Publication route and transport schemas
core/application/knowledge_publication/   # Input, output, and publish handler
core/domain/{environment,knowledge_publication}/ # Publication invariants and events
core/infrastructure/postgres/             # Environment/publication persistence
tests/{unit,integration}/                  # Route, use-case, domain, and repository checks
```

## HTTP CONTRACT

| Item | Contract |
|------|----------|
| Method and path | `POST /v1/knowledge-publications` |
| Header | Required `Authorization: Bearer <token>` with exact `memory:publish` scope. |
| Required fields | `project_key`, `environment`, `deployment_id`, `version` |
| Fact fields | `entities`, `relations`, `evidence`; default to empty arrays |
| New publication | HTTP 201 with status `ACTIVATED` |
| Completed retry | HTTP 200 with status `ALREADY_PUBLISHED` |
| Divergent retry | HTTP 409 when the same deployment ID carries different content. |
| Invalid facts | HTTP 422; entity, relation, and provenance fields are validated strictly. |
| Response | `status`, `publication_id`, `snapshot_id` |

## PUBLICATION RULES

REQUIRED: Resolve project and environment inside the trusted tenant context.
REQUIRED: Derive tenant identity from the token owner; never from headers or payloads.
REQUIRED: Create a missing project/environment pair on its first trusted publication.
REQUIRED: Use `(tenant, project, environment, deployment_id)` as the idempotency lookup.
REQUIRED: Return the existing publication and snapshot for a completed retry.
REQUIRED: Create and promote the snapshot in one persistence operation.
REQUIRED: Preserve deployment ID, version, publication ID, and snapshot ID.
PROHIBITED: Treat a deployment as active before environment resolution succeeds.
PROHIBITED: Let callers mutate individual graph facts through this route.

## SECURITY BOUNDARY

The publication credential is separate from `API_ADMIN_TOKEN`. Only an active API token
owned by a tenant-bound identity and carrying exactly `memory:publish` can publish. User
input cannot select or override the tenant.

## DOCUMENT MAP

```mermaid
graph TD
    PUBLICATION["API Knowledge Publication"] -->|implements| ARCH["Project Architecture"]
    PUBLICATION -->|references| API["API Architecture"]
    PUBLICATION -->|tested_by| TESTS["Testing Protocol"]
    PUBLICATION -->|depends_on| ENV["Environment Snapshots"]
    PUBLICATION -->|depends_on| SNAP["Snapshot Publication"]
    click ARCH "../../adr/ARCHITECTURE.md"
    click API "../../adr/API.md"
    click TESTS "../../adr/TESTS.md"
    click ENV "../core/environment-snapshots.md"
    click SNAP "../core/snapshot-publication.md"
```

## REFERENCES

- [**API.md**](../../adr/API.md): Defines API registration, versioning, and transport boundaries.
- [**TESTS.md**](../../adr/TESTS.md): Defines route and persistence verification tiers.
- [**environment-snapshots.md**](../core/environment-snapshots.md): Defines environment context and current snapshot behavior.
- [**snapshot-publication.md**](../core/snapshot-publication.md): Defines immutable snapshot and activation rules.
