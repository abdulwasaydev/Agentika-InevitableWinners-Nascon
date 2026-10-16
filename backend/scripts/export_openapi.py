"""Export contracts/openapi.json from the FastAPI route definitions."""

import json
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parents[1]
repo_dir = backend_dir.parent
sys.path.insert(0, str(backend_dir))

from app.main import app  # noqa: E402

output = repo_dir / "contracts" / "openapi.json"
output.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(output)
