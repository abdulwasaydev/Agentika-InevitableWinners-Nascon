# Demo readiness

Updated 2026-10-17. Work remains on `arman/backend-foundation`; the README was fast-forwarded from origin without local changes to preserve.

## Plan

1. Establish the checked baseline and document missing configuration.
2. Add persisted promise and versioned policy document input to the existing API.
3. Compare exact supplied passages, validate citations, and assign a separate comparison result.
4. Add three fictional input fixtures and exercise them without verdict shortcuts.
5. Recheck review history and Guardian hold/release after decisions.
6. Improve the existing interface and inspect it at desktop and narrow widths.
7. Rehearse the integrated flow, publish run instructions, and hand off blockers.

## Milestones

| Milestone | Check actually run | Result | Real versus simulated; remaining dependency |
| --- | --- | --- | --- |
| 1 — baseline | `git status --short --branch`, `git fetch origin --prune`, `git merge --ff-only origin/arman/backend-foundation`; `python -m pytest -q -p no:cacheprovider backend/tests` via `.venv`; frontend `tsc --noEmit`, `vitest run`, `vite build` through installed binaries | PASS: clean fast-forward; 18 passed, 1 skipped; 22 passed; typecheck and build passed | Existing browser demo is simulated. No `backend/.env`, hence no PostgreSQL URL, Supabase schema, or configured Brave/LLM calls. The database-backed request, review, and restart checks are blocked until a separate database is configured and reviewed SQL is manually applied. |

The backend accepts no in-memory fallback. An unavailable real API must remain an error in live frontend mode. Do not describe generated or fictional passages as live retrieval.
