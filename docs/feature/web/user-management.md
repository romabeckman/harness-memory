---
doc_type: feature
domain: user-identity-management
stack: [TypeScript 5.x, Next.js 15, React 19, Vitest 1.6.x, Playwright]
node_id: "feature:web-user-management"
tags: [web, users, identity, tokens, tenants]
edges:
  - relation: implements
    target: "adr:architecture"
    read: must
  - relation: references
    target: "adr:api"
    read: must
  - relation: references
    target: "adr:security"
    read: must
  - relation: tested_by
    target: "adr:tests"
    read: must
  - relation: depends_on
    target: "feature:api-users"
    read: must
  - relation: depends_on
    target: "feature:api-tokens"
    read: must
  - relation: depends_on
    target: "feature:web-admin-token-management"
    read: must
updated: 2026-09-26
---
```graph
{"node_id":"feature:web-user-management","domain":"user-identity-management","implements":["adr:architecture"],"tested_by":["adr:tests"],"entrypoints":["web/src/app/users/page.tsx"],"registration_files":["web/src/components/admin-sidebar.tsx","web/src/app/actions/users.ts","web/src/app/actions/tokens.ts","web/src/application/ports/harness-api-client.port.ts","web/src/infrastructure/api/client-factory.ts"],"reference_files":["web/src/components/user-table.tsx","web/src/application/use-cases/issue-token.use-case.ts","api/application/services/user_service.py","core/infrastructure/postgres/repositories/api_user_repository.py"],"code_files":["web/src/components/user-dialog.tsx","web/src/components/confirm-delete-dialog.tsx","web/src/components/create-token-dialog.tsx","web/src/components/secret-reveal-modal.tsx","web/src/domain/access-token-order.ts","web/src/domain/user-token-owner.ts","web/src/domain/token-scope.ts","web/src/infrastructure/api/rest-harness-api-client.ts","web/src/middleware.ts","api/server/app.py","api/domain/entities/user.py","core/infrastructure/postgres/models/api_user.py"],"test_files":["web/tests/unit/components/user-management-components.test.ts","web/tests/unit/domain/user-management.test.ts","web/tests/unit/application/issue-user-token.use-case.test.ts","web/tests/unit/application/users.action.test.ts","web/tests/unit/infrastructure/rest-harness-api-client-users.test.ts","web/tests/e2e/user-management.spec.ts","tests/unit/api/adapters/http/test_api_authentication.py","tests/integration/api/infrastructure/test_repositories.py","tests/e2e/api/test_user_token_crud.py"],"knowledge":{"schema_version":1,"entities":[{"id":"capability:manage-users-page","type":"capability","label":"Manage users","definition":"List, create, edit, and delete users from the authenticated Web admin console.","aliases":["user management"]},{"id":"capability:issue-user-token","type":"capability","label":"Issue a user-owned token","definition":"Create an expiring access token from a selected user row.","aliases":[]},{"id":"rule:locked-user-owner","type":"rule","label":"Locked user owner","definition":"Keep the row-selected user as the sole owner throughout the token creation flow.","aliases":[]},{"id":"rule:delete-warning-confirmation","type":"rule","label":"User deletion confirmation","definition":"Require explicit confirmation after warning that all owned tokens will be permanently revoked.","aliases":[]},{"id":"decision:dedicated-users-page","type":"decision","label":"Dedicated Users page","definition":"Keep human-user management separate from service-account management.","aliases":[]},{"id":"contract:users-rest-operations","type":"contract","label":"User REST operations","definition":"Use existing paged global GET and CRUD operations under /v1/users.","aliases":[]}],"claims":[{"id":"claim:dedicated-global-user-management","subject":"capability:manage-users-page","relation":"governed_by","object":"decision:dedicated-users-page","statement":"The accepted feature scope provides a dedicated Users page with a global list and create, edit, and delete actions.","kind":"requirement","status":"supported","evidence":[{"kind":"specification","source":"docs/specs/user_identity_management/003-harness-memory-tactical-design.md","locator":"Refined Target Scope; Q01 and Q03 final answers","snapshot":null}],"derived_from":[],"gap":null},{"id":"claim:existing-user-rest-contract","subject":"capability:manage-users-page","relation":"depends_on","object":"contract:users-rest-operations","statement":"The Web page uses the existing GET /v1/users?q=&limit=&offset= and user CRUD operations; it sends only managed identity fields.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"web/src/infrastructure/api/rest-harness-api-client.ts","locator":"listUsers, createUser, updateUser, deleteUser","snapshot":null},{"kind":"code","source":"web/src/app/actions/users.ts","locator":"listUsersAction, createUserAction, updateUserAction, deleteUserAction","snapshot":null}],"derived_from":[],"gap":null},{"id":"claim:locked-user-token-owner","subject":"capability:issue-user-token","relation":"constrained_by","object":"rule:locked-user-owner","statement":"The row passes its user ID and name to the token dialog; the dialog has no owner selector, and AccessTokenOrder stores a frozen copy of that owner.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"web/src/app/users/page.tsx","locator":"onCreateToken callback","snapshot":null},{"kind":"code","source":"web/src/components/create-token-dialog.tsx","locator":"userOwner controls and createTokenAction call","snapshot":null},{"kind":"code","source":"web/src/domain/access-token-order.ts","locator":"resolveOwner","snapshot":null}],"derived_from":[],"gap":null},{"id":"claim:user-tenant-binding-preserved","subject":"capability:issue-user-token","relation":"depends_on","object":"feature:api-users#contract:user-tenant-binding","statement":"User-owned token requests contain user_id without tenant_id; selecting a tenant loads its projects and sends only selected project keys.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"web/src/components/create-token-dialog.tsx","locator":"tenant project request and createTokenAction payload","snapshot":null},{"kind":"code","source":"core/infrastructure/postgres/repositories/api_user_repository.py","locator":"ApiUserRepository.add","snapshot":null}],"derived_from":[],"gap":null},{"id":"claim:user-token-api-rules","subject":"capability:issue-user-token","relation":"constrained_by","object":"feature:api-tokens#rule:token-owner-and-lifetime","statement":"The Web token order accepts user lifetimes of 30 or 90 days and keeps Never Expires available only for service-account owners.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"web/src/domain/access-token-order.ts","locator":"validateLifetime","snapshot":null},{"kind":"code","source":"web/src/components/create-token-dialog.tsx","locator":"user lifetime controls","snapshot":null}],"derived_from":[],"gap":null},{"id":"claim:cascade-warning-before-delete","subject":"capability:manage-users-page","relation":"constrained_by","object":"rule:delete-warning-confirmation","statement":"User deletion requires typing the user name after a warning that all owned tokens will be permanently revoked; the API user relationship cascades token deletion.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"web/src/components/user-table.tsx","locator":"handleDelete and ConfirmDeleteDialog props","snapshot":null},{"kind":"code","source":"core/infrastructure/postgres/models/api_user.py","locator":"ApiUser.tokens cascade relationship","snapshot":null}],"derived_from":[],"gap":null}]}}
```

