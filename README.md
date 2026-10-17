# Veritas

Veritas checks AI-generated factual claims against inspectable evidence, records human decisions, and gives applications a release action: `pass`, `annotate`, or `hold_for_review`.

The two product interfaces share one verification engine:
- **Policy Check:** submit text and inspect claim-level findings and evidence.
- **AI Output Guardian:** intercept an AI response and hold uncertain output until backend policy permits release.


## Primary MVP: promises versus fine print

**Pitch: Veritas checks whether a company's promises survive its own fine print — before you subscribe.**

The audience is someone considering a subscription who does not have time to compare marketing claims with cancellation and refund policies. The main demo compares a specific advertised promise against supplied policy documents and exposes matching clauses, material exceptions, conflicts, and missing evidence. This is the selected product focus for demo preparation; the general verification engine and Guardian remain underneath it.

A summary describes each document. This workflow compares documents: what was promised, which clauses support it, which conditions narrow it, and what the user should clarify before paying.

### Bounded workflow

1. Supply one advertised promise and the relevant policy text. Pasted documents are sufficient for the MVP; document upload is optional if already supported.
2. Extract the promise and its material conditions, preserving exact wording.
3. The promise examiner identifies supporting passages; the fine-print examiner searches for exclusions, exceptions, scope differences, and conflicting passages.
4. Validate evidence references and exact excerpts, then present both positions side by side.
5. Display a document-comparison result: **consistent**, **qualified**, **conflicting**, or **insufficient evidence**.
6. A human inspects the evidence and records a decision with rationale. Preserve the original machine finding and review history.

These comparison labels are now explicit `comparison_result` fields, separate from claim statuses and Guardian release actions. The deterministic adapter maps **consistent** to `supported`, **qualified** to `pending_review`, **conflicting** to `disputed`, and **insufficient evidence** to `insufficient_evidence`. Qualified wording is never presented as unconditionally supported.

Neither examiner must invent an argument for its assigned side. No relevant passage is a valid finding. Use bounded supplied evidence; do not imply an exhaustive internet search.

### Morning demo preparation: three cases

Prepare three clearly labeled fictional subscription cases, each with an advertisement and versioned policy documents containing exact, inspectable clauses.

| Case | Example promise and policy | Expected demonstration |
| --- | --- | --- |
| Promise holds up | Advertisement: "Cancel anytime; access continues until the end of your paid month." Policy explicitly permits cancellation at any time, stops the next renewal, and preserves access through the paid period. | **Consistent within the supplied documents.** Show matching excerpts and a reasoned human review. Do not infer a refund promise. |
| Significant exception | Advertisement: "Full refund within 30 days." Policy allows a refund only when the service has never been used. | **Qualified or conflicting**, depending on the precise wording. Surface the unused-service restriction prominently and explain why the unconditional promise is not established. Human review must not erase the exception. |
| Cannot be resolved | Advertisement: "Cancel anytime and receive a refund." Supplied policy explains how to cancel but says nothing about refund eligibility. | **Insufficient evidence.** Distinguish cancellation from refund entitlement, show the missing information, and suggest asking for the refund policy. Absence of evidence is not proof of deception. |

Run these cases through actual backend services, persisted evidence and review records, and the integrated frontend. Seed inputs and source documents, not hard-coded verdict buttons. If assessments are deterministic fixtures, label them as simulated; distinguish those from actual model calls. Do not present fictional documents as real company policies or invent source URLs.

For each case, show:
- Original promise and the documents examined, including document IDs/version context.
- Exact supporting and qualifying/conflicting passages.
- Machine finding, concise explanation, and unresolved questions.
- Human decision and persisted rationale.
- Guardian behavior where applicable: unresolved material claims stay held; review submission alone is not release approval.

### Scope and preparation instructions

This checks consistency with the supplied written policies. It does **not** establish whether a company follows its policies in practice, whether a clause is legally enforceable, or whether documents omitted from the review change the result. Avoid legal verdicts and claims of guaranteed truth.

On resuming work in the morning, fetch and safely incorporate this README update without discarding local changes. Inspect the current implementation first, reuse the existing engine/UI, implement the smallest missing comparison-input and evidence-display pieces, and rehearse the three cases. Prioritize a coherent end-to-end demo and the required live deployment over new generic features. Report any missing configuration and which behavior is real versus simulated.

This section records the next demo milestone; it does not assert that the three cases or comparison workflow have already been implemented.


## Morning execution prompts: run sequentially and verify each milestone

**Instruction to Codex:** When asked to implement this README, execute the numbered prompts below in order in the same session. These are successive implementation tasks, not prompts for the user to paste separately. Inspect and reuse working code; skip rebuilding a capability only after verifying it meets the acceptance criteria. Do not stop after planning or after the first milestone.

Stay on the current `arman/backend-foundation` branch. Preserve uncommitted work and Wasay's original branch. The user has authorized implementation across frontend and backend. Do not deploy, spend credits, apply remote migrations, or merge to main automatically.

