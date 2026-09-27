---
doc_type: feature
domain: admin-token-management
stack: [TypeScript, Next.js 15, React 19, Tailwind CSS v4, Lucide React, Vitest, Playwright]
node_id: "feature:web-admin-token-management"
tags: [web, admin, tokens, session, bff]
edges:
  - relation: implements
    target: "adr:architecture"
  - relation: depends_on
    target: "feature:api-tokens"
  - relation: depends_on
    target: "feature:api-service-accounts"
  - relation: references
    target: "adr:security"
  - relation: tested_by
    target: "adr:tests"
updated: 2026-09-27
---
```graph
{"node_id":"feature:web-admin-token-management","domain":"admin-token-management","implements":["adr:architecture"],"tested_by":["adr:tests"],"entrypoints":["web/src/middleware.ts","web/src/app/page.tsx","web/src/app/login/page.tsx"],"registration_files":["web/src/infrastructure/api/client-factory.ts","web/src/application/dashboard-load-state.ts"],"reference_files":["web/src/application/use-cases/issue-token.use-case.ts"],"code_files":["web/src/app/actions/auth.ts","web/src/app/actions/projects.ts","web/src/app/actions/tokens.ts","web/src/application/ports/harness-api-client.port.ts","web/src/application/use-cases/bootstrap-tenant.use-case.ts","web/src/application/use-cases/revoke-token.use-case.ts","web/src/components/create-token-dialog.tsx","web/src/components/secret-reveal-modal.tsx","web/src/components/token-list.tsx","web/src/domain/access-token-order.ts","web/src/domain/admin-session.ts","web/src/domain/credential-review-item.ts","web/src/domain/secret-reveal-view.ts","web/src/domain/token-scope.ts","web/src/infrastructure/api/rest-harness-api-client.ts","web/src/infrastructure/auth/auth-service.ts","web/src/infrastructure/auth/session-manager.ts"],"test_files":["web/tests/unit/application/bootstrap-tenant.use-case.test.ts","web/tests/unit/application/issue-token.use-case.test.ts","web/tests/unit/application/revoke-token.use-case.test.ts","web/tests/unit/application/tokens.action.test.ts","web/tests/unit/components/token-list.test.tsx","web/tests/unit/domain/access-token-order.test.ts","web/tests/unit/domain/admin-session.test.ts","web/tests/unit/domain/credential-review-item.test.ts","web/tests/unit/domain/secret-reveal-view.test.ts","web/tests/unit/domain/token-scope.test.ts","web/tests/unit/infrastructure/rest-harness-api-client.test.ts","web/tests/unit/infrastructure/session-manager.test.ts","web/tests/e2e/admin-console.spec.ts","web/tests/e2e/demo-walkthrough.spec.ts","web/tests/unit/application/dashboard-load-state.test.ts"],"knowledge":{"schema_version":1,"entities":[{"id":"capability:credential-review","type":"capability","label":"Credential review","definition":"Show existing credentials with resolved owner context and revocation controls.","aliases":[]},{"id":"rule:single-credential-owner","type":"rule","label":"Single credential owner","definition":"Every reviewed credential resolves to exactly one known user or service account.","aliases":[]},{"id":"contract:credential-catalog-loading","type":"contract","label":"Credential catalog loading","definition":"Load bounded token and identity pages, then return complete review-ready rows or a safe error.","aliases":[]},{"id":"decision:server-held-admin-authority","type":"decision","label":"Server-held admin authority","definition":"Keep API_ADMIN_TOKEN in the server BFF for management requests.","aliases":[]},{"id":"rule:discard-stale-review","type":"rule","label":"Discard stale review","definition":"Clear credential rows when a dashboard load or refresh fails.","aliases":[]}],"claims":[{"id":"claim:credential-owner-context","subject":"capability:credential-review","relation":"constrained_by","object":"rule:single-credential-owner","statement":"The review projection rejects missing, ambiguous, or unknown owners and shows User or Service Account explicitly.","kind":"requirement","status":"supported","evidence":[{"kind":"specification","source":"docs/specs/credential_review_revocation/003-harness-memory-tactical-design.md","locator":"Q02, Q05, CredentialReviewItem","snapshot":null}],"derived_from":[],"gap":null},{"id":"claim:bounded-review-catalogs","subject":"capability:credential-review","relation":"exposes","object":"contract:credential-catalog-loading","statement":"The server action loads a bounded token page and traverses bounded user, service-account, and tenant pages before resolving review rows locally.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"web/src/app/actions/tokens.ts","locator":"loadDashboardDataAction: token page and identity catalog traversal","snapshot":null}],"derived_from":[],"gap":null},{"id":"claim:management-authority-boundary","subject":"capability:credential-review","relation":"governed_by","object":"decision:server-held-admin-authority","statement":"Credential list and revoke calls use the server-held administrative client; browser data contains review metadata only.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"web/src/infrastructure/api/rest-harness-api-client.ts","locator":"RestHarnessApiClient.request","snapshot":null},{"kind":"specification","source":"docs/specs/credential_review_revocation/003-harness-memory-tactical-design.md","locator":"Q01, Q08","snapshot":null}],"derived_from":[],"gap":null},{"id":"claim:discard-stale-review","subject":"capability:credential-review","relation":"constrained_by","object":"rule:discard-stale-review","statement":"A failed dashboard load clears previously shown credentials and reports a safe error; a failed refresh after successful revocation does not display stale rows.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"web/src/app/page.tsx","locator":"fetchData: nextDashboardLoadState and catch branch","snapshot":null},{"kind":"code","source":"web/src/application/dashboard-load-state.ts","locator":"nextDashboardLoadState failure handling","snapshot":null}],"derived_from":[],"gap":null}]},"updated":"2026-09-27"}
```