# Web User Management
Manage global user CRUD and user-owned tokens.

The Users API applies search filters, email ordering, limit, and offset in PostgreSQL. The token dialog loads every page of a tenant's projects before offering explicit project grants.

## OVERVIEW

The authenticated Next.js console calls existing user and token REST operations through server actions. User DTOs expose only `id`, `name`, and `email`; creating a user does not create a tenant or project.

## FOLDER STRUCTURE

```text
web/src/{app/users,components,application,domain,infrastructure}/ # Route, UI, use cases, rules, REST
web/tests/{unit,e2e}/ # Web unit and browser journey tests
tests/{unit,integration,e2e}/ # API authority, persistence, and HTTP contracts
```

## USER MANAGEMENT FLOW

1. List global users in 20-row pages with debounced search; retain rows when refresh fails.
2. Create or edit name and email only; the API owns normalization, identity, and uniqueness.
3. Delete only after warning that all owned tokens will be permanently revoked and the operator types the user's name.
4. Start token creation from a row; lock its user, select all tenants or one tenant and its projects, choose scopes, then set 30-day or 90-day expiry.
5. Reveal plaintext once and clear it when the modal closes.

## TOKEN AND TENANT RULES

User token requests send `user_id` and project keys only. Empty project keys retain global access across all tenants and projects. Selecting a tenant loads that tenant's projects; selected project keys constrain access. The tenant choice itself is not a separate token grant.

REQUIRED: Keep user lifetime at 30 or 90 days and omit **Never Expires** for users.
REQUIRED: Keep token plaintext in the one-time reveal flow only.
REQUIRED: Leave token listing and revocation on **Tokens & Credentials**.
REQUIRED: Keep deletion confirmation explicit because the API cascades deletion to every owned token.

## SECURITY

The login session gates `/users`; server actions send `API_ADMIN_TOKEN` to the API. The browser never receives it. Management routes remain admin-only.

## TESTING

Web checks use `npm --prefix web run test` and `npm --prefix web run test:e2e`. API checks cover authority, token cascade, and ownership contracts.

## REFERENCES

- [**ARCHITECTURE.md**](../../adr/ARCHITECTURE.md): Defines the Web BFF and REST boundaries.
- [**API.md**](../../adr/API.md): Defines user and token management routes.
- [**SECURITY.md**](../../adr/SECURITY.md): Defines admin credential authority and isolation.
- [**users.md**](../api/users.md): Defines user normalization and tenant binding.
- [**tokens.md**](../api/tokens.md): Defines token ownership, expiry, and one-time plaintext.
- [**admin-token-management.md**](./admin-token-management.md): Defines Web session and token dialog patterns.
