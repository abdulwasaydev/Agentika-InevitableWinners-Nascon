/** Temporary frontend view model. Reconcile with canonical OpenAPI before integration. */
export type Mode = 'live' | 'demo';
export type Action = 'pass' | 'annotate' | 'hold_for_review';
export type JobStatus = 'queued' | 'processing' | 'completed' | 'review_pending' | 'failed' | 'interrupted' | 'provider_unavailable';
export type Finding = 'supported' | 'challenged' | 'insufficient_evidence' | 'pending_review' | 'not_checkable';
export type ComparisonResult = 'consistent' | 'qualified' | 'conflicting' | 'insufficient_evidence';
export type Decision = 'supported' | 'challenged' | 'uncertain' | 'more_evidence';
export type Scenario = 'review' | 'pass' | 'annotate' | 'disputed' | 'insufficient' | 'failed' | 'interrupted' | 'provider_unavailable';

export interface Evidence {
  evidence_id: string;
  document_id?: string;
  title: string;
  url: string;
  excerpt: string;
  stance: 'supporting' | 'challenging' | 'context';
  source_type?: string;
  provenance?: string;
  retrieved_at?: string;
  validity_status?: string;
}
export interface SuppliedDocument { document_id: string; title: string; version?: string | null; effective_date?: string | null; text: string }
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
  comparison_result?: ComparisonResult | null;
  comparison_explanation?: string | null;
  unresolved_questions?: string[];
  human_review: Review | null;
  effective_status?: Finding;
  needs_review?: boolean;
  review_history?: Review[];
  assessments?: { role: string; position: string; reasoning_summary: string; evidence_ids: string[]; limitations?: string }[];
  parent_claim_ids?: string[];
}
export interface Job {
  job_id: string;
  status: JobStatus;
  submitted_text: string;
  documents?: SuppliedDocument[];
  overall_action: Action | null;
  claim_ids: string[];
  created_at: string;
  limitations: string[];
  reason_codes: string[];
  revised_output?: string | null;
  error?: string | null;
}
export interface Submission { text: string; mode?: 'guardian' | 'claim_court'; scenario?: Scenario; documents?: SuppliedDocument[] }
export interface VeritasApi {
  submit(input: Submission, signal?: AbortSignal): Promise<{ job_id: string }>;
  getJob(id: string, signal?: AbortSignal): Promise<Job>;
  getClaim(id: string, signal?: AbortSignal): Promise<Claim>;
  listReviews(signal?: AbortSignal): Promise<Claim[]>;
  review(id: string, input: ReviewInput, signal?: AbortSignal): Promise<Review>;
}
