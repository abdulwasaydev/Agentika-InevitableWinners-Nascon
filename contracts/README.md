# Veritas API contract

`openapi.json` is generated from `backend/app/main.py` and `backend/app/schemas.py` with `python backend/scripts/export_openapi.py`. The frontend should generate or validate its client types from that file and never infer status values from display text. Re-export and commit the contract whenever a route or schema changes.

## Polling and lifecycle

`POST /api/v1/verify` returns **202** with `job_id`, `status: queued`, and `poll_url`; it never claims to have checked the text synchronously. Poll `GET /api/v1/jobs/{job_id}` until `completed`, `failed`, or `interrupted`. `queued` and `running` are nonterminal. Poll no faster than once per second. A completed job has an `overall_action` and claim findings; a failed or interrupted job must not be presented as verified. An interrupted job can be submitted again as a new job.

For a promise-versus-policy case, send the advertised wording in `text` and up to three supplied `documents` with unique `document_id`, `title`, optional `version`/`effective_date`, and original `text`. The combined document text is capped at 24,000 characters. `GET /api/v1/jobs/{job_id}` returns these documents separately from the claim. See `examples/promise-request.json`. The claim has a separate `comparison_result` (`consistent`, `qualified`, `conflicting`, `insufficient_evidence`), explanation, and unresolved questions. This bounded deterministic document comparison uses exact supplied passages, never unrelated seeded or web evidence. It can miss paraphrases and does not establish real-world compliance or legal enforceability. The claim's provisional/effective status and Guardian action remain separate.

Job statuses: `queued`, `running`, `completed`, `failed`, `interrupted`. Claim findings: `supported`, `disputed`, `insufficient_evidence`, `pending_review`, `not_checkable`. Guardian release actions: `pass`, `annotate`, `hold_for_review`. These are separate concepts. Each claim has a `provisional_status` from the machine and an `effective_status` after any human decision. `needs_review` is an explicit queue flag.

## Review transitions

For a GitHub policy scan, set `policy_source` to `github_privacy` and omit `documents`; see `examples/github-policy-request.json`. Leave `policy_text` out to use the locally downloaded official GitHub Docs snapshot. To scan a full document pasted by the user, add `policy_text` as a separate string of 10,000 to 100,000 characters. The backend persists that exact text with the job and labels its evidence `user_supplied_privacy_policy` / `user_pasted_unverified`; pasted text has no authenticated source URL. Both paths rank passages across the full document and call separate support and challenge LLM roles. Every cited quote must exactly match a selected passage. The claim stays `pending_review` until a human decision. Missing keys, provider failures, and invalid quotes never permit Guardian release. This is model-assisted analysis of written text, not proof of company practice or authenticity of a paste.

`GET /api/v1/reviews?status=pending` lists claims requiring review. `POST /api/v1/claims/{claim_id}/reviews` requires `decision`, `reviewer_id`, and `rationale`. Decisions are `approve`, `dispute`, `insufficient`, `request_more_evidence`, and `correct`; `correct` also requires `corrected_text`. Reviews append to the audit history and preserve the provisional machine finding. A correction is a proposal beside the original text, not an edit to it. The backend recalculates the job action from **all** material claims. Completing a review does not necessarily release a strict-mode job: disputed, insufficient, or still-pending claims continue to hold it.

## Frontend behavior

Use the `poll_url` after submission. On completion, render evidence and assessments from `GET /api/v1/claims/{claim_id}`. Show synthetic demo evidence as synthetic. For Guardian mode, obey `overall_action`: show `pass`, show `annotate` with caveats, and withhold final publication for `hold_for_review`. A caller should poll again after a review because the action can change. Keep original and corrected text visibly distinct.

## Errors

Validation errors return HTTP 422. Unknown IDs return 404. Review attempts before job completion return 409. Missing database configuration, migration, or a full worker queue returns 503 with an error description. Provider failures are represented in job status/reason codes and must not become a `pass`. There is no implicit in-memory persistence fallback.

Example payloads in `examples/` are **synthetic contract illustrations**, not live verification results. The API requires the reviewed PostgreSQL schema before accepting jobs; see the root README for implementation and test status.
