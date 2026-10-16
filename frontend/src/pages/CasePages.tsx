import { useCallback } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, ArrowRight, Check, Clock, FileText, GitBranch, LoaderCircle, RefreshCw, ShieldCheck } from 'lucide-react';
import { useWorkspace } from '../Workspace';
import { useJob } from '../hooks/useJob';
import { useResource } from '../hooks/useResource';
import { isTerminal } from '../domain/release';
import { Badge, ClaimCards, ErrorPanel, EvidenceList, FindingBadge, formatDate, Limitations, Loading, PageHeading, ReasonCodes, shortId } from '../components/ui';
import type { Job } from '../api/types';

export function JobProgress({ job }: { job: Job | null }) {
  const step = !job || job.status === 'queued' ? 0 : 1;
  return <section className="panel progress-panel" role="status"><div className="progress-symbol"><LoaderCircle size={27} className="spin" /></div><h2>Verification in progress</h2><p>The passage is on the record. Gathering the evidence takes a moment.</p><div className="progress-steps">{['Case submitted', 'Examining claims', 'Evidence & decision'].map((label, i) => <div key={label} className={i <= step ? 'current' : ''}><span>{i < step ? <Check size={13} /> : i + 1}</span>{label}</div>)}</div></section>;
}
export function JobNotice({ job }: { job: Job }) {
  const { mode } = useWorkspace();
  if (['failed', 'interrupted', 'provider_unavailable'].includes(job.status)) return <ErrorPanel message={job.error ?? `Verification ${job.status.replaceAll('_', ' ')}. No output is approved.`} />;
  return <div className={`job-notice ${job.overall_action === 'hold_for_review' ? 'notice-warning' : 'notice-success'}`}><ShieldCheck size={23} /><div><strong>{job.overall_action === 'hold_for_review' ? 'A human hearing is needed.' : job.overall_action === 'annotate' ? 'Available with claim-level caveats.' : 'Release permitted by the verification service.'}</strong><p>{job.overall_action === 'hold_for_review' ? 'Unresolved findings keep the release gate closed. Inspect the evidence before making a decision.' : mode === 'demo' ? 'This is a simulated release decision based only on fictional documents.' : 'The latest job response permits this output. Read all findings and limitations.'}</p></div></div>;
}
export function CasePage() {
  const { jobId = '' } = useParams(); const { api } = useWorkspace();
  const { job, claims, loading, error, refresh } = useJob(api, jobId);
  return <div className="page"><Link className="back-link" to="/"><ArrowLeft size={14} />Claim Court</Link><PageHeading eyebrow={`CASE RECORD / ${shortId(jobId)}`} title="Follow the evidence." description="The original passage, its claims, and the record behind every finding."><button className="button secondary" onClick={refresh}><RefreshCw size={14} />Refresh case</button></PageHeading>
    {error ? <ErrorPanel message={error} retry={refresh} /> : loading || !job || !isTerminal(job.status) ? <JobProgress job={job} /> : <>
      <div className="case-meta"><span className="mono">{shortId(job.job_id)}</span><span><Clock size={13} />{formatDate(job.created_at)} PKT</span><Badge tone={job.status === 'completed' ? 'success' : 'warning'}>{job.status.replaceAll('_', ' ')}</Badge></div><JobNotice job={job} />
      <div className="case-summary"><div><span>{claims.length.toString().padStart(2, '0')}</span><p>Extracted claims</p></div><div><span>{claims.filter(c => c.finding === 'supported').length.toString().padStart(2, '0')}</span><p>Machine supported</p></div><div><span>{claims.filter(c => c.human_review ? c.human_review.decision !== 'supported' : c.finding !== 'supported').length.toString().padStart(2, '0')}</span><p>Unresolved claims</p></div></div>
      <details className="original-text"><summary><FileText size={15} />Original submitted text<span>Unmodified record</span></summary><p className="preserve-text">{job.submitted_text}</p></details>
      <div className="section-heading"><h2>Extracted claims</h2><span className="muted">Machine findings are provisional</span></div>{claims.length ? <ClaimCards claims={claims} /> : <p className="muted">No claim findings are available for this case.</p>}
      <Limitations items={job.limitations} /><ReasonCodes codes={job.reason_codes} /><div className="button-row section-actions"><Link className="button secondary" to={`/lineage/${encodeURIComponent(jobId)}`}><GitBranch size={15} />View lineage</Link><Link className="button primary" to={`/guardian/${encodeURIComponent(jobId)}`}><ShieldCheck size={16} />Open Guardian<ArrowRight size={15} /></Link></div>
    </>}
  </div>;
}
export function ClaimPage() {
  const { claimId = '' } = useParams(); const { api } = useWorkspace();
  const load = useCallback((signal: AbortSignal) => api.getClaim(claimId, signal), [api, claimId]);
  const { data: claim, loading, error, refresh } = useResource(load);
  return <div className="page"><Link className="back-link" to={claim ? `/jobs/${encodeURIComponent(claim.job_id)}` : '/'}><ArrowLeft size={14} />Case record</Link><PageHeading eyebrow="CLAIM COURT / EVIDENCE FILE" title="A closer look." description="Read the finding against its sources. Keep the limits in view." />{loading ? <Loading /> : error ? <ErrorPanel message={error} retry={refresh} /> : claim && <>
    <section className="panel claim-focus"><div className="claim-meta"><FindingBadge finding={claim.finding} /><span className="review-label">Provisional machine finding</span></div><h2>{claim.text}</h2><p>{claim.explanation}</p><ReasonCodes codes={claim.reason_codes} /></section>
    {claim.human_review && <section className="human-note"><Badge tone="info">Human reviewed · {claim.human_review.decision}</Badge><h3>Human rationale</h3><p className="preserve-text">{claim.human_review.rationale}</p>{claim.human_review.correction && <><h3>Suggested correction · separate from original</h3><p className="preserve-text">{claim.human_review.correction}</p></>}</section>}
    <div className="section-heading"><h2>Evidence on the record</h2><span className="muted">{claim.evidence.length} source records</span></div><EvidenceList evidence={claim.evidence} /><Limitations items={claim.limitations} /><div className="section-actions button-row"><Link to={`/guardian/${encodeURIComponent(claim.job_id)}`} className="button secondary">Open Guardian</Link><Link to={`/reviews/${encodeURIComponent(claim.claim_id)}`} className="button primary">{claim.human_review ? 'Update human review' : 'Review claim'}<ArrowRight size={15} /></Link></div>
  </>}</div>;
}
