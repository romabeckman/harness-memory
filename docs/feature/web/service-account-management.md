---
doc_type: feature
domain: service-account-management
stack: [TypeScript 5.x, Next.js 15, React 19, Vitest 1.6.x, Playwright]
node_id: "feature:web-service-account-management"
tags: [web, service-accounts, admin, tokens]
edges:
  - relation: implements
    target: "adr:architecture"
    read: must
  - relation: tested_by
    target: "adr:tests"
    read: must
  - relation: depends_on
    target: "feature:api-service-accounts"
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
{"node_id":"feature:web-service-account-management","domain":"service-account-management","implements":["adr:architecture"],"tested_by":["adr:tests"],"entrypoints":["web/src/app/service-accounts/page.tsx"],"registration_files":["web/src/components/admin-sidebar.tsx","web/src/app/actions/service-accounts.ts","web/src/application/ports/harness-api-client.port.ts","web/src/infrastructure/api/rest-harness-api-client.ts"],"reference_files":["web/src/components/create-token-dialog.tsx","web/src/components/confirm-delete-dialog.tsx","web/src/application/use-cases/issue-token.use-case.ts"],"code_files":["web/src/components/service-account-table.tsx","web/src/components/service-account-dialog.tsx","web/src/domain/access-token-order.ts","web/src/app/actions/tokens.ts","web/src/infrastructure/auth/session-manager.ts","web/src/middleware.ts"],"test_files":["web/tests/unit/domain/access-token-order.test.ts","web/tests/unit/application/service-accounts.action.test.ts","web/tests/unit/application/service-accounts-page.test.ts","web/tests/unit/infrastructure/rest-harness-api-client-service-accounts.test.ts","web/tests/unit/components/service-account-management-components.test.ts","web/tests/unit/application/issue-token.use-case.test.ts","web/tests/e2e/service-account-management.spec.ts","tests/unit/api/adapters/http/test_api_authentication.py","tests/e2e/api/test_user_token_crud.py"],"knowledge":{"schema_version":1,"entities":[{"id":"capability:manage-service-accounts","type":"capability","label":"Manage service accounts","definition":"Let an authenticated admin list, create, rename, delete, and issue tokens for service accounts from a dedicated Web page.","aliases":["service-account management"]},{"id":"rule:locked-service-account-owner","type":"rule","label":"Locked service-account owner","definition":"Keep the row-selected service account as the sole token owner while project access changes.","aliases":[]},{"id":"rule:immutable-service-account-organization","type":"rule","label":"Immutable service-account organization","definition":"Require organization on creation and omit organization changes from update payloads.","aliases":[]},{"id":"contract:service-account-bff","type":"contract","label":"Service-account BFF contract","definition":"Use server actions and a server-held API_ADMIN_TOKEN for paged list and CRUD operations.","aliases":[]},{"id":"decision:dedicated-service-accounts-page","type":"decision","label":"Dedicated service-accounts page","definition":"Keep service-account identity management separate from users and token listing.","aliases":[]}],"claims":[{"id":"claim:dedicated-admin-boundary","subject":"capability:manage-service-accounts","relation":"governed_by","object":"decision:dedicated-service-accounts-page","statement":"The Web console exposes service-account management at /service-accounts and keeps token listing on the existing credentials page.","kind":"requirement","status":"supported","evidence":[{"kind":"specification","source":"docs/specs/service_account_management/003-harness-memory-tactical-design.md","locator":"Q01 and Section 1 ServiceAccountsPage","snapshot":null},{"kind":"code","source":"web/src/app/service-accounts/page.tsx","locator":"ServiceAccountsPage route UI","snapshot":null}],"derived_from":[],"gap":null},{"id":"claim:server-held-management","subject":"capability:manage-service-accounts","relation":"exposes","object":"contract:service-account-bff","statement":"Service-account list and mutations call the injected REST client from server actions, sanitize boundary errors, and revalidate /service-accounts after successful mutations.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"web/src/app/actions/service-accounts.ts","locator":"listServiceAccountsAction, createServiceAccountAction, updateServiceAccountAction, deleteServiceAccountAction","snapshot":null},{"kind":"code","source":"web/src/infrastructure/api/rest-harness-api-client.ts","locator":"request and service-account REST methods","snapshot":null}],"derived_from":[],"gap":null},{"id":"claim:owner-lock-and-organization","subject":"capability:manage-service-accounts","relation":"constrained_by","object":"rule:locked-service-account-owner","statement":"A row-selected owner is copied into a frozen AccessTokenOrder owner and remains visible while global or organization-scoped project access changes.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"web/src/domain/access-token-order.ts","locator":"resolveOwner and validateLifetime","snapshot":null},{"kind":"code","source":"web/src/components/create-token-dialog.tsx","locator":"serviceAccountOwner branch and createTokenAction payload","snapshot":null},{"kind":"test_definition","source":"web/tests/unit/components/service-account-management-components.test.ts","locator":"locked service-account owner scenario","snapshot":null}],"derived_from":[],"gap":null},{"id":"claim:organization-immutability","subject":"capability:manage-service-accounts","relation":"constrained_by","object":"rule:immutable-service-account-organization","statement":"Create validation requires a nonblank organization and name; update sends a name-only payload; delete uses the API cascade warning flow.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"web/src/app/actions/service-accounts.ts","locator":"createServiceAccountAction and updateServiceAccountAction validation","snapshot":null},{"kind":"code","source":"web/src/components/service-account-dialog.tsx","locator":"create organization selector and edit organization display","snapshot":null},{"kind":"code","source":"web/src/components/confirm-delete-dialog.tsx","locator":"typed destructive confirmation","snapshot":null}],"derived_from":[],"gap":null}]}}
```

# Web Service Account Management

Manage tenant-bound automation identities on Next.js admin page. It lists and filters accounts, requires explicit organization selection, supports name-only edits, warns about token cascade deletion, and starts locked-owner token issuance.

## FOLDER STRUCTURE

```text
web/src/app/service-accounts/       # Dedicated route and page state
web/src/components/                 # Table, CRUD dialog, and token dialog reuse
web/src/app/actions/                # Server-only BFF operations
web/src/domain/                     # Immutable token-owner and lifetime rules
web/tests/{unit,e2e}/                # Contract, component, domain, and browser checks
```

## MAIN CONCEPTS / COMPONENTS

- **Global list:** Load 20 rows by default. The API applies filters and pagination in the database before materializing rows. Organization changes reset pagination; request versions prevent stale replacement.
- **Organization catalog:** Load organization metadata through bounded 500-row BFF pages until the final short page, preserving filter options and row names beyond page one.
- **Organization binding:** Creation sends `tenant_id`; editing sends `{ name }` only. Disabled organizations cannot be selected for new accounts.
- **Locked token owner:** `ServiceAccountTokenOwner` contains account and organization display data. `AccessTokenOrder` stores a frozen copy and accepts 30, 90, or non-expiring service-account lifetimes.
- **Deletion warning:** The operator must type the account name after seeing that all owned tokens will be permanently revoked.

## HOW TO CHANGE THIS FEATURE

1. Read the tactical design and routed graph files.
2. Keep API calls inside `web/src/app/actions/` and `RestHarnessApiClient`; never expose `API_ADMIN_TOKEN` to client components.
3. Preserve rows on refresh failure and show a safe retry error.
4. Keep creation organization blank until explicit active-organization selection.
5. Run Web unit and E2E checks when dependencies and API services are available.

## PARAMETERS / CONFIGURATIONS

| Name | Type | Required | Description | Default |
|------|------|----------|-------------|---------|
| `limit` | number | No | Page size sent to the service-account list endpoint. | `20` |
| `offset` | number | No | Nonnegative page offset. | `0` |
| `tenantId` | string | No | Organization filter; omitted means global list. | omitted |
| organization catalog page | number | No | Bounded organization page size used by the server action. | `500` |

## BEST PRACTICES

REQUIRED: Keep administrative authorization server-side through `API_ADMIN_TOKEN`.
REQUIRED: Treat service-account organization as immutable after creation.
REQUIRED: Apply service-account list filters and pagination before repository materialization.
REQUIRED: Require explicit organization selection during service-account creation.
REQUIRED: Reveal token plaintext only through the existing one-time secret modal.
PROHIBITED: Let project-access selection replace the row-selected token owner.
PROHIBITED: Include `tenant_id` in service-account update payloads.

## REFERENCES

- [**ARCHITECTURE.md**](../../adr/ARCHITECTURE.md): Web BFF and layer boundaries.
- [**TESTS.md**](../../adr/TESTS.md): Web unit and Playwright verification.
- [**service-accounts.md**](../api/service-accounts.md): API account lifecycle and organization contract.
- [**tokens.md**](../api/tokens.md): One-owner token issuance and lifetime rules.
- [**admin-token-management.md**](./admin-token-management.md): Web session and credential isolation.