After **every prompt**:
1. Run the smallest meaningful functional check for that milestone, not merely a compilation check.
2. Fix failures introduced by the change and rerun the affected checks before moving on.
3. Record the result in `docs/DEMO_READINESS.md`: milestone, actual command/check, pass/fail/blocked, real versus simulated behavior, and remaining dependency. Never record an unrun check as passed.
4. Commit coherent working progress without secrets. Push safe checkpoints to the current branch.
5. Continue to the next prompt automatically. If an external dependency blocks a check, record it, give precise user setup instructions, and continue independent work. Do not claim the blocked functionality works.

Maintain a short task plan and avoid unrelated refactors, new frameworks, duplicate services, speculative features, or repetitive broad test runs. Backend domain tests should target behavior; visual changes need browser inspection rather than tests that merely mirror styling.

### Prompt 1 — Establish the actual baseline

Read this README, AGENTS.md, the existing specification, backend/frontend setup docs, and canonical contract. Inspect Git status and available code before edits. Safely incorporate remote README changes if needed without discarding local changes or switching branches. Report what actually runs, what is simulated, which database is configured, and whether any live model/retrieval integration is usable. Never print secret values.

Run existing relevant checks once to establish the baseline. Start the local services where possible. Create the readiness log and a concise implementation plan for the remaining prompts.

**Gate:** verified baseline commands and blockers are recorded; actual implementation is distinguished from README claims.

### Prompt 2 — Add promise-and-policy input through the real API

Implement the smallest extension needed to submit an advertised promise together with supplied policy documents. Preserve document IDs, title, version/date context where supplied, original text, and clause excerpts. Pasted text is sufficient; do not spend time on PDF parsing or crawling. Keep source documents separate from the claim text so policy clauses are not mistaken for claims made by the advertisement.

Reuse the existing job/persistence pipeline. Apply input/document size limits. If schemas change, update Pydantic models, generated OpenAPI, examples, typed frontend client, and migration artifacts together. Produce remote SQL for manual application only.

**Gate:** submit a promise plus two documents through the API; retrieve the job and prove that the correct documents and claim are linked. Check invalid/oversized input. If persistence cannot be exercised, mark that specific check blocked rather than substituting an undisclosed in-memory success.

### Prompt 3 — Implement evidence-backed comparison

Build or adapt the promise examiner and fine-print examiner to reason over the submitted evidence. They may report no evidence; neither must manufacture an argument. Validate cited IDs and excerpt grounding. Detect material conditions such as cancellation versus refund eligibility, time windows, usage exclusions, and billing-period scope.

Return/display consistent, qualified, conflicting, or insufficient evidence with concise justifications. Define explicit domain fields or documented mappings; do not overload Guardian actions or incorrectly equate qualified with unconditional support. Existing hosted-model adapters may be reused. Deterministic demo adapters must remain visibly labeled, without claiming live inference.

Do not implement decisions keyed to a case title, fixture ID, or expected answer. Source excerpts and conditions must drive the result.

**Gate:** check matching wording, a usage exception, missing refund evidence, and an invalid citation. Change a policy clause and confirm the comparison can change accordingly. Unsupported evidence must not yield a false pass.

### Prompt 4 — Prepare all three reproducible demo cases

Create the three fictional cases defined above as versioned input/source fixtures:
1. Promise holds up.
2. Significant exception.
3. Cannot be resolved.

A case picker should prefill inputs, not inject a final verdict. Run each through the real local API and service pipeline. Make resetting demo-owned records safe, bounded, and explicit; never delete unrelated records. Include expected findings in test expectations, not in runtime answer shortcuts.

**Gate:** all three cases produce the intended distinctions with traceable excerpts. Confirm the exception appears prominently and missing evidence is not described as proof of fraud. Record whether assessments are live or simulated.

### Prompt 5 — Complete real human review and Guardian behavior

Wire review controls to persisted backend decisions with reviewer identity, rationale, timestamps, and history. Preserve the initial machine findings. Recalculate the job after review and let the frontend refetch the backend action.

Keep unresolved material output held in strict mode. A review click alone must not release content; a disputed original claim stays qualified/held according to documented policy. Show original and corrected wording separately. Reviewer overrides must remain visible and must not erase missing evidence. If review endpoints are publicly exposed later, use the existing access controls or require a minimal backend-verified reviewer credential; do not embed a privileged shared secret in frontend assets.

**Gate:** exercise hold → review → recalculation through the real client/API. Reload to confirm review persistence and, when configured, restart the backend to check durability. Test a dispute and an insufficient-evidence decision, not just the favorable path.

### Prompt 6 — Make the interface worthy of a judged demo

Improve the existing interface into a deliberate, polished product centered on **"Does the promise survive the fine print?"** Preserve useful imported work and functionality; do not replace the app with an unrelated landing-page mockup.

