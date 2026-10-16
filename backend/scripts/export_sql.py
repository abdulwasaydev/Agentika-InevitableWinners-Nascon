"""Render reviewable PostgreSQL migration SQL without connecting to a database."""

import subprocess
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parents[1]
result = subprocess.run(
    [sys.executable, "-m", "alembic", "-c", str(backend_dir / "alembic.ini"), "upgrade", "head", "--sql"],
    cwd=backend_dir.parent,
    capture_output=True,
    text=True,
    check=True,
)
sql = "\n".join(line.rstrip() for line in result.stdout.splitlines()).rstrip() + "\n"
output = backend_dir / "initial_schema.sql"
output.write_text(sql, encoding="utf-8")
print(output)
