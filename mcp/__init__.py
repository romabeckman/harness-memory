"""Harness Memory MCP adapter package.

The namespace path remains extensible so FastMCP can resolve its installed
``mcp`` distribution beside this local adapter package.
"""

import sys
from pathlib import Path
from pkgutil import extend_path

__path__ = extend_path(__path__, __name__)

for _entry in sys.path:
    _candidate = Path(_entry) / "mcp" / "__init__.py"
    if _candidate.is_file() and _candidate.resolve() != Path(__file__).resolve():
        exec(compile(_candidate.read_text(encoding="utf-8"), str(_candidate), "exec"), globals())
        break