Design direction:
- Use an editorial evidence-desk aesthetic: warm off-white surfaces, deep ink text, restrained teal accents, amber for exceptions, and red only for actual conflicts/errors. Avoid generic purple/blue gradients, glowing blobs, and excessive glass effects.
- Pair a distinctive readable serif heading face (for example Newsreader or an available equivalent) with a clean sans-serif UI/body face (for example Inter or an available equivalent). Use reliable bundled/self-hosted assets where practical and graceful fallbacks; do not let remote fonts block the demo.
- Establish a clear type scale, strong headings, comfortable paragraph measure, intentional whitespace, and subtle borders. Avoid making every element an identical rounded card.
- Give the promise visual priority, then show the exact fine-print exception as a highlighted quotation with document/version context. Make the conclusion understandable before the user reads detailed reasoning.
- Use a clear evidence comparison layout and a compact step progression: Promise → Evidence → Review → Outcome. This is product navigation, not decorative status pretending processing occurred.
- Put the three example cases within easy reach. Make loading, reset, retry, and navigation obvious; keep advanced developer details secondary.
- Use meaningful icons sparingly. Add restrained transitions with reduced-motion support; no fake delay, typewriter effects, or animation that slows the presentation.
- Distinguish machine finding, human decision, source provenance, and Guardian action using words as well as color.
- Write concise product copy. Do not expose stack details or raw enum names where plain language is clearer.
- Support keyboard navigation, visible focus, contrast, readable evidence, and narrow screens.

**Gate:** inspect actual rendered screens in a browser at desktop presentation size and a narrow/mobile size. Check submission, processing, evidence detail, review, and final/held views for clipping, overflow, awkward wrapping, unreadable contrast, broken fonts, and dead controls. Capture local QA screenshots if useful, inspect them, and fix issues. If browser inspection is unavailable, record that limitation; a build alone is not visual verification.

### Prompt 7 — Integrate, rehearse, and prepare the handoff

Run the complete local flow for all three cases using the integrated frontend and backend. Confirm API/client agreement, polling cleanup, refresh behavior, errors, and no silent mock fallback. Run final backend checks, frontend type checks, and production build once after the final changes; fix material failures.

Prepare a concise six-minute walkthrough in `docs/DEMO_SCRIPT.md`, with the three cases, exact clicks, evidence to point out, human review, the product's limits, and a clearly labeled fallback if providers fail. This is a technical demo script, not the prohibited AI-written LinkedIn/Twitter posts.

Update README status and `docs/DEMO_READINESS.md` with verified outcomes. Document exact local start commands, required user configuration, and remaining deployment steps. Prepare Docker packaging if time permits, but do not deploy or spend credits in this sequence.

**Gate:** one full rehearsal succeeds, or specific blocked steps are clearly reported. Final report includes commits, checks, runnable commands, real/simulated capabilities, and unresolved dependencies. Do not call the product deployed or fully verified unless demonstrated.

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

The integrated MVP supports a deterministic comparator for supplied promises and policy excerpts, plus two Gemini-assisted privacy-policy scans. One uses an ignored local snapshot downloaded from GitHub Docs; the other accepts the full GitHub policy pasted by the user and persists that text with the job. The pasted source is clearly labeled unauthenticated. Both Gemini paths rank passages from the full document and show separate support and challenge notes; cited quotes must exactly match the selected source text. Human review is required before a supported claim can pass Guardian, while challenged or insufficient claims stay held under strict policy. The UI uses Policy Check, Reviews, Release Gate, and Source Trail language with a blue and cyan palette. The fictional subscription picker was removed from Live API; the explicitly labeled Synthetic demo mode remains.

**Verified locally:** the GitHub statement was downloaded from the official Docs API and hash-checked. With a Gemini key stored only in ignored `backend/.env`, three full-policy paste claims ran through the frontend proxy and Supabase. The absolute no-training claim was challenged and held after human dispute; the account-email claim was supported and passed Guardian after human approval; the service-provider claim was supported and remains pending review. Stored quotes matched the pasted text, both agent notes were present, and jobs/reviews/release decisions survived a FastAPI restart. The downloaded-source path was also exercised with two real claims. A provider or source failure stays explicit and cannot become synthetic success. The MVP remains local-only and unauthenticated.

**Local start:** on a fresh setup, copy `backend/.env.example` to ignored `backend/.env`; do not overwrite an existing `.env`. Enter the separate Veritas PostgreSQL URL and Gemini settings described in [backend setup](backend/README.md). Apply reviewed [SQL](backend/initial_schema.sql) manually in Supabase only if the project is fresh. For the downloaded-source option, run `.\.venv\Scripts\python backend\scripts\download_github_policy.py` from the repository root; a full policy paste works without that local snapshot. Run `cd backend; ..\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000` and `cd frontend; corepack pnpm dev` in separate PowerShell terminals. Open `http://127.0.0.1:5173/` in **Live API** mode. `/health` must show `database_ready: true`. No extra database migration is needed for this path. Keep credentials in ignored local files; never paste them into chat.

## Event requirements

The opening slides specify **October 17, 2026, 12:45 PM PKT** as the submission deadline and require a working deployment on **Clouds by Alternate Futures**. Build locally first; deploy after receiving the event credits. Follow Discord for schedule changes and submission instructions.

Participants must write their required LinkedIn and Twitter posts themselves; only grammar assistance is allowed. Coding agents must not draft those posts.
