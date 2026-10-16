# Veritas frontend

## Scope and design

Frontend owner: Abdul Wasay. Work is based on shared main `9cf4137` on `wasay/frontend-foundation`. Only `frontend/**` and this document belong to this change.

Veritas is an evidence-review workspace, with an ink-green navigation rail, warm paper surfaces, editorial headings, legible source excerpts, and restrained semantic colors. Claim Court submits text and follows a job; a case shows provisional findings and evidence; the review queue records human decisions; Guardian withholds final output until a freshly fetched job permits release. Lineage records the job-to-claim-to-evidence relationship after these core flows work.

React + TypeScript + Vite + Tailwind + React Router. A single typed client isolates HTTP calls and an explicitly selected synthetic service. Default mode is live. No database, model, search provider, or credential belongs in browser code.

The root VERITAS_CODEX_CONTEXT.md became available during implementation and has been read. The user's updated pasted brief and follow-up demo requirements override its older stack and deployment suggestions. Backend contracts and fixtures are pending; frontend-local temporary types and synthetic data must be reconciled before integration.

## Implementation plan and progress

1. [ ] Foundation: configure frontend-local tooling; test submission and error behavior; build shell and Claim Court. Client interface: `submit(text, signal)`, `getJob(id, signal)`, `getClaim(id, signal)`, `listReviews(signal)`, `review(id, input, signal)`.
2. [ ] Verification and review: test polling cancellation, terminal statuses, review refetch, and failure handling; build job, claim, evidence, queue, and review screens.
3. [ ] Guardian and lineage: test hold-before-approval, successful-review-still-held, annotations, corrections, unavailable/malformed responses, and mode isolation; build controlled release and explicit draft inspection.
4. [ ] Validate: typecheck, tests, build, browser checks if available; check the latest remote contract; document exact integration status; commit logical changes, push, and open a PR without merging.

Review focus: stale responses after navigation/mode change; unknown backend statuses; review success followed by failed refetch; malicious text/source URLs; synthetic data presented as live.

## Integration status

Pending canonical `contracts/openapi.json` and fixtures from `arman/backend-foundation`. Do not treat temporary frontend payloads as the backend contract. No live verification has been validated yet.

## Paused implementation checkpoint

The user asked to stop coding and push the current state. See `frontend/context.md` for the complete handoff. Screen source, mock/live adapters, and tests exist, but styling has not been implemented. Type checking passes; 19 of 21 tests pass (two screen-query failures); the production build fails because `src/styles.css` is missing. This is an unfinished checkpoint.

Run `pnpm install` inside `frontend`, then `pnpm dev:demo` to explicitly select `.env.demo` (`VITE_API_MODE=demo`). `pnpm dev` defaults to the live API. No secrets are required for the synthetic demo. Demo records persist in browser local storage and can be removed with Reset demo.
