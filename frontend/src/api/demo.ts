import type { Claim, Job, Review, Scenario, VeritasApi } from './types';
import { ApiError } from './client';
export const DEMO_TEXT = 'The Aster Observatory opened in 2018. Its telescope is the largest on Earth. It welcomes visitors every weekend.';
export const DEMO_DOCUMENTS = [
  { id: 'SYN-REG-001', title: 'Aster Observatory · Founding register', text: 'SYNTHETIC DOCUMENT — fictional material for interface testing only. The Aster Observatory opened in 2018. The inaugural visitor log records the opening on 14 June 2018.' },
  { id: 'SYN-TECH-002', title: 'Aster Observatory · Instrument inventory', text: 'SYNTHETIC DOCUMENT — fictional material for interface testing only. The telescope has a 2.4-metre primary mirror. This internal inventory makes no comparison with instruments at other observatories.' },
  { id: 'SYN-VIS-003', title: 'Aster Observatory · Visitor circular', text: 'SYNTHETIC DOCUMENT — fictional material for interface testing only. Public visits are available on selected weekends by appointment. The observatory is closed to visitors during maintenance.' },
];
export interface DemoApi extends VeritasApi { reset(): void }
type Entry = { job: Job; claims: Claim[]; tick: number; scenario: Scenario };
const STORAGE_KEY = 'veritas.synthetic.v1';
const clone = <T,>(value: T): T => JSON.parse(JSON.stringify(value)) as T;

export function createDemoApi(storage?: Storage): DemoApi {
  const entries = new Map<string, Entry>();
  try {
    const stored = JSON.parse(storage?.getItem(STORAGE_KEY) ?? '[]') as Entry[];
    if (Array.isArray(stored)) for (const item of stored) {
      if (item?.job?.job_id?.startsWith('demo-') && Array.isArray(item.claims) && typeof item.tick === 'number') entries.set(item.job.job_id, item);
    }
  } catch { /* Corrupt local demo data is ignored; no live data is involved. */ }
  function save() { try { storage?.setItem(STORAGE_KEY, JSON.stringify([...entries.values()])); } catch { /* Demo remains usable without persistence. */ } }
  function check(signal?: AbortSignal) { signal?.throwIfAborted(); }
  function entry(id: string) { const value = entries.get(id); if (!value) throw new ApiError('Synthetic case not found. Start a new case or reset the demo.', 404); return value; }
  function claim(id: string) {
    for (const value of entries.values()) { const c = value.claims.find(item => item.claim_id === id); if (c) return { value, c }; }
    throw new ApiError('Synthetic claim not found.', 404);
  }
  function recalculate(value: Entry) {
    const unresolved = value.claims.some(c => c.human_review ? c.human_review.decision !== 'supported' : c.finding !== 'supported');
    value.job.status = unresolved ? 'review_pending' : 'completed';
    value.job.overall_action = unresolved ? 'hold_for_review' : value.scenario === 'pass' ? 'pass' : 'annotate';
    value.job.reason_codes = unresolved ? ['unresolved_claims', 'human_review_required'] : value.scenario === 'pass' ? ['all_claims_supported'] : ['review_resolved', 'scope_limitations'];
  }
  return {
    async submit(input, signal) {
      check(signal);
      if (!input.text.trim() || input.text.length > 20000) throw new ApiError('Enter claim text between 1 and 20,000 characters.');
      const id = `demo-${crypto.randomUUID()}`;
      const scenario = input.scenario ?? 'review';
      const sentences = input.text.match(/[^.!?]+[.!?]?/g)?.map(s => s.trim()).filter(Boolean) ?? [input.text];
      const texts = sentences.slice(0, 8);
      const findings: Claim['finding'][] = scenario === 'pass' || scenario === 'annotate' ? ['supported'] : scenario === 'disputed' ? ['challenged'] : scenario === 'insufficient' ? ['insufficient_evidence'] : ['supported', 'insufficient_evidence', 'challenged'];
      const claims: Claim[] = texts.map((text, i) => {
        const finding = findings[i % findings.length];
        const doc = DEMO_DOCUMENTS[i % DEMO_DOCUMENTS.length];
        return { claim_id: `${id}-c${i + 1}`, job_id: id, text, finding, explanation: finding === 'supported' ? 'The synthetic record supports this statement within the fictional scenario.' : finding === 'challenged' ? 'The synthetic visitor record challenges the absolute wording. A human decision is required.' : 'The synthetic inventory cannot establish this comparison. More evidence is needed.', evidence: [{ evidence_id: `${id}-e${i + 1}`, document_id: doc.id, title: doc.title, url: '', excerpt: doc.text, stance: finding === 'challenged' ? 'challenging' : finding === 'supported' ? 'supporting' : 'context' }], limitations: ['Synthetic evidence only. This is not a factual verification of your submitted text.'], reason_codes: [finding === 'challenged' ? 'source_conflict' : finding === 'supported' ? 'synthetic_support' : 'insufficient_independent_sources'], human_review: null };
      });
      entries.set(id, { job: { job_id: id, status: 'queued', submitted_text: input.text, overall_action: null, claim_ids: claims.map(c => c.claim_id), created_at: new Date().toISOString(), limitations: ['Fictional documents and simulated decisions. No external verification has occurred.', ...(sentences.length > 8 ? ['Only the first eight sentence fragments are represented in this synthetic case.'] : [])], reason_codes: ['synthetic_demo'] }, claims, tick: 0, scenario });
      save(); return { job_id: id };
    },
    async getJob(id, signal) {
      check(signal); const value = entry(id);
      if (value.tick === 0) value.job.status = 'queued';
      else if (value.tick === 1) value.job.status = 'processing';
      else if (['failed', 'interrupted', 'provider_unavailable'].includes(value.scenario)) {
        value.job.status = value.scenario as Job['status']; value.job.overall_action = 'hold_for_review';
        value.job.error = value.scenario === 'interrupted' ? 'Simulated verification was interrupted before evidence review finished.' : value.scenario === 'provider_unavailable' ? 'Simulated evidence provider is unavailable.' : 'Simulated verification failed. No findings are approved.';
      } else recalculate(value);
      value.tick += 1; save(); return clone(value.job);
    },
    async getClaim(id, signal) { check(signal); return clone(claim(id).c); },
    async listReviews(signal) {
      check(signal);
      return clone([...entries.values()].filter(e => e.job.status === 'review_pending').flatMap(e => e.claims.filter(c => c.human_review ? c.human_review.decision !== 'supported' : c.finding !== 'supported')));
    },
    async review(id, input, signal) {
      check(signal);
      if (!input.rationale.trim()) throw new ApiError('A review rationale is required.');
      const { value, c } = claim(id);
      if (!['review_pending', 'completed'].includes(value.job.status)) throw new ApiError('This case is not ready for a review.');
      const review: Review = { ...input, review_id: `demo-review-${crypto.randomUUID()}`, claim_id: id, created_at: new Date().toISOString() };
      c.human_review = review; recalculate(value); save(); return clone(review);
    },
    reset() { entries.clear(); save(); },
  };
}
