import type { Claim, Job } from '../api/types';
export type Release = { kind: 'held' | 'waiting' | 'unavailable' | 'released' | 'annotated'; output: string | null };
export function claimRequiresReview(claim: Claim): boolean {
  if (claim.needs_review !== undefined) return claim.needs_review || !['supported', 'not_checkable'].includes(claim.effective_status ?? claim.finding);
  return claim.human_review ? claim.human_review.decision !== 'supported' : !['supported', 'not_checkable'].includes(claim.finding);
}
export function getRelease(job: Job | null, claims: Claim[], error?: string | null): Release {
  if (error || (job && ['failed', 'interrupted', 'provider_unavailable'].includes(job.status))) return { kind: 'unavailable', output: null };
  if (!job || ['queued', 'processing'].includes(job.status)) return { kind: 'waiting', output: null };
  if (job.status !== 'completed' || !['pass', 'annotate'].includes(job.overall_action ?? '')) return { kind: 'held', output: null };
  if (job.claim_ids.some(id => !claims.some(claim => claim.claim_id === id))) return { kind: 'held', output: null };
  return { kind: job.overall_action === 'pass' ? 'released' : 'annotated', output: job.revised_output ?? job.submitted_text };
}
export function safeSourceUrl(value: string): string | null {
  try { const url = new URL(value); return ['https:', 'http:'].includes(url.protocol) ? url.href : null; }
  catch { return null; }
}
export function isTerminal(status: string): boolean {
  return ['completed', 'review_pending', 'failed', 'interrupted', 'provider_unavailable'].includes(status);
}
