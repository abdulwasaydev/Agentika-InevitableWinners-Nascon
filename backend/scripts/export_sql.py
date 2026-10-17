"""Render reviewable PostgreSQL migration SQL without connecting to a database."""

import subprocess
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parents[1]
for revision, filename in (
    ("head", "initial_schema.sql"),
    ("0001_initial:head", "upgrade_0001_to_0002.sql"),
):
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(backend_dir / "alembic.ini"), "upgrade", revision, "--sql"],
        cwd=backend_dir.parent,
        capture_output=True,
        text=True,
        check=True,
    )
    sql = "\n".join(line.rstrip() for line in result.stdout.splitlines()).rstrip() + "\n"
    output = backend_dir / filename
    output.write_text(sql, encoding="utf-8")
    print(output)
