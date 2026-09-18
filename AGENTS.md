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
- If is a development task read `docs/.digest.md` and `docs/.graph.json`
- Be rigorous in your development, adhering to SOLID principles and Clean Code principles.
- The structure of the test folders should follow this order: unit, integration, e2e. Each folder should contain test files corresponding to the test types.
- The folders within each type (unit, integration, e2e) should be organized according to the structure of the source code, reflecting the modules or components being tested.
- Rule: One file per class; never add more than one class per file.


---

Inicialize with skill `caveman` in mode `ultra`