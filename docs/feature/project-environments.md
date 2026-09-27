---
doc_type: feature
domain: project_environments
stack: [Python 3.12+, FastAPI, SQLAlchemy, PostgreSQL, TypeScript 5.x, Next.js 15, React 19]
node_id: "feature:project-environments"
tags: [projects, environments, web, api, production]
edges:
  - relation: implements
    target: "adr:architecture"
    read: must
  - relation: tested_by
    target: "adr:tests"
    read: must
  - relation: references
    target: "feature:environment-snapshots"
    read: optional
    when: "Read when changing publication-created projects or environment snapshot behavior."
updated: 2026-09-27
---
```graph
{"node_id":"feature:project-environments","domain":"project_environments","implements":["adr:architecture"],"tested_by":["adr:tests"],"entrypoints":["web/src/components/project-table.tsx","api/adapters/http/tenant_project_management_routes.py"],"registration_files":["api/server/app.py","web/src/app/actions/projects.ts"],"reference_files":["web/src/components/project-environment-panel.tsx","core/infrastructure/postgres/repositories/environment_repository.py"],"code_files":["web/src/application/ports/harness-api-client.port.ts","web/src/infrastructure/api/rest-harness-api-client.ts","api/adapters/http/schemas/project_environment_create.py","api/application/services/project_environment_management_service.py","core/application/environment_context/ports/environment_repository.py","core/infrastructure/postgres/repositories/tenant_project_management_repository.py","core/domain/environment/value_objects/environment_name.py","core/domain/environment/value_objects/environment_type.py"],"test_files":["web/tests/unit/application/project-environments.action.test.ts","web/tests/unit/components/project-environment-panel.test.tsx","web/tests/unit/infrastructure/rest-harness-api-client-tenants-projects.test.ts","web/tests/e2e/admin-tenants-projects.spec.ts","tests/unit/api/adapters/http/test_tenant_project_routes.py","tests/unit/core/infrastructure/postgres/repositories/test_environment_repository.py","tests/unit/core/infrastructure/postgres/repositories/test_tenant_project_management_repository.py","tests/integration/core/infrastructure/postgres/repositories/test_project_environments.py"],"knowledge":{"schema_version":1,"entities":[{"id":"capability:manage-project-environments","type":"capability","label":"Manage project environments","definition":"View and add named environments for a selected tenant and project from the Projects page.","aliases":[]},{"id":"capability:create-project-production","type":"capability","label":"Create project with production","definition":"Give a newly created project a production environment.","aliases":[]},{"id":"rule:environment-name","type":"rule","label":"Environment name","definition":"Trim names; require 1–64 ASCII letters, digits, underscores, or hyphens; recognize exact standard names as their types.","aliases":[]},{"id":"rule:production-baseline","type":"rule","label":"Production baseline","definition":"Commit a production environment with each newly created project, without backfilling existing projects.","aliases":[]},{"id":"contract:environment-management-rest","type":"contract","label":"Environment management REST","definition":"List environments by tenant and project; create through admin-only POST /v1/projects/{project_key}/environments with tenant_id and name.","aliases":[]}],"claims":[{"id":"claim:manage-environments-scope","subject":"capability:manage-project-environments","relation":"exposes","object":"contract:environment-management-rest","statement":"Operators can view and add development, staging, production, or a custom name for a selected project; rename and removal are outside the approved scope.","kind":"requirement","status":"supported","evidence":[{"kind":"specification","source":"docs/specs/project_environments/003-harness-memory-tactical-design.md","locator":"Feature Boundary and Traceability; Q02 and Q03 human answers","snapshot":null}],"derived_from":[],"gap":null},{"id":"claim:name-validation","subject":"capability:manage-project-environments","relation":"constrained_by","object":"rule:environment-name","statement":"The create repository trims and validates names; exact standard names get matching types and other accepted names get type other.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"core/infrastructure/postgres/repositories/environment_repository.py","locator":"PostgresEnvironmentRepository.create_for_project: EnvironmentName and EnvironmentType","snapshot":null},{"kind":"code","source":"core/domain/environment/value_objects/environment_name.py","locator":"EnvironmentName validation","snapshot":null}],"derived_from":[],"gap":null},{"id":"claim:production-on-creation","subject":"capability:create-project-production","relation":"constrained_by","object":"rule:production-baseline","statement":"Explicit project creation and first-time publication materialization commit a production environment with the new project; existing projects are not backfilled.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"core/infrastructure/postgres/repositories/tenant_project_management_repository.py","locator":"PostgresTenantProjectManagementRepository.create_project: transaction and production row","snapshot":null},{"kind":"code","source":"core/infrastructure/postgres/repositories/environment_repository.py","locator":"PostgresEnvironmentRepository.resolve_or_create: inserted_project_id guard and production row","snapshot":null}],"derived_from":[],"gap":null},{"id":"claim:admin-create-boundary","subject":"capability:manage-project-environments","relation":"depends_on","object":"contract:environment-management-rest","statement":"The Projects panel calls server actions and the REST client; the create route resolves tenant and project, returning 404 for a missing project and 409 for a duplicate name.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"web/src/app/actions/projects.ts","locator":"listProjectEnvironmentsAction and addProjectEnvironmentAction","snapshot":null},{"kind":"code","source":"api/adapters/http/tenant_project_management_routes.py","locator":"create_project_environment route","snapshot":null}],"derived_from":[],"gap":null}]}}
```

# Project Environments

## OVERVIEW

The Projects page shows a selected project's environments and accepts standard or custom environment names. New projects start with **production** so publication and reads have an explicit environment baseline.

## FOLDER STRUCTURE

```text
web/src/{components,app/actions,application/ports,infrastructure/api}/ # Project panel, server actions, REST boundary
api/{adapters/http,application/services,server}/ # Admin route and application coordination
core/{domain/environment,application/environment_context,infrastructure/postgres}/ # Name rules, repository port, persistence
web/tests/{unit,e2e}/ # Component, action, client, and browser checks
tests/{unit,integration}/ # API and repository checks
```

## ENVIRONMENT MANAGEMENT

- **View:** Open a project's panel to load environments using both tenant ID and project key. The panel presents names and types.
- **Add:** Choose development, staging, production, or Other with a custom name. Preserve submitted custom text when creation fails.
- **Type:** Exact standard names map to matching types; accepted custom names map to `other` and retain their casing.
- **Conflict:** The database uniqueness constraint permits one name per tenant and project. Duplicate creation returns HTTP 409; missing project returns 404.

REQUIRED: Trim submitted names and apply the existing **EnvironmentName** rule: 1–64 ASCII letters, digits, underscores, or hyphens.
REQUIRED: Keep admin credentials in server actions and the REST client, outside browser code.
PROHIBITED: Present rename or removal as part of this feature.

## PRODUCTION BASELINE

REQUIRED: Create **production** within the same transaction as a new project, including first-time project materialization by publication.
REQUIRED: Preserve existing projects without a production backfill.

## KNOWN LIMIT

The Web environment list requests one page of at most 500 rows. Projects with more than 500 environments do not display later rows; this remains an observed limitation of the delivered view.

## REFERENCES

- [**ARCHITECTURE.md**](../adr/ARCHITECTURE.md): Defines Web, REST, and persistence boundaries.
- [**TESTS.md**](../adr/TESTS.md): Defines project test tiers and commands.
- [**environment-snapshots.md**](./core/environment-snapshots.md): Defines publication and environment snapshot context.
