import { useCallback } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, ArrowRight, Check, Clock, FileText, GitBranch, LoaderCircle, RefreshCw, ShieldCheck } from 'lucide-react';
import { useWorkspace } from '../Workspace';
import { useJob } from '../hooks/useJob';
import { useResource } from '../hooks/useResource';
import { claimRequiresReview, isTerminal } from '../domain/release';
import { Badge, ClaimCards, ErrorPanel, EvidenceList, FindingBadge, formatDate, Limitations, Loading, PageHeading, ReasonCodes, shortId } from '../components/ui';
import type { Job } from '../api/types';

const comparisonLabels = { consistent: 'Supported by cited policy passages', qualified: 'Qualified by a policy condition', conflicting: 'Challenged by a policy passage', insufficient_evidence: 'Insufficient policy evidence' } as const;

export function JobProgress({ job }: { job: Job | null }) {
  const step = !job || job.status === 'queued' ? 0 : 1;
  return <section className="panel progress-panel" role="status"><div className="progress-symbol"><LoaderCircle size={27} className="spin" /></div><h2>Verification in progress</h2><p>Your text has been received. Gathering the evidence takes a moment.</p><div className="progress-steps">{['Check submitted', 'Examining claims', 'Evidence & decision'].map((label, i) => <div key={label} className={i <= step ? 'current' : ''}><span>{i < step ? <Check size={13} /> : i + 1}</span>{label}</div>)}</div></section>;
}
export function JobNotice({ job }: { job: Job }) {
  const { mode } = useWorkspace();
  if (['failed', 'interrupted', 'provider_unavailable'].includes(job.status)) return <ErrorPanel message={job.error ?? `Verification ${job.status.replaceAll('_', ' ')}. No output is approved.`} />;
  return <div className={`job-notice ${job.overall_action === 'hold_for_review' ? 'notice-warning' : 'notice-success'}`}><ShieldCheck size={23} /><div><strong>{job.overall_action === 'hold_for_review' ? 'A human review is needed.' : job.overall_action === 'annotate' ? 'Available with claim-level caveats.' : 'Release permitted by the verification service.'}</strong><p>{job.overall_action === 'hold_for_review' ? 'Unresolved findings keep the release gate closed. Inspect the evidence before making a decision.' : mode === 'demo' ? 'This is a simulated release decision based only on fictional documents.' : 'The latest job response permits this output. Read all findings and limitations.'}</p></div></div>;
}
export function CasePage() {
  const { jobId = '' } = useParams(); const { api } = useWorkspace();
  const { job, claims, loading, error, refresh } = useJob(api, jobId);
  return <div className="page"><Link className="back-link" to="/"><ArrowLeft size={14} />Policy Check</Link><PageHeading eyebrow={`CHECK RESULT / ${shortId(jobId)}`} title="Follow the evidence." description="The submitted text, claim findings, and sources behind each conclusion."><button className="button secondary" onClick={refresh}><RefreshCw size={14} />Refresh check</button></PageHeading>
    {error ? <ErrorPanel message={error} retry={refresh} /> : loading || !job || !isTerminal(job.status) ? <JobProgress job={job} /> : <>
      <div className="case-meta"><span className="mono">{shortId(job.job_id)}</span><span><Clock size={13} />{formatDate(job.created_at)} PKT</span><Badge tone={job.status === 'completed' ? 'success' : 'warning'}>{job.status.replaceAll('_', ' ')}</Badge></div><JobNotice job={job} />
      {claims[0]?.comparison_result && <section className={`comparison-banner comparison-${claims[0].comparison_result}`}>
        <span className="eyebrow">{job.origin === 'official_github_policy' ? 'OFFICIAL POLICY / TWO AGENT SCAN' : job.origin === 'user_pasted_github_policy' ? 'PASTED POLICY / TWO AGENT SCAN' : 'SUPPLIED DOCUMENT COMPARISON'}</span>
        <h2>{comparisonLabels[claims[0].comparison_result]}</h2><p>{claims[0].comparison_explanation}</p>
        {claims[0].evidence.find(item => item.stance === 'challenging') && <blockquote>{claims[0].evidence.find(item => item.stance === 'challenging')?.excerpt}</blockquote>}
        <p className="muted">{job.origin === 'official_github_policy' ? 'Citations come from a downloaded GitHub privacy statement. The two LLM notes are provisional; a person must review them before release.' : job.origin === 'user_pasted_github_policy' ? 'Citations come only from your pasted text. Its authenticity and completeness were not verified; human review is required before release.' : 'Based only on the supplied policy text. This does not establish real-world practice.'}</p>
      </section>}
      <div className="case-summary"><div><span>{claims.length.toString().padStart(2, '0')}</span><p>Extracted claims</p></div><div><span>{claims.filter(c => c.finding === 'supported').length.toString().padStart(2, '0')}</span><p>Machine supported</p></div><div><span>{claims.filter(claimRequiresReview).length.toString().padStart(2, '0')}</span><p>Unresolved claims</p></div></div>
      <details className="original-text"><summary><FileText size={15} />Original submitted text<span>Unmodified record</span></summary><p className="preserve-text">{job.submitted_text}</p></details>
      {!!job.documents?.length && <section className="supplied-documents"><div className="section-heading"><h2>Supplied policy documents</h2><span className="muted">{job.documents.length} original records</span></div>{job.documents.map(document => <details className="original-text" key={document.document_id}><summary><FileText size={15} />{document.title}<span>{document.document_id}{document.version ? ` · ${document.version}` : ''}</span></summary><p className="muted">{document.effective_date ? `Effective date: ${document.effective_date}` : 'No effective date supplied'}</p><p className="preserve-text">{document.text}</p></details>)}</section>}
      <div className="section-heading"><h2>Extracted claims</h2><span className="muted">Machine findings are provisional</span></div>{claims.length ? <ClaimCards claims={claims} /> : <p className="muted">No claim findings are available for this check.</p>}
      <Limitations items={job.limitations} /><ReasonCodes codes={job.reason_codes} /><div className="button-row section-actions"><Link className="button secondary" to={`/lineage/${encodeURIComponent(jobId)}`}><GitBranch size={15} />View lineage</Link><Link className="button primary" to={`/guardian/${encodeURIComponent(jobId)}`}><ShieldCheck size={16} />Open Guardian<ArrowRight size={15} /></Link></div>
    </>}
  </div>;
}
export function ClaimPage() {
  const { claimId = '' } = useParams(); const { api } = useWorkspace();
  const load = useCallback((signal: AbortSignal) => api.getClaim(claimId, signal), [api, claimId]);
  const { data: claim, loading, error, refresh } = useResource(load);
  return <div className="page"><Link className="back-link" to={claim ? `/jobs/${encodeURIComponent(claim.job_id)}` : '/'}><ArrowLeft size={14} />Check result</Link><PageHeading eyebrow="CLAIM / SOURCE NOTES" title="A closer look." description="Read the finding against its sources. Keep the limits in view." />{loading ? <Loading /> : error ? <ErrorPanel message={error} retry={refresh} /> : claim && <>
    <section className="panel claim-focus"><div className="claim-meta"><FindingBadge finding={claim.finding} /><span className="review-label">Provisional machine finding</span></div><h2>{claim.text}</h2><p>{claim.explanation}</p>{claim.effective_status && <p><strong>Effective status:</strong> {claim.effective_status.replaceAll('_', ' ')}{claim.needs_review ? ' · human review required' : ''}</p>}<ReasonCodes codes={claim.reason_codes} /></section>
    {claim.comparison_result && <section className={`comparison-banner comparison-${claim.comparison_result}`}><span className="eyebrow">{claim.evidence.some(item => item.source_type === 'official_privacy_policy') ? 'OFFICIAL POLICY / LLM SCAN' : claim.evidence.some(item => item.source_type === 'user_supplied_privacy_policy') ? 'PASTED POLICY / LLM SCAN' : 'SUPPLIED POLICY / WORDING CHECK'}</span><h2>{comparisonLabels[claim.comparison_result]}</h2><p>{claim.comparison_explanation}</p>{!!claim.unresolved_questions?.length && <div><strong>Questions to clarify</strong><ul>{claim.unresolved_questions.map(question => <li key={question}>{question}</li>)}</ul></div>}</section>}
    {(claim.review_history?.length ? claim.review_history : claim.human_review ? [claim.human_review] : []).map(review => <section className="human-note" key={review.review_id}><Badge tone="info">Human review · {review.decision}</Badge><h3>Rationale · {formatDate(review.created_at)}</h3><p className="preserve-text">{review.rationale}</p>{review.correction && <><h3>Suggested correction · separate from original</h3><p className="preserve-text">{review.correction}</p></>}</section>)}
    <div className="section-heading"><h2>Source passages</h2><span className="muted">{claim.evidence.length} source records</span></div>{claim.comparison_result ? <div className="comparison-evidence"><section><h3>Supporting passages</h3><EvidenceList evidence={claim.evidence.filter(item => item.stance === 'supporting')} /></section><section><h3>Exceptions or conflicts</h3><EvidenceList evidence={claim.evidence.filter(item => item.stance === 'challenging')} challengeTone={claim.comparison_result === 'qualified' ? 'warning' : 'danger'} /></section></div> : <EvidenceList evidence={claim.evidence} />}
    {!!claim.assessments?.length && <section className="assessment-list"><div className="section-heading"><h2>Two agent notes</h2><span className="muted">Each quote must match the source text</span></div><div className="agent-grid">{claim.assessments.map(assessment => <article className={`panel assessment-card agent-${assessment.role}`} key={assessment.role}>
      <Badge tone={assessment.role === 'support' ? 'success' : 'danger'}>{assessment.role === 'support' ? 'In favor' : 'Against'} / {assessment.position.replaceAll('_', ' ')}</Badge>
      <p>{assessment.reasoning_summary}</p>
      {claim.evidence.filter(item => assessment.evidence_ids.includes(item.evidence_id)).map(item => <div className="agent-citation" key={item.evidence_id}><blockquote>{item.excerpt}</blockquote>{item.url ? <a href={item.url} target="_blank" rel="noopener noreferrer">{item.title} <ArrowRight size={13} /></a> : <span className="muted">{item.title}</span>}</div>)}
      {!assessment.evidence_ids.length && <p className="muted">No direct passage cited for this position.</p>}
      {assessment.limitations && <small>{assessment.limitations}</small>}
    </article>)}</div></section>}
    <Limitations items={claim.limitations} /><div className="section-actions button-row"><Link to={`/guardian/${encodeURIComponent(claim.job_id)}`} className="button secondary">Open Guardian</Link><Link to={`/reviews/${encodeURIComponent(claim.claim_id)}`} className="button primary">{claim.human_review ? 'Update human review' : 'Review claim'}<ArrowRight size={15} /></Link></div>
  </>}</div>;
}
