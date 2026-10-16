import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, ArrowRight, CheckCircle2, ClipboardCheck, LoaderCircle, RefreshCw } from 'lucide-react';
import { useWorkspace } from '../Workspace';
import { useResource } from '../hooks/useResource';
import type { Decision, Job } from '../api/types';
import { Badge, EmptyState, ErrorPanel, EvidenceList, FindingBadge, Limitations, Loading, PageHeading, ReasonCodes, shortId } from '../components/ui';

export function QueuePage() {
  const { api } = useWorkspace();
  const load = useCallback((signal: AbortSignal) => api.listReviews(signal), [api]);
  const { data: claims, loading, error, refresh } = useResource(load);
  const [filter, setFilter] = useState('all');
  const filtered = (claims ?? []).filter(c => filter === 'all' || c.finding === filter);
  return <div className="page"><PageHeading eyebrow="HUMAN OVERSIGHT / REVIEW QUEUE" title="Where judgment matters." description="Uncertainty deserves attention. Examine the record, then leave a reasoned decision."><button className="button secondary" onClick={refresh}><RefreshCw size={14} />Refresh queue</button></PageHeading>
    <div className="queue-toolbar"><span><ClipboardCheck size={18} /><strong>{claims?.length ?? '—'}</strong> claims need attention</span><label>Show<select aria-label="Review filter" value={filter} onChange={event => setFilter(event.target.value)}><option value="all">All findings</option><option value="challenged">Disputed</option><option value="insufficient_evidence">Insufficient evidence</option><option value="not_checkable">Not checkable</option></select></label></div>
    {loading ? <Loading /> : error ? <ErrorPanel message={error} retry={refresh} /> : filtered.length === 0 ? <EmptyState title={claims?.length ? 'No claims match this filter.' : 'The review desk is clear.'} description={claims?.length ? 'Choose another finding to see the rest of the queue.' : 'Unresolved claims will appear here after a case has finished processing.'}><Link className="button secondary" to="/">Open Claim Court<ArrowRight size={15} /></Link></EmptyState> : <div className="queue-list">{filtered.map((claim, i) => <article className="panel queue-card" key={claim.claim_id}><div className="queue-card-top"><span className="mono">{shortId(claim.job_id)} / CLAIM {String(i + 1).padStart(2, '0')}</span><FindingBadge finding={claim.finding} /></div><h2>{claim.text}</h2><p>{claim.explanation}</p><ReasonCodes codes={claim.reason_codes} /><div className="queue-card-bottom"><span>{claim.human_review ? `Human reviewed · ${claim.human_review.decision} · still unresolved` : 'Provisional finding · awaiting human review'}</span><Link className="button secondary" to={`/reviews/${encodeURIComponent(claim.claim_id)}`}>Examine & review<ArrowRight size={15} /></Link></div></article>)}</div>}
  </div>;
}

