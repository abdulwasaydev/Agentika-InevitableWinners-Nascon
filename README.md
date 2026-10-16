# Veritas

Veritas checks AI-generated factual claims against inspectable evidence, records human decisions, and gives applications a release action: `pass`, `annotate`, or `hold_for_review`.

The two product interfaces share one verification engine:
- **Claim Court:** submit text and inspect claim-level findings and evidence.
- **AI Output Guardian:** intercept an AI response and hold uncertain output until backend policy permits release.

## Agreed architecture and stack

| Layer | Decision |
| --- | --- |
| Frontend | React, TypeScript, Vite, Tailwind CSS, React Router |
| Backend | Python 3.12, FastAPI, Pydantic |
| Persistence | Separate Supabase PostgreSQL project; SQLAlchemy and Alembic |
| Job processing | Database-backed jobs with one bounded in-process worker initially |
| AI and retrieval | Backend-only provider adapters; explicitly labeled deterministic demo mode |
| Deployment target | Clouds by Alternate Futures, after local integration and receipt of event credits |

Locally, the frontend proxies `/api` to `http://localhost:8000`. Planned production packaging is one Docker image: FastAPI serves the compiled frontend and API from one origin and connects to Supabase. Deployment, connectivity, and cost must be verified before claiming success.

## Ownership and integration

| Owner | Writable scope |
| --- | --- |
| Arman / integration branch | Backend, frontend, contracts, shared fixtures, and documentation on `arman/backend-foundation` |
| Abdul Wasay | Original frontend work preserved on `wasay/frontend-foundation` |

The frontend calls FastAPI for application data and review decisions; it does not access the database or AI/search providers directly. All database and provider credentials stay on the backend.

Wasay's frontend files were copied selectively into Arman's branch without modifying his branch or history. Keep new integration work on `arman/backend-foundation`. Do not force-push, discard another person's work, or merge into `main` automatically. Follow [AGENTS.md](AGENTS.md).

## Local-first build plan

1. Publish the backend schemas, generated OpenAPI contract, and example responses.
2. Build backend and frontend in parallel against that contract.
3. Integrate submission, job polling, claim findings, and evidence display.
4. Add durable human review and a Guardian client that genuinely obeys the release action.
5. Enable configured live providers and test failure behavior.
6. Add minimal explicit lineage if time permits, then package and deploy on Clouds by Alternate Futures.

Use [the product specification](docs/VERITAS_CODEX_CONTEXT.md) for detailed requirements. The agreed decisions in this README take precedence over older stack suggestions in that document. Prioritize the working core flow over MCP, elaborate graphs, PDF ingestion, or other stretch features.

## Frontend modes

The interface has an explicit synthetic mode for local demonstrations and a live mode that calls FastAPI. Live mode is the default.

- Put mock behavior behind the same typed adapter interface as real API requests.
- Enable mock mode explicitly and display **Demo mode — simulated verification**.
- Include functional submission, progress, evidence, review, and Guardian flows, plus failure and interrupted-job states.
- Use labeled synthetic documents and document IDs; never invent real-world citations or imply fixtures are live verification.
- Keep mock data consistent across screens and provide a demo reset.
- Never silently replace a failed live request with mock success.
- Align temporary fixtures and types with the canonical contract before integration.
- After switching adapters, verify the complete flow against the real backend.

Frontend implementation and setup belong in `frontend/**` and `docs/FRONTEND.md`.

## API contract and release behavior

The canonical interface is the generated [OpenAPI contract](contracts/openapi.json), with details in the [contract guide](contracts/README.md). Reconcile API changes there rather than implementing different assumptions on each device.

- `POST /api/v1/verify` accepts a job and returns HTTP 202 with its ID.
- The frontend polls `GET /api/v1/jobs/{job_id}` and stops at a terminal job status.
- Claim details and the review queue come from their documented API endpoints.
- Human reviews persist rationale, reviewer identity, timestamp, and history.
- After submitting a review, refetch the job and obey the backend's recalculated action.

Keep job status, claim finding, and release action separate. Preserve provisional machine findings alongside effective human-reviewed findings. Model agreement is not proof, and unverified does not mean false.

Strict mode holds unresolved material claims. A successful review request alone does not release output; disputed or insufficient findings may still require correction or a hold. Provider failure, missing evidence, invalid citations, and interrupted jobs must never become a false pass. Show original wording and corrections separately unless the backend explicitly supplies revised output.

## Database and secrets

Use a separate Veritas Supabase project; do not access or modify SocietyOS. Produce reviewable SQL/migrations for Arman to apply manually. Do not automatically mutate the remote database. Keep real environment files and credentials out of Git; provide example environment files with placeholders.

See [backend setup](backend/README.md) for current commands and configuration. Missing database or provider configuration must be reported honestly; mock behavior is not proof of working persistence or live inference.

## Current recorded status

Backend code includes a generated contract, PostgreSQL models and reviewable migration SQL, one bounded worker, deterministic synthetic verification, review/audit history, strict and balanced release policy, minimal explicit lineage, and optional Brave Search / OpenAI-compatible provider adapters. Wasay's frontend is integrated on this branch with responsive styling, passing tests and production build, and a client adapted to the canonical FastAPI responses. PostgreSQL persistence and live provider calls still need an isolated configured environment for execution tests; production packaging and deployment are not verified. Search snippets are labeled unverified and cannot alone produce a `pass`.

## Event requirements

The opening slides specify **October 17, 2026, 12:45 PM PKT** as the submission deadline and require a working deployment on **Clouds by Alternate Futures**. Build locally first; deploy after receiving the event credits. Follow Discord for schedule changes and submission instructions.

Participants must write their required LinkedIn and Twitter posts themselves; only grammar assistance is allowed. Coding agents must not draft those posts.
