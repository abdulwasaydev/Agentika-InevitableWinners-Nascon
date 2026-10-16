import type { Action, Claim, Decision, Evidence, Finding, Job, JobStatus, Review, VeritasApi } from './types';
export class ApiError extends Error {
  constructor(message: string, public readonly status?: number) { super(message); this.name = 'ApiError'; }
}
const contractError = () => new ApiError('API contract mismatch. This response cannot be trusted for release. Reconcile the frontend with the canonical contract.');
function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw contractError();
  return value as Record<string, unknown>;
}
function string(value: unknown): string { if (typeof value !== 'string') throw contractError(); return value; }
function strings(value: unknown): string[] { if (!Array.isArray(value)) throw contractError(); return value.map(string); }
function choice<T extends string>(value: unknown, choices: readonly T[]): T {
  if (typeof value !== 'string' || !choices.includes(value as T)) throw contractError();
  return value as T;
}
function parseReview(value: unknown): Review {
  const r = record(value);
  return { review_id: string(r.review_id), claim_id: string(r.claim_id), decision: choice<Decision>(r.decision, ['supported', 'challenged', 'uncertain']), rationale: string(r.rationale), correction: r.correction == null ? undefined : string(r.correction), created_at: string(r.created_at) };
}
function parseEvidence(value: unknown): Evidence {
  const e = record(value);
  return { evidence_id: string(e.evidence_id), document_id: e.document_id == null ? undefined : string(e.document_id), title: string(e.title), url: string(e.url), excerpt: string(e.excerpt), stance: choice(e.stance, ['supporting', 'challenging', 'context']) };
}
function parseClaim(value: unknown): Claim {
  const c = record(value);
  if (!Array.isArray(c.evidence)) throw contractError();
  return { claim_id: string(c.claim_id), job_id: string(c.job_id), text: string(c.text), finding: choice<Finding>(c.finding, ['supported', 'challenged', 'insufficient_evidence', 'not_checkable']), explanation: string(c.explanation), evidence: c.evidence.map(parseEvidence), limitations: strings(c.limitations), reason_codes: strings(c.reason_codes), human_review: c.human_review == null ? null : parseReview(c.human_review) };
}
function parseJob(value: unknown): Job {
  const j = record(value);
  return { job_id: string(j.job_id), status: choice<JobStatus>(j.status, ['queued', 'processing', 'completed', 'review_pending', 'failed', 'interrupted', 'provider_unavailable']), submitted_text: string(j.submitted_text), overall_action: j.overall_action === null ? null : choice<Action>(j.overall_action, ['pass', 'annotate', 'hold_for_review']), claim_ids: strings(j.claim_ids), created_at: string(j.created_at), limitations: strings(j.limitations), reason_codes: strings(j.reason_codes), revised_output: j.revised_output == null ? null : string(j.revised_output), error: j.error == null ? null : string(j.error) };
}

export function createLiveApi(fetcher: typeof fetch = fetch): VeritasApi {
  async function request(path: string, signal?: AbortSignal, body?: unknown, acceptedStatus?: number): Promise<unknown> {
    let response: Response;
    try {
      const timeout = AbortSignal.timeout(15000);
      response = await fetcher(`/api/v1${path}`, { method: body === undefined ? 'GET' : 'POST', headers: { Accept: 'application/json', ...(body === undefined ? {} : { 'Content-Type': 'application/json' }) }, credentials: 'same-origin', signal: signal ? AbortSignal.any([signal, timeout]) : timeout, ...(body === undefined ? {} : { body: JSON.stringify(body) }) });
    } catch (error) {
      if (signal?.aborted) throw error;
      throw new ApiError('Live API unavailable. Check that the FastAPI backend is running on localhost:8000. No synthetic results were substituted.');
    }
    if (!response.ok) throw new ApiError(`Live API request failed (HTTP ${response.status}). No result is approved.`, response.status);
    if (acceptedStatus && response.status !== acceptedStatus) throw new ApiError(`API contract mismatch: expected HTTP ${acceptedStatus}.`, response.status);
    try { return await response.json(); } catch { throw contractError(); }
  }
  return {
    async submit(input, signal) {
      if (!input.text.trim() || input.text.length > 20000) throw new ApiError('Enter claim text between 1 and 20,000 characters.');
      const result = record(await request('/verify', signal, { text: input.text }, 202));
      const id = string(result.job_id);
      if (!id.trim()) throw contractError();
      return { job_id: id };
    },
    async getJob(id, signal) { return parseJob(await request(`/jobs/${encodeURIComponent(id)}`, signal)); },
    async getClaim(id, signal) { return parseClaim(await request(`/claims/${encodeURIComponent(id)}`, signal)); },
    async listReviews(signal) {
      const result = record(await request('/reviews?status=pending', signal));
      if (!Array.isArray(result.items)) throw contractError();
      return result.items.map(parseClaim);
    },
    async review(id, input, signal) {
      if (!input.rationale.trim()) throw new ApiError('A review rationale is required.');
      return parseReview(await request(`/claims/${encodeURIComponent(id)}/reviews`, signal, input));
    },
  };
}
