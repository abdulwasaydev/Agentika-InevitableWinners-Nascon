import type { Action, Claim, ComparisonResult, Decision, Evidence, Finding, Job, JobStatus, Review, SuppliedDocument, VeritasApi } from './types';

/** The sole boundary between the canonical FastAPI contract and the UI view model. */
export class ApiError extends Error {
  constructor(message: string, public readonly status?: number) { super(message); this.name = 'ApiError'; }
}
const contractError = () => new ApiError('API contract mismatch. This response cannot authorize release.');
function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw contractError();
  return value as Record<string, unknown>;
}
function string(value: unknown): string { if (typeof value !== 'string') throw contractError(); return value; }
function strings(value: unknown): string[] { if (!Array.isArray(value)) throw contractError(); return value.map(string); }
function array(value: unknown): unknown[] { if (!Array.isArray(value)) throw contractError(); return value; }
function choice<T extends string>(value: unknown, choices: readonly T[]): T {
  if (typeof value !== 'string' || !choices.includes(value as T)) throw contractError();
  return value as T;
}
function optionalString(value: unknown): string | undefined { return value == null ? undefined : string(value); }
function finding(value: unknown): Finding {
  const canonical = choice(value, ['supported', 'disputed', 'insufficient_evidence', 'pending_review', 'not_checkable'] as const);
  return canonical === 'disputed' ? 'challenged' : canonical;
}
function parseReview(value: unknown): Review {
  const r = record(value);
  const decision = choice(r.decision, ['approve', 'dispute', 'insufficient', 'request_more_evidence', 'correct'] as const);
  const uiDecision: Decision = decision === 'approve' ? 'supported' : decision === 'dispute' || decision === 'correct' ? 'challenged' : decision === 'insufficient' ? 'uncertain' : 'more_evidence';
  string(r.reviewer_id);
  return {
    review_id: string(r.id), claim_id: string(r.claim_id), decision: uiDecision,
    rationale: string(r.rationale), correction: optionalString(r.corrected_text), created_at: string(r.created_at),
  };
}
function parseEvidence(value: unknown): Evidence {
  const e = record(value);
  const stance = choice(e.stance, ['support', 'challenge', 'context'] as const);
  return {
    evidence_id: string(e.id), document_id: optionalString(e.document_id), title: string(e.title),
    url: optionalString(e.url) ?? '', excerpt: string(e.excerpt),
    stance: stance === 'support' ? 'supporting' : stance === 'challenge' ? 'challenging' : 'context',
    source_type: string(e.source_type), provenance: string(e.provenance),
    retrieved_at: string(e.retrieved_at), validity_status: string(e.validity_status),
  };
}
function parseClaim(value: unknown, detail = false): Claim {
  const c = record(value);
  const provisional = finding(c.provisional_status);
  const effective = finding(c.effective_status);
  const needsReview = c.needs_review;
  if (typeof needsReview !== 'boolean') throw contractError();
  string(c.checkability);
  const reasons = strings(c.reason_codes);
  const comparison = c.comparison_result == null ? null : choice<ComparisonResult>(c.comparison_result, ['consistent', 'qualified', 'conflicting', 'insufficient_evidence']);
  strings(c.support_evidence_ids); strings(c.challenge_evidence_ids);
  const assessments = detail ? array(c.assessments).map(value => {
    const a = record(value);
    return { role: string(a.role), position: string(a.position), reasoning_summary: string(a.reasoning_summary), evidence_ids: strings(a.evidence_ids), limitations: optionalString(a.limitations) };
  }) : [];
  const evidence = detail ? array(c.evidence).map(parseEvidence) : [];
  const history = detail ? array(c.reviews).map(parseReview) : [];
  const parentIds = detail ? strings(c.parent_claim_ids) : [];
  const explanation = detail
    ? assessments.map(a => `${a.role}: ${a.reasoning_summary}`).join(' ') || 'No role assessment is available.'
    : 'Open the claim to inspect the evidence and role assessments.';
  return {
    claim_id: string(c.id), job_id: string(c.job_id), text: string(c.text), finding: provisional,
    effective_status: effective, needs_review: needsReview, explanation, evidence,
    limitations: assessments.flatMap(a => a.limitations ? [a.limitations] : []),
    reason_codes: reasons, human_review: history.at(-1) ?? null, review_history: history,
    comparison_result: comparison, comparison_explanation: optionalString(c.comparison_explanation),
    unresolved_questions: strings(c.unresolved_questions ?? []),
    assessments, parent_claim_ids: parentIds,
  };
}
function parseJob(value: unknown): Job {
  const j = record(value);
  const status = choice(j.status, ['queued', 'running', 'completed', 'failed', 'interrupted'] as const);
  const action = j.overall_action == null ? null : choice<Action>(j.overall_action, ['pass', 'annotate', 'hold_for_review']);
  if (status === 'completed' && action === null) throw contractError();
  const claims = array(j.claims).map(item => parseClaim(item));
  const id = string(j.id);
  if (claims.some(claim => claim.job_id !== id)) throw contractError();
  string(j.mode); string(j.policy); string(j.origin); string(j.updated_at);
  const errorCode = optionalString(j.error_code);
  const documents: SuppliedDocument[] = array(j.documents).map(item => {
    const d = record(item);
    return { document_id: string(d.document_id), title: string(d.title), version: optionalString(d.version), effective_date: optionalString(d.effective_date), text: string(d.text) };
  });
  return {
    job_id: id, origin: string(j.origin), status: (status === 'running' ? 'processing' : status) as JobStatus,
    submitted_text: string(j.input_text), documents, overall_action: action,
    claim_ids: claims.map(claim => claim.claim_id), created_at: string(j.created_at),
    limitations: [], reason_codes: [],
    error: errorCode ? `Verification stopped: ${errorCode}. No output is approved.` : null,
  };
}

