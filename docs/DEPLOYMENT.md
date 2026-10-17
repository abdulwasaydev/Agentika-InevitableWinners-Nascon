# Veritas deployment

## Package

The root `Dockerfile` builds the existing React frontend with Node 24 and pnpm
11.25.0, then runs Python 3.12 and `python -m app.production` as a non-root user.
The server binds `0.0.0.0:8000` (`PORT` can override this). Use one replica and
one worker: the existing FastAPI lifespan owns the database-backed job worker.
Frontend assets and `/api` share one origin; no Vite development server is used.
No database migration runs during build or startup.

At the owner's explicit request, the production frontend, case APIs, reviews,
and API documentation are public. No username or password is required, and old
`DEPLOY_USERNAME` / `DEPLOY_PASSWORD` variables are ignored. Anyone with the URL
can view submitted policy text, submit verification jobs, and record reviews.
Use public or synthetic documents for this shared hackathon demo.

Cross-origin browser writes are rejected. Responses use `Cache-Control: no-store`,
`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, and a no-referrer policy.
Missing API endpoints/assets retain 404s; frontend navigation routes get the SPA.
The ordinary local `app.main:app` entry point remains unchanged and unauthenticated.

## Runtime configuration

Set these as runtime variables, never frontend variables or Docker build args:

- `DATABASE_URL`: separate Veritas PostgreSQL URL using `postgresql+psycopg://`
  with `sslmode=require`; reviewed schema must already be at `0003_comparison`.
- `LLM_PROVIDER=gemini`, `LLM_API_KEY`, `LLM_MODEL`: the user's configured Gemini model.
- `PORT=8000`, `DEMO_MODE=true`: allows the explicitly labeled synthetic mode;
  Live API remains the frontend default. Failed live requests do not become demos.
- Optional bounded processing settings from `backend/.env.example`.

The image excludes all actual environment files, local credentials, node_modules,
the virtual environment, and `backend/data`. The full-policy paste flow needs no
downloaded snapshot. The separate downloaded-GitHub-source API path will explicitly
fail unless its hash-matched policy/metadata pair is provisioned separately.
There is no direct frontend Supabase access. Review and source text persist in
Supabase; no container volume is needed for the pasted-policy flow.

## Local rehearsal

Build with `pnpm --dir frontend build`, then set the runtime variables above and
run `python -m app.production` from `backend` using the project's Python 3.12 venv.
Alternatively: `docker build -t veritas:<commit> .` then
`docker run --rm --env-file <private-runtime-env> -p 8000:8000 veritas:<commit>`.
Keep the private env file ignored. Do not put secrets in shell arguments or logs.

Verify `/` and `/api/v1/reviews` return 200 without authorization headers and
without a `WWW-Authenticate` challenge; `/health` must return `database_ready: true`.
Test a deep link and an unknown `/api` path. Run the existing tests and the production-gateway tests.
The Docker health check requires actual database readiness, not just HTTP 200.

## Clouds by Alternate Futures

Use the GitHub source `abdulwasaydev/Agentika-InevitableWinners-Nascon`, branch
`arman/backend-foundation`, root directory `.`, root `Dockerfile`, and source
container port `8000`. Do not select the stale default `arman-work` branch.
Give the GitHub App access only to this repository. Disable automatic deployment
if further pushes would disrupt the judged demo; build a specific recorded commit.

Inspect the provider's actual settings before deployment. Its Settings page warns
that runtime variables go to the winning decentralized provider in plaintext;
the account owner must approve the chosen handling of dedicated demo secrets.
Use the smallest suitable CPU-only instance, verify the price, and set a lifetime
budget cap within the available event credits. Do not top up or subscribe silently.
No public deployment has been verified yet; record its actual URL and settings
only after the cloud build and hosted checks succeed.

After deployment: check TLS, public access, database readiness, Gemini connectivity, full
policy submission, evidence quotes, persisted human review, and Guardian's hold/
pass decision. Confirm a disputed or unresolved claim remains held after review.
Restart once and confirm records persist. Record actual verification and any
remaining limitations in `docs/DEMO_READINESS.md` before calling it deployed.
