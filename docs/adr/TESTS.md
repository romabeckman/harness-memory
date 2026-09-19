---
doc_type: adr
domain: testing
stack: [Python 3.12+, pytest 9.x, pytest-asyncio, pytest-cov, coverage.py, FastMCP 4.x, PostgreSQL]
node_id: "adr:tests"
tags: [testing, unit-tests, e2e-tests, coverage]
edges: []
updated: 2026-09-19
---
# Testing Protocol

## OVERVIEW

Use **pytest 9.x** for unit, integration, end-to-end, and MCP contract tests. The configured **80% coverage gate** applies globally to `core` and `mcp`; no per-layer threshold is configured.

## COMMANDS

| Type | Command | Description |
|------|---------|-------------|
| Unit | `pytest tests/unit` | Test domain entities, application handlers, contracts, and adapters. |
| Integration | `pytest tests/integration` | Test repository behavior and migrations; repository integration fixtures currently use SQLite. |
| E2E / MCP | `pytest tests/e2e` | Test public MCP registration, schemas, and adapter-to-application behavior. |
| Coverage | `pytest --cov=core --cov=mcp` | Run configured branch coverage with the global 80% threshold. |

Verified migration commands from project scope: `harness-memory migrate` and `harness-memory migrate --status`.

## MINIMUM COVERAGE

REQUIRED: Maintain the configured global coverage threshold. Per-layer thresholds remain unconfigured.

| Layer | Coverage | Description |
|-------|----------|-------------|
| Domain / Core | Report only | `core` contributes to the global threshold; no independent gate exists. |
| Application / Use Cases | Report only | `core` contributes to the global threshold; no independent gate exists. |
| Infrastructure / Adapters | Report only | `core` and `mcp` contribute to the global threshold; no independent gate exists. |
| Global | 80% | Enforced by `coverage.fail_under` across configured source packages. |

No CI gate exists in the repository yet. REQUIRED: Add a CI gate before treating 80% as release-enforced.

## PATTERNS & BEST PRACTICES

REQUIRED: Use Arrange, Act, Assert with one behavior per test.
REQUIRED: Test domain entities/value objects without infrastructure and application handlers through fake/mock ports.
REQUIRED: Test snapshot immutability, versioning, idempotent publication, invalid input rejection, and active replacement.
REQUIRED: Use real PostgreSQL behavior for models, repositories, transactions, migrations, and tenant isolation.
REQUIRED: Use the FastMCP in-process client for MCP catalog and schema tests.
REQUIRED: Assert provenance and evidence in relationship and impact results.
PROHIBITED: Mock domain logic or hide transaction behavior behind broad mocks.
PROHIBITED: Depend on test execution order or shared tenant data.

## TOOLING

- **Framework:** Python 3.12+, pytest 9.x, pytest-asyncio, and FastMCP 4.x.
- **Assertions:** pytest built-in assertions.
- **Mocks/Stubs:** No mocking library configured; keep substitutes at external boundaries.
- **Coverage:** coverage.py with pytest-cov; branch measurement and missing-line text report.
- **CI Integration:** No CI configuration exists in the repository.

## TROUBLESHOOTING

- **Flaky tests:** Isolate the failing tier, record database state and tenant identity, then rerun the focused test.
- **Debug mode:** Run `pytest -vv -s` to show verbose test output and captured standard output.

## REFERENCES

- [**README.md**](../README.md): Documentation navigation index.
- [**ARCHITECTURE.md**](./ARCHITECTURE.md): System boundaries and dependency rules.