export function createLiveApi(fetcher: typeof fetch = fetch): VeritasApi {
  async function request(path: string, signal?: AbortSignal, body?: unknown, acceptedStatus?: number): Promise<unknown> {
    let response: Response;
    try {
      const timeout = AbortSignal.timeout(15000);
      response = await fetcher(`/api/v1${path}`, {
        method: body === undefined ? 'GET' : 'POST',
        headers: { Accept: 'application/json', ...(body === undefined ? {} : { 'Content-Type': 'application/json' }) },
        credentials: 'same-origin', signal: signal ? AbortSignal.any([signal, timeout]) : timeout,
        ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      });
    } catch (error) {
      if (signal?.aborted) throw error;
      throw new ApiError('Live API unavailable. Check that FastAPI is running on localhost:8000. No synthetic results were substituted.');
    }
    if (!response.ok) {
      let message = `Live API request failed (HTTP ${response.status}). No result is approved.`;
      try {
        const payload = record(await response.json());
        if (typeof payload.message === 'string') message += ` ${payload.message}`;
      } catch { /* HTTP status remains authoritative. */ }
      throw new ApiError(message, response.status);
    }
    if (acceptedStatus && response.status !== acceptedStatus) throw new ApiError(`API contract mismatch: expected HTTP ${acceptedStatus}.`, response.status);
    try { return await response.json(); } catch { throw contractError(); }
  }
  return {
    async submit(input, signal) {
      if (!input.text.trim() || input.text.length > 8000) throw new ApiError('Enter claim text between 1 and 8,000 characters.');
      if (input.policy_text && (input.policy_text.length < 10000 || input.policy_text.length > 100000)) throw new ApiError('Paste the full policy document (10,000 to 100,000 characters).');
      const mode = input.mode ?? 'claim_court';
      const result = record(await request('/verify', signal, {
        text: input.text, mode, policy: 'strict', origin: mode === 'guardian' ? 'agent_output' : 'user_input',
        documents: input.documents ?? [],
        ...(input.policy_source ? { policy_source: input.policy_source } : {}),
        ...(input.policy_text ? { policy_text: input.policy_text } : {}),
      }, 202));
      const id = string(result.job_id);
      if (!id.trim() || choice(result.status, ['queued']) !== 'queued' || string(result.poll_url) !== `/api/v1/jobs/${id}`) throw contractError();
      return { job_id: id };
    },
    async getJob(id, signal) { const job = parseJob(await request(`/jobs/${encodeURIComponent(id)}`, signal)); if (job.job_id !== id) throw contractError(); return job; },
    async getClaim(id, signal) { const claim = parseClaim(await request(`/claims/${encodeURIComponent(id)}`, signal), true); if (claim.claim_id !== id) throw contractError(); return claim; },
    async listReviews(signal) {
      const result = record(await request('/reviews?status=pending', signal));
      return array(result.items).map(item => parseClaim(item));
    },
    async review(id, input, signal) {
      if (input.rationale.trim().length < 3) throw new ApiError('A review rationale of at least three characters is required.');
      const decision = input.correction?.trim() ? 'correct' : ({ supported: 'approve', challenged: 'dispute', uncertain: 'insufficient', more_evidence: 'request_more_evidence' } as const)[input.decision];
      const result = record(await request(`/claims/${encodeURIComponent(id)}/reviews`, signal, {
        decision, reviewer_id: 'local-reviewer', rationale: input.rationale,
        ...(decision === 'correct' ? { corrected_text: input.correction?.trim() } : {}),
      }));
      choice(result.overall_action, ['pass', 'annotate', 'hold_for_review']);
      const claim = parseClaim(result.claim, true);
      const review = parseReview(result.review);
      if (claim.claim_id !== id || review.claim_id !== id) throw contractError();
      return review;
    },
  };
}