# Web Admin Token Management

Secure Next.js BFF for admin sessions, owner-linked token issuance on identity pages, and aggregate credential review and revocation.

## OVERVIEW

The browser receives signed session state and review metadata only. Server Actions call the REST API through `RestHarnessApiClient` with server-held `API_ADMIN_TOKEN` authority.

## FOLDER STRUCTURE

```text
web/
├── src/domain/                 # Review projection and token rules
├── src/application/            # Ports and Bootstrap, Issue, Revoke flows
├── src/infrastructure/         # REST client and session services
├── src/app/                    # Routes and server actions
├── src/components/             # Review table and identity-page dialogs
└── tests/                      # Vitest unit and Playwright E2E suites
```

## CORE CONCEPTS

- **Admin Session**: HTTP-only signed cookie validated by middleware.
- **Credential review boundary**: Opening the dashboard reads existing credentials and identity catalogs without creating identities.
- **Credential Review Item**: Immutable token metadata plus one resolved owner name and explicit `User` or `Service Account` type. Service-account organization is optional.
- **Owner-linked Issuance**: User and service-account pages validate one locked owner and reveal plaintext once.
- **Server Authority**: REST list and delete calls never expose `API_ADMIN_TOKEN` to browser code.

## TOKEN MANAGEMENT WORKFLOW

1. **Authenticate**: `/login` creates the admin session; middleware protects `/`.
2. **Load review**: Dashboard loads one bounded credential page and traverses user, service-account, and tenant catalogs. `resolveCredentialReviewItems` resolves owners locally by immutable IDs.
3. **Reject ambiguity**: Missing, dual, unknown, or malformed owners return a safe load error. Missing organization names do not invalidate service-account rows.
4. **Review**: `TokenList` shows owner context, scopes, projects, status, and no aggregate-page issuance control.
5. **Revoke**: Confirmation selects one token ID. Pending delete disables that row. Delete failure retains the row and displays a retryable safe error. Success revalidates `/`; if refresh then fails, the dashboard clears stale rows and reports that current state is unavailable.

## IMPLEMENTATION RULES

REQUIRED: Keep API calls behind `HarnessApiClientPort` and server Actions.
REQUIRED: Page credentials and traverse identity catalogs using bounded `limit` and `offset` values; avoid per-credential owner requests.
REQUIRED: Keep credential review read-only until the operator confirms revocation.
REQUIRED: Clear old review rows after a failed refresh; never present stale credentials as current.
REQUIRED: Resolve exactly one known owner for every displayed credential.
REQUIRED: Freeze review projections and copy dependency DTO metadata without exposing token plaintext or digests.
REQUIRED: Revalidate the dashboard only after successful revocation.
REQUIRED: Keep issuance and one-time secret reveal on owner pages.
PROHIBITED: Leak `API_ADMIN_TOKEN`, authorization headers, cookies, plaintext tokens, or raw request errors to browser data or UI.
PROHIBITED: Render partial credential rows when catalog loading or owner resolution fails.

## REFERENCES

- [**ARCHITECTURE.md**](../../adr/ARCHITECTURE.md): Layer boundaries and BFF integration rules.
- [**SECURITY.md**](../../adr/SECURITY.md): Authentication, token storage, and credential isolation.
- [**TESTS.md**](../../adr/TESTS.md): Vitest and Playwright execution standards.
- [**tokens.md**](../api/tokens.md): API token lifecycle, storage, scopes, and revocation.
- [**service-accounts.md**](../api/service-accounts.md): Service-account ownership and lifecycle.
