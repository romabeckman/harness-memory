`venv/bin/python`:

- pip should only be executed via ./venv
- python should only be executed via ./venv


Create if not exist:

```bash
# 1. Create the virtualenv (first time only)
python3 -m venv venv

# 2. Install backend dependencies
./venv/bin/pip install -r requirements.txt
```

---

Rules: 

- CRITICAL: Always respond, write code, and create documentation in English.
- CRITICAL: Do not narrate progress or emit interim status updates. Use tools and internal reasoning normally. After completing all required work, return only the final output explicitly required by the current prompt. If a final result is not required, return the summary exactly, limited to 1000 characters.
- Read `docs\BUSINESS.md` document.
- If is a development task read `docs/.digest.md` and `docs/.graph.json`
- Be rigorous in your development, adhering to SOLID principles and Clean Code principles.
- The structure of the test folders should follow this order: unit, integration, e2e. Each folder should contain test files corresponding to the test types.
- The folders within each type (unit, integration, e2e) should be organized according to the structure of the source code, reflecting the modules or components being tested.
- Rule: One file per class; never add more than one class per file.
- Ignore the `docs/workflow` folder during development. `docs/workflow` contains public-facing documents and should not be consulted for context.

## Post-development validation

- After Python, migration, or CI changes, run all applicable gates below in order from the repository root. Use `venv` tools. Check RTK availability with `rtk --version`; if it succeeds, use RTK to run the listed commands. Otherwise, run them directly. Listed validation commands have no RTK prefix by default.
- On POSIX, use `./venv/bin/python` and `./venv/bin/harness-memory`. On Windows, use `.\venv\Scripts\python.exe` and `.\venv\Scripts\harness-memory.exe`.
- When creating `venv` or changing dependencies, install test dependencies: `./venv/bin/python -m pip install --upgrade pip`, then `./venv/bin/python -m pip install -e '.[test]'`.
- Lint: `./venv/bin/python -m ruff check api core harness_memory_mcp --ignore E501,I001`.
- Format: `./venv/bin/python -m ruff format --check core/domain/platform/schema_compatibility_status.py core/domain/platform/schema_incompatible_error.py core/infrastructure/telemetry/telemetry_span_sanitizer.py harness_memory_mcp/config.py harness_memory_mcp/server/app.py harness_memory_mcp/server/factory.py harness_memory_mcp/server/server_lifespan_manager.py`.
- Against a clean, disposable PostgreSQL database, run `./venv/bin/python -m alembic upgrade head`, then `./venv/bin/harness-memory migrate --status`.
- Unit tests: `./venv/bin/python -m pytest tests/unit`.
- Integration tests: set `DATABASE_URL` and `TEST_DATABASE_URL` to a disposable PostgreSQL database, then run `./venv/bin/python -m pytest tests/integration`.
- E2E tests: `./venv/bin/python -m pytest tests/e2e`.
- Coverage, with disposable PostgreSQL: `./venv/bin/python -m pytest tests/unit tests/integration tests/e2e --cov=api --cov=core --cov=harness_memory_mcp --cov-report=term-missing --cov-fail-under=80`.
- If `sdk/` changes, run in this order: `npm install`, `npm run lint`, `npm run build`, `npm run typecheck`, `npm run test`.
- Run `git diff --check` at the end. Never use production or valuable development data for migration, integration, or coverage checks. Report skipped or unrun gates; do not mark them as passing.
- If you update the `endpoints`, update the Swagger in `api/`; check `api/server/app.py`.

---

Inicialize with skill `caveman` in mode `ultra`
