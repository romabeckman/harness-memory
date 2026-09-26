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

- CRITICAL: Do not narrate progress or emit interim status updates. Use tools and internal reasoning normally. After completing all required work, return only the final output explicitly required by the current prompt. If a final result is not required, return the summary exactly, limited to 1000 characters.
- Read `docs\BUSINESS.md` document.
- If is a development task read `docs/.digest.md` and `docs/.graph.json`
- Be rigorous in your development, adhering to SOLID principles and Clean Code principles.
- The structure of the test folders should follow this order: unit, integration, e2e. Each folder should contain test files corresponding to the test types.
- The folders within each type (unit, integration, e2e) should be organized according to the structure of the source code, reflecting the modules or components being tested.
- Rule: One file per class; never add more than one class per file.
- Ignore the `docs/workflow` folder during development. `docs/workflow` contains public-facing documents and should not be consulted for context.
- Before validating code changes, read `.github/workflows/ci.yml`, identify affected CI jobs, and run every matching check locally. Treat the workflow as source of truth; keep these instructions aligned when CI changes. Do not report a gate as passing if it was skipped or not run.
- For backend Python or migration changes, run CI checks in this order from the repository root. Use only the virtual environment executables. On Windows, replace `./venv/bin/python` with `.\venv\Scripts\python.exe` and `./venv/bin/harness-memory` with `.\venv\Scripts\harness-memory.exe`.
  - When creating the environment or changing dependencies: `rtk run "./venv/bin/python -m pip install -e '.[test]'"`
  - Lint: `rtk run "./venv/bin/python -m ruff check api core harness_memory_mcp --ignore E501,I001"`
  - Format: `rtk run "./venv/bin/python -m ruff format --check core/domain/platform/schema_compatibility_status.py core/domain/platform/schema_incompatible_error.py core/infrastructure/telemetry/telemetry_span_sanitizer.py harness_memory_mcp/config.py harness_memory_mcp/server/app.py harness_memory_mcp/server/factory.py harness_memory_mcp/server/server_lifespan_manager.py"`
  - Against a fresh disposable PostgreSQL database: `rtk run "./venv/bin/python -m alembic upgrade head"`, then `rtk run "./venv/bin/harness-memory migrate --status"`.
  - Unit: `rtk run "./venv/bin/python -m pytest tests/unit"`.
  - Integration, with `DATABASE_URL` and `TEST_DATABASE_URL` set to a fresh disposable PostgreSQL database: `rtk run "./venv/bin/python -m pytest tests/integration"`.
  - E2E: `rtk run "./venv/bin/python -m pytest tests/e2e"`.
  - Coverage, with a fresh disposable PostgreSQL database: `rtk run "./venv/bin/python -m pytest tests/unit tests/integration tests/e2e --cov=api --cov=core --cov=harness_memory_mcp --cov-report=term-missing --cov-fail-under=80"`.
- Migration, integration, and coverage checks mutate their database. Never point them at production or valuable development data. If PostgreSQL is unavailable, report those checks as unverified.
- Run only if the code in `sdk/` is updated:
    - ALWAYS run `rtk npm install` to check dependencies
    - ALWAYS run `rtk npm run lint` to check code syntax
    - ALWAYS run `rtk npm run build` before `npm run typecheck`
    - ALWAYS run `rtk npm run typecheck` before `npm run test`

---

Inicialize with skill `caveman` in mode `ultra`
