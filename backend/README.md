# Backend local setup

Python 3.12 and PostgreSQL are required. The API has **no in-memory database fallback**. From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend\requirements.txt
if (-not (Test-Path backend\.env)) { Copy-Item backend\.env.example backend\.env }
```

Enter a connection string for a separate PostgreSQL database in the untracked `backend/.env`. The conditional copy preserves an existing local `.env` and its credentials. Keep the Supabase credentials private. `DEMO_MODE=true` selects the deterministic synthetic corpus; it still requires PostgreSQL for jobs and reviews.

Review the [initial migration](alembic/versions/0001_initial.py), [supplied-document migration](alembic/versions/0002_supplied_documents.py), [comparison migration](alembic/versions/0003_comparison.py), and [generated SQL for a fresh database](initial_schema.sql). Generate SQL again with:

```powershell
.\.venv\Scripts\python backend\scripts\export_sql.py
```

Apply the reviewed SQL **manually** to a fresh, separate database. If revision `0001_initial` is already applied, apply [0001 to 0002](upgrade_0001_to_0002.sql) followed by [0002 to 0003](upgrade_0002_to_0003.sql); if already at `0002_supplied_documents`, apply only the latter. It enables row-level security on the Veritas tables and revokes access from Supabase's `anon` and `authenticated` roles when they exist; only the backend connects using the database password. The API checks the schema and Alembic revision; it returns 503 until the database is ready. No command here applies a remote migration or creates cloud resources.

Promise-and-policy submissions send the advertised wording as `text` and separate bounded `documents`; the deterministic comparison cites exact supplied passages. It returns `consistent`, `qualified`, `conflicting`, or `insufficient_evidence` separately from claim status and Guardian action. This adapter uses narrow wording rules and can miss paraphrases; it makes no hosted model or live search call for supplied documents.

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

For optional general web-search calls, set `DEMO_MODE=false`, `BRAVE_SEARCH_API_KEY`, `LLM_PROVIDER=gemini`, `LLM_API_KEY`, and `LLM_MODEL` in `backend/.env`. This sends submitted text to those external services. The search adapter uses [Brave Web Search](https://api-dashboard.search.brave.com/app/documentation/web-search/get-started). The Gemini adapter uses Google's [native generateContent API](https://ai.google.dev/api/generate-content) with JSON output. `LLM_PROVIDER=openai_compatible` remains available if `LLM_API_URL` points to a Chat Completions JSON endpoint. It makes at most one search query and two role calls per claim, with bounded timeouts. Search descriptions are **unverified snippets**, not fetched page text; they cannot alone yield `pass`.

## Official GitHub privacy policy scan

The API also supports a downloaded scan of [GitHub's General Privacy Statement](https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement). The generic live form now uses the pasted-document path. To use the API's downloaded-source path, download its current Markdown from the [official GitHub Docs Article API](https://docs.github.com/en/get-started/using-github-docs/github-docs-api):

```powershell
.\.venv\Scripts\python backend\scripts\download_github_policy.py
```

This writes a SHA-256-checked snapshot and retrieval metadata under ignored `backend/data/`; refresh it when the published statement changes. The backend ranks passages across the whole snapshot and sends at most eight relevant passages plus the claim to separate support and challenge LLM roles. Each role's notes appear beside exact quotes and the official source link. Only cited excerpts and analysis records are persisted in PostgreSQL for this downloaded-source path, not the entire snapshot. Retrieval can miss relevant passages, so a supported finding requires human review before Guardian permits release. A contradiction or insufficient finding remains held under strict policy.

To paste the entire policy yourself, select **Live API** → **Policy Check**, type a claim, and paste 10,000 to 100,000 characters into **Full privacy policy**. The UI has no GitHub preset or suggested claims. It keeps the draft in browser session storage so you can try multiple claims without pasting it again. This path sends `policy_text` alongside one claim, persists that full text in Supabase, and labels its evidence as **user-pasted, source unverified** with no authenticated URL. An empty field submits a general text check; the downloaded official snapshot path remains available through the API contract. No new SQL migration is needed. Selected passages, rather than the entire paste, are sent to Gemini; do not paste private material.

For this scan, set these fields **only** in ignored `backend/.env` and restart the API:

```dotenv
LLM_PROVIDER=gemini
LLM_API_KEY=YOUR_KEY_ENTERED_LOCALLY
LLM_MODEL=gemini-3.5-flash-lite
```

Create a Gemini API key in [Google AI Studio](https://aistudio.google.com/app/apikey) and use a model available to your project; Google's [pricing page](https://ai.google.dev/gemini-api/docs/pricing) lists a free tier for `gemini-3.5-flash-lite`, subject to your project's [rate limits](https://ai.google.dev/gemini-api/docs/rate-limits). `LLM_API_URL` is unused with `LLM_PROVIDER=gemini`. `BRAVE_SEARCH_API_KEY` is not needed for this document path, and `DEMO_MODE=true` may remain enabled for the separate fictional corpus. The policy scan always calls the configured LLM; it never falls back to synthetic success. Each scan makes two bounded model calls, so four claims require about eight model calls. Missing keys, source snapshots, provider errors, and quotes that do not match the downloaded text fail closed. Do not enter secrets in the frontend or chat. No new database migration is required.

Run local checks:

```powershell
.\.venv\Scripts\python backend\scripts\export_openapi.py
.\.venv\Scripts\python -m pytest -q -p no:cacheprovider backend\tests
```

The PostgreSQL integration test runs only when `TEST_DATABASE_URL` points to a dedicated local `veritas_test` database on localhost. It is skipped otherwise. Supabase persistence across a backend restart was verified for downloaded-source and full-paste Gemini scans. Three pasted-policy claims completed; one human-disputed claim stayed held, one human-approved supported claim passed Guardian, and one remains pending review. The Gemini key stays in ignored `backend/.env`. The API is a local MVP without authentication; keep it on localhost until access control and deployment safeguards are added.