export function ReviewPage() {
  const { claimId = '' } = useParams(); const { api, mode } = useWorkspace();
  const load = useCallback((signal: AbortSignal) => api.getClaim(claimId, signal), [api, claimId]);
  const { data: claim, loading, error, refresh } = useResource(load);
  const [decision, setDecision] = useState<Decision | ''>('');
  const [rationale, setRationale] = useState(''); const [correction, setCorrection] = useState('');
  const [busy, setBusy] = useState(false); const [saveError, setSaveError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false); const [latest, setLatest] = useState<Job | null>(null);
  const request = useRef<AbortController | null>(null);
  useEffect(() => () => request.current?.abort(), []);
  useEffect(() => { setDecision(''); setRationale(''); setCorrection(''); setSuccess(false); setLatest(null); setSaveError(null); }, [claimId]);
  async function save(event: FormEvent) {
    event.preventDefault(); if (!claim || !decision || !rationale.trim() || busy) return;
    const controller = new AbortController(); request.current?.abort(); request.current = controller;
    setBusy(true); setSaveError(null); setSuccess(false); setLatest(null);
    try {
      await api.review(claimId, { decision, rationale, ...(correction.trim() ? { correction } : {}) }, controller.signal);
      if (controller.signal.aborted) return;
      setSuccess(true);
      // A persisted review is not approval. Always fetch the recalculated job.
      const updated = await api.getJob(claim.job_id, controller.signal);
      if (!controller.signal.aborted) setLatest(updated);
    } catch (failure) { if (!controller.signal.aborted) setSaveError(failure instanceof Error ? failure.message : 'Could not save this review.'); }
    finally { if (!controller.signal.aborted) setBusy(false); }
  }
  return <div className="page"><Link className="back-link" to="/reviews"><ArrowLeft size={14} />Review queue</Link><PageHeading eyebrow="HUMAN OVERSIGHT / CASE REVIEW" title="Record a human decision" description="A decision without a rationale is just another claim. Show your reasoning." />{loading ? <Loading /> : error ? <ErrorPanel message={error} retry={refresh} /> : claim && <>
    <div className="review-grid"><div><section className="panel claim-focus"><div className="claim-meta"><FindingBadge finding={claim.finding} /><span className="review-label">Provisional machine finding</span></div><h2>{claim.text}</h2><p>{claim.explanation}</p><ReasonCodes codes={claim.reason_codes} /></section><div className="section-heading"><h2>Read the evidence</h2></div><EvidenceList evidence={claim.evidence} /><Limitations items={claim.limitations} />{claim.human_review && <div className="human-note"><Badge tone="info">Previous human decision · {claim.human_review.decision}</Badge><p>{claim.human_review.rationale}</p>{claim.human_review.correction && <><h3>Previous correction · separate from original</h3><p>{claim.human_review.correction}</p></>}</div>}</div>
    <form className="panel review-form" onSubmit={save}><div className="panel-header"><div><ClipboardCheck size={18} /><h2>Your assessment</h2></div></div>{mode === 'demo' && <p className="form-demo-note">Simulated human review of fictional evidence.</p>}<fieldset><legend>Decision</legend>{([['supported', 'Supported', 'The record supports this claim.'], ['challenged', 'Disputed', 'The evidence contradicts the claim.'], ['uncertain', 'Still uncertain', 'The record cannot settle this claim.']] as const).map(([value, label, help]) => <label className={`decision-option ${decision === value ? 'selected' : ''}`} key={value}><input type="radio" name="decision" value={value} checked={decision === value} onChange={() => { setDecision(value); setSuccess(false); }} required /><span><strong>{label}</strong><small>{help}</small></span></label>)}</fieldset><label htmlFor="rationale">Rationale<span className="required-mark"> *</span></label><textarea id="rationale" value={rationale} onChange={event => { setRationale(event.target.value); setSuccess(false); }} placeholder="Explain what the evidence does or does not establish…" required maxLength={5000} /><label htmlFor="correction">Suggested correction <span className="muted">(optional)</span></label><textarea id="correction" value={correction} onChange={event => { setCorrection(event.target.value); setSuccess(false); }} placeholder="A correction is kept separate from the original wording." maxLength={5000} /><p className="form-hint">Disputed and unresolved decisions keep the demo release gate closed. Saving alone never releases output.</p>{saveError && <ErrorPanel message={success ? `The review was saved, but the latest release decision is unavailable. ${saveError}` : saveError} />}{success && <div className="review-success" role="status"><CheckCircle2 size={19} /><div><strong>Review saved.</strong><p>{latest ? `Latest service action: ${latest.overall_action ?? 'not yet decided'}. Guardian will check this job again.` : 'Refreshing the release decision. Content remains withheld until it can be checked.'}</p></div></div>}<button className="button primary full-width" type="submit" disabled={busy || !decision || !rationale.trim() || success}>{busy ? <LoaderCircle size={16} className="spin" /> : <CheckCircle2 size={16} />}{busy ? 'Saving & checking…' : 'Save review'}</button></form></div>
    <div className="section-actions button-row"><Link className="button secondary" to="/reviews">Back to review queue</Link><Link className="button primary" to={`/guardian/${encodeURIComponent(claim.job_id)}`}>Return to Guardian<ArrowRight size={15} /></Link></div>
  </>}</div>;
}
