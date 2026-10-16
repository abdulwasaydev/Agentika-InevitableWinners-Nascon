# Veritas frontend checkpoint

Date: 2026-10-16 (Pakistan time).
Repository: https://github.com/abdulwasaydev/Agentika-InevitableWinners-Nascon
Branch: `wasay/frontend-foundation`, created from shared main commit `9cf4137`.

## Current status

This is an **unfinished implementation checkpoint**, pushed at the user's request. The user explicitly stopped further coding. Do not describe this checkpoint as a completed, polished, or buildable MVP.

Only `frontend/**` and `docs/FRONTEND.md` were edited. Existing root files, backend work, contracts, and teammate branches were preserved. The user-provided root `VERITAS_CODEX_CONTEXT.md` was read when it became available and is not part of this frontend commit.

## Code in place

- Frontend-local React, TypeScript, Vite, Tailwind, React Router, Lucide, Vitest, and Testing Library configuration; dependencies and lockfile are in `frontend/`.
- Application shell, navigation, mode indicator, reset-demo confirmation, workspace guide, and routes for Claim Court, cases, claims, review queue, review form, Guardian, synthetic documents, and minimal evidence lineage.
- Claim submission with size limits, loading/error handling, case progress polling, extracted claim cards, provisional machine findings, reason codes, evidence excerpts, and source inspection.
- A single typed API interface and separate live HTTP and frontend-local synthetic adapters. Relative `/api/v1` requests; Vite proxies `/api` to `http://localhost:8000`.
- Explicit demo environment (`.env.demo`, `pnpm dev:demo`) and persistent “Demo mode — simulated verification” label. Ordinary `pnpm dev` defaults to live mode.
- Synthetic observatory documents with IDs `SYN-REG-001`, `SYN-TECH-002`, and `SYN-VIS-003`. No fabricated real-world citations. Document text is visibly marked fictional.
- Mock jobs, progress, review records, recalculated policy, browser-local demo persistence, and reset. Scenarios include mixed/pending review, supported, disputed, insufficient evidence, annotated, failed, interrupted, and provider unavailable.
- Review forms collect a decision, rationale, and optional correction. Corrections remain separate from original text. Machine findings are preserved alongside human decisions.
- Guardian withholds final content for unresolved, unavailable, interrupted, or failed checks. Draft inspection is explicitly labeled. A review POST is followed by a job GET; saving a review alone is not release permission.
- The synthetic policy keeps disputed and uncertain decisions held. After every claim is definitively supported, the synthetic service permits pass or annotated release, depending on the scenario. This is simulation, never real factual approval.
- Sequential polling stops on terminal states, aborts on navigation, rejects stale responses, and invalidates previous approval before refetching.
- Submitted text and evidence are React text nodes; source URLs are restricted to absolute HTTP(S).

## Validation and unfinished work

- TypeScript type checking passed on the current source.
- Earlier tests passed for 18 release-policy, HTTP-client, mock-adapter, and polling checks. Three screen integration tests were then added and observed failing before the screens were implemented, as part of test-first development.
- Final test rerun: **19 passed, 2 failed** across five test files. All 18 release-policy, HTTP-client, mock-adapter, and polling tests pass, as does the screen test for live failure without mock fallback. The two remaining screen tests fail on ambiguous/mismatched accessible queries: duplicate source-document headings and the supported radio option's combined label. They were not changed because the user stopped further coding.
- **Production build currently fails:** `frontend/src/main.tsx` imports `./styles.css`, but that stylesheet has not been created. Responsive visual styling was the next implementation step when the user stopped coding.
- No browser visual QA or complete interactive rehearsal has been performed.
- No deployment, backend service, direct Supabase access, external model/search calls, event social posts, or merge into main was performed.

## Backend contract and Git integration

Canonical backend OpenAPI and fixtures were not available when the provisional frontend interface was written. The live client currently validates a frontend-local temporary schema and is **not verified against the backend**.

The temporary model uses `job_id`, `claim_ids`, `submitted_text`, `finding`, `human_review`, and `overall_action`; review decisions are `supported`, `challenged`, and `uncertain`; the review queue is expected as `{items: Claim[]}`. These are assumptions, not ownership of the canonical contract. Reconcile request fields, statuses, review payloads, evidence metadata, and response envelopes with `contracts/openapi.json` on Arman's backend branch before integration. The original context document contains broader illustrative schemas; the user's updated frontend brief and canonical contract take precedence.

The most recent `git fetch origin` failed with a bad local `refs/codex/turn-diffs/checkpoints/...` object. This appeared in tool-managed Git metadata. No refs were deleted or rewritten to work around it. Check the current remote state before resuming integration.

## Local commands

With Node.js 22.12+ and pnpm 11.25.0 available:

```powershell
cd frontend
pnpm install
pnpm dev:demo
pnpm test
pnpm typecheck
pnpm build
```

`pnpm dev:demo` will currently encounter the missing stylesheet until implementation resumes. `pnpm dev` uses live mode and requires the backend. No live API failure silently switches to the mock adapter.

## Resume priorities, only when requested

1. Read this file, `docs/FRONTEND.md`, applicable `AGENTS.md`, and the latest canonical backend contract.
2. Preserve the existing branch and ownership boundaries; inspect local changes and fetch remote state safely.
3. Implement the missing stylesheet and finish responsive/accessibility work.
4. Run the complete test suite and production build; fix actual failures. Exercise every synthetic flow, including disputed/uncertain reviews staying held and fully resolved cases changing state.
5. Check browser rendering, keyboard interaction, mode switching, reset, persistence, and failed refetch behavior.
6. Align the adapter and fixtures with Arman's contract, document real integration gaps, and open a PR when ready. Do not merge automatically.
