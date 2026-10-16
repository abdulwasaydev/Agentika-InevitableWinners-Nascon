/** Temporary frontend view model. Reconcile with canonical OpenAPI before integration. */
export type Mode = 'live' | 'demo';
export type Action = 'pass' | 'annotate' | 'hold_for_review';
export type JobStatus = 'queued' | 'processing' | 'completed' | 'review_pending' | 'failed' | 'interrupted' | 'provider_unavailable';
export type Finding = 'supported' | 'challenged' | 'insufficient_evidence' | 'not_checkable';
export type Decision = 'supported' | 'challenged' | 'uncertain';
export type Scenario = 'review' | 'pass' | 'annotate' | 'disputed' | 'insufficient' | 'failed' | 'interrupted' | 'provider_unavailable';

export interface Evidence {
  evidence_id: string;
  document_id?: string;
  title: string;
  url: string;
  excerpt: string;
  stance: 'supporting' | 'challenging' | 'context';
}
export interface ReviewInput { decision: Decision; rationale: string; correction?: string }
export interface Review extends ReviewInput { review_id: string; claim_id: string; created_at: string }
export interface Claim {
  claim_id: string;
  job_id: string;
  text: string;
  finding: Finding;
  explanation: string;
  evidence: Evidence[];
  limitations: string[];
  reason_codes: string[];
  human_review: Review | null;
}
export interface Job {
  job_id: string;
  status: JobStatus;
  submitted_text: string;
  overall_action: Action | null;
  claim_ids: string[];
  created_at: string;
  limitations: string[];
  reason_codes: string[];
  revised_output?: string | null;
  error?: string | null;
}
export interface Submission { text: string; scenario?: Scenario }
export interface VeritasApi {
  submit(input: Submission, signal?: AbortSignal): Promise<{ job_id: string }>;
  getJob(id: string, signal?: AbortSignal): Promise<Job>;
  getClaim(id: string, signal?: AbortSignal): Promise<Claim>;
  listReviews(signal?: AbortSignal): Promise<Claim[]>;
  review(id: string, input: ReviewInput, signal?: AbortSignal): Promise<Review>;
}
