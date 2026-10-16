# Veritas

Veritas checks AI generated factual claims against inspectable evidence, records human decisions, and gives applications a release action. This repository is the NASCON hackathon MVP.

## Agreed stack and ownership

- Arman: `backend/**`, `contracts/**`, shared fixtures and documentation, database migrations, and later deployment packaging. Python 3.12, FastAPI, Pydantic, SQLAlchemy, Alembic, and a separate Supabase PostgreSQL project.
- Abdul Wasay: `frontend/**` and `docs/FRONTEND.md`. React, TypeScript, Vite, Tailwind, and React Router.
- Frontend development proxies `/api` to `http://localhost:8000`. Production packaging will eventually serve both from one origin.

## MVP scope

The backend accepts verification jobs, extracts bounded claims, retrieves labeled evidence, runs support and challenge assessments, validates citations, assigns machine findings, and applies a deterministic release policy. Human reviews preserve the provisional finding and recalculate the release action. A seeded synthetic demo works without provider credentials; live providers are configured separately.

**Implemented:** shared API schemas and generated [OpenAPI contract](contracts/openapi.json). **In progress:** persistent local backend and tests. **Planned:** frontend integration, live providers, production packaging, and cloud deployment. No cloud resources are provisioned by this repository.

Read the [product specification](docs/VERITAS_CODEX_CONTEXT.md) and [contract guide](contracts/README.md). Backend setup commands are in [backend/README.md](backend/README.md).
