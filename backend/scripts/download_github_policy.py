"""Download GitHub's published privacy statement for local policy scans."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.official_policy import POLICY_FILE, download_policy  # noqa: E402


if __name__ == "__main__":
    snapshot = download_policy()
    print(f"Saved {len(snapshot.text)} characters to {POLICY_FILE}")
    print(f"SHA-256: {snapshot.sha256}")
    print(f"Retrieved: {snapshot.retrieved_at.isoformat()}")
