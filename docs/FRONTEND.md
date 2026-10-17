# Veritas frontend

Abdul Wasay built the frontend foundation on `wasay/frontend-foundation`. Its `frontend/**` files were imported selectively into `arman/backend-foundation`; his branch remains intact. Arman now owns local integration and the application flow. `frontend/context.md` preserves the original checkpoint notes.

## Run locally

Use Node.js 22.12+ and the pinned pnpm package manager. From the repository root:

```powershell
cd frontend
corepack pnpm install --frozen-lockfile
corepack pnpm dev:demo
```

Open http://127.0.0.1:5173. `dev:demo` explicitly sets `VITE_API_MODE=demo`: all jobs, reviews, documents, and Guardian decisions are browser-local simulations, visibly labeled as such. Reset demo clears those browser-local cases. The ordinary `corepack pnpm dev` command defaults to live mode. It proxies `/api` to FastAPI on port 8000 and does **not** substitute demo results when that backend fails.

In a second terminal, start the backend using [its setup guide](../backend/README.md). PostgreSQL must be configured and the reviewed migration applied manually before the live submission flow can complete; otherwise the API returns 503 and the UI displays the failure. Credentials belong only in ignored backend environment files.

Run checks:

```powershell
corepack pnpm typecheck
corepack pnpm test
corepack pnpm build
```

## Contract and behavior

The live adapter in `frontend/src/api/client.ts` validates canonical FastAPI responses from `contracts/openapi.json` and maps them into the existing UI view model. It submits Claim Court as `mode=claim_court` and Guardian as `mode=guardian`, with strict policy. It reads job claim summaries, fetches full details, and uses the backend's `overall_action` for release. A `pass` or `annotate` action is only shown after every referenced claim detail has loaded. Failed, interrupted, malformed, timed-out, or unavailable requests remain withheld.

In Live API mode the Claim Court also offers three clearly fictional subscription cases. Choosing one only prefills an advertised promise and two versioned policy documents; the backend decides the result after submission. The case and claim screens display original supplied text, a separate deterministic comparison result, exact supporting/exception passages, document IDs, questions, review history, and the latest Guardian action. **Clear form** does not delete backend jobs. This flow requires the manually configured PostgreSQL schema; the browser demo adapter does not impersonate it.

The review form sends `reviewer_id=local-reviewer`. Its Supported, Disputed, Still uncertain, and Request more evidence choices map to `approve`, `dispute`, `insufficient`, and `request_more_evidence`. A disputed choice with correction maps to `correct` and sends `corrected_text`; the original wording stays intact. After a review, the UI refetches the job before Guardian can change state.

Claim details show provisional and effective findings, evidence provenance, exact excerpts, support/challenge summaries, limitations, and the persisted review history. Backend synthetic evidence remains marked as synthetic even in live API mode. Search snippets remain marked unverified.

## Verification status

Frontend typecheck, all 23 frontend tests, and the production build pass locally. The tests include canonical contract examples, fictional case prefill, simulated UI flow, live failure handling, and Guardian hold behavior. The Vite server returned HTTP 200; FastAPI `/health` reported `setup_required` with `database_ready: false`, and a fictional policy submission in Live API mode returned HTTP 503 without mock fallback. Desktop and narrow browser views of the form, simulated evidence/review/Guardian flow, and the live error were inspected. The actual Supabase-backed submission → review → Guardian browser flow, persistence across process restart, hosted AI/search calls, and deployment remain unverified. Apply the reviewed SQL manually after configuring a separate Veritas PostgreSQL project.
