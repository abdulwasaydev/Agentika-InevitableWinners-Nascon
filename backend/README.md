# Backend local setup

Python 3.12 and PostgreSQL are required. The API has **no in-memory database fallback**. From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env
```

Enter a connection string for a separate PostgreSQL database in the untracked `backend/.env`. Keep the Supabase credentials private. `DEMO_MODE=true` selects the deterministic synthetic corpus; it still requires PostgreSQL for jobs and reviews.

Review [the initial migration](alembic/versions/0001_initial.py) and [its generated SQL](initial_schema.sql). Generate it again with:

```powershell
.\.venv\Scripts\python backend\scripts\export_sql.py
```

Apply the reviewed SQL **manually** to a fresh, separate database. It enables row-level security on the Veritas tables and revokes access from Supabase's `anon` and `authenticated` roles when they exist; only the backend connects using the database password. The API checks the schema and Alembic revision; it returns 503 until the database is ready. No command here applies a remote migration or creates cloud resources.

Start the local API:

```powershell
cd backend
..\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open `http://localhost:8000/docs` for the live API reference. From another PowerShell at the repository root, submit and poll a synthetic example:

The API accepts browser requests from `http://localhost:5173` and `http://127.0.0.1:5173` by default. Set `FRONTEND_ORIGINS` in `backend/.env` to a comma-separated list if the frontend uses another local origin. Only `GET` and `POST` API methods are allowed cross-origin.

```powershell
$body = Get-Content contracts\examples\verify-request.json -Raw
$accepted = Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/v1/verify -ContentType application/json -Body $body
Invoke-RestMethod -Uri "http://localhost:8000$($accepted.poll_url)"
```

Poll until `completed`, `failed`, or `interrupted`. Use the claim and review endpoints in [the contract guide](../contracts/README.md). A restart marks previously running jobs `interrupted`; queued jobs remain queued for the single worker. Strict mode holds unresolved material claims even after a review that records a dispute or insufficient evidence.
Reviewing an ancestor claim also returns every downstream claim to `pending_review` and recalculates each affected Guardian job; descendants never become supported automatically.

For optional live calls, set `DEMO_MODE=false`, `BRAVE_SEARCH_API_KEY`, `LLM_API_URL`, `LLM_API_KEY`, and `LLM_MODEL` in `backend/.env`. This sends submitted text to those external services. The search adapter uses [Brave Web Search](https://api-dashboard.search.brave.com/app/documentation/web-search/get-started), and the LLM adapter expects an [OpenAI-compatible Chat Completions JSON response](https://platform.openai.com/docs/api-reference/chat). It makes at most one search query and two role calls per claim, with bounded timeouts. Search descriptions are **unverified snippets**, not fetched page text; they cannot alone yield `pass`.

Run local checks:

```powershell
.\.venv\Scripts\python backend\scripts\export_openapi.py
.\.venv\Scripts\python -m pytest -q -p no:cacheprovider backend\tests
```

The PostgreSQL integration test runs only when `TEST_DATABASE_URL` points to a dedicated local `veritas_test` database on localhost. It is skipped otherwise. Persistence against Supabase and actual live-provider calls have not been verified here. The API is a local MVP without authentication; keep it on localhost until access control and deployment safeguards are added.
