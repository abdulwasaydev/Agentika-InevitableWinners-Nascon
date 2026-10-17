import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, ArrowUpRight, Check, CornerDownLeft, FileText, LoaderCircle, ScanText, ShieldCheck, Sparkles } from 'lucide-react';
import { useWorkspace } from '../Workspace';
import { DEMO_TEXT } from '../api/demo';
import type { Scenario, SuppliedDocument } from '../api/types';
import { Badge, ErrorPanel, formatDate, shortId } from '../components/ui';

export function CourtPage({ guardian = false }: { guardian?: boolean }) {
  const { api, mode, recent, remember } = useWorkspace();
  const navigate = useNavigate();
  const [text, setText] = useState('');
  const [comparePolicies, setComparePolicies] = useState(false);
  const [officialPolicy, setOfficialPolicy] = useState(false);
  const [policyText, setPolicyText] = useState(() => {
    try { return sessionStorage.getItem('veritas.githubPolicyDraft') ?? ''; } catch { return ''; }
  });
  const [documents, setDocuments] = useState<SuppliedDocument[]>([
    { document_id: 'POLICY-1', title: '', version: '', effective_date: '', text: '' },
    { document_id: 'POLICY-2', title: '', version: '', effective_date: '', text: '' },
  ]);
  const [scenario, setScenario] = useState<Scenario>('review');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const controller = useRef<AbortController | null>(null);
  function updateDocument(index: number, field: keyof SuppliedDocument, value: string) {
    setDocuments(current => current.map((document, position) => position === index ? { ...document, [field]: value } : document));
  }
  function updatePolicyText(value: string) {
    setPolicyText(value);
    try { if (value) sessionStorage.setItem('veritas.githubPolicyDraft', value); else sessionStorage.removeItem('veritas.githubPolicyDraft'); } catch { /* Session storage is optional. */ }
  }
  function clearForm() {
    setText(''); setComparePolicies(false); setOfficialPolicy(false); setError(null);
    updatePolicyText('');
    setDocuments([{ document_id: 'POLICY-1', title: '', version: '', effective_date: '', text: '' }, { document_id: 'POLICY-2', title: '', version: '', effective_date: '', text: '' }]);
  }
  useEffect(() => () => controller.current?.abort(), []);
  async function submit(event: FormEvent) {
    event.preventDefault(); if (busy || !text.trim()) return;
    controller.current?.abort(); const request = new AbortController(); controller.current = request;
    setBusy(true); setError(null);
    try {
      const supplied = comparePolicies && !officialPolicy ? documents.filter(document => document.text.trim()) : [];
      if (comparePolicies && (!supplied.length || supplied.some(document => !document.document_id.trim() || !document.title.trim()))) {
        setError('Add a policy document with an ID, title, and text.'); setBusy(false); return;
      }
      const result = await api.submit({ text, mode: guardian ? 'guardian' : 'claim_court', documents: supplied, ...(officialPolicy ? { policy_source: 'github_privacy' as const } : {}), ...(officialPolicy && policyText.trim() ? { policy_text: policyText.trim() } : {}), ...(mode === 'demo' ? { scenario } : {}) }, request.signal);
      if (request.signal.aborted) return;
      remember(result.job_id, text); navigate(`/${guardian ? 'guardian' : 'jobs'}/${encodeURIComponent(result.job_id)}`);
    } catch (failure) { if (!request.signal.aborted) setError(failure instanceof Error ? failure.message : 'Submission failed.'); }
    finally { if (!request.signal.aborted) setBusy(false); }
  }
  const officialPanel = mode === 'live' ? <section className="official-source-panel">
    <div className="official-source-top"><span className="eyebrow">REAL DOCUMENT / GITHUB</span><a href="https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement" target="_blank" rel="noopener noreferrer">Read the published policy <ArrowUpRight size={13} /></a></div>
    <label className="official-source-choice"><input type="checkbox" checked={officialPolicy} onChange={event => { setOfficialPolicy(event.target.checked); setComparePolicies(false); setError(null); }} /><span><strong>Scan GitHub's privacy statement</strong><small>Two LLM roles read relevant passages from a downloaded official document and cite exact text.</small></span></label>
    {officialPolicy && <><label className="full-policy-label" htmlFor="full-policy-text">Paste the entire GitHub privacy statement (optional)</label><textarea id="full-policy-text" className="full-policy-editor" value={policyText} onChange={event => updatePolicyText(event.target.value)} maxLength={100000} rows={9} placeholder="Paste the full policy here, or leave this empty to scan the downloaded GitHub Docs snapshot." /><p className="muted policy-source-note">{policyText.trim() ? `Pasted source: ${policyText.length.toLocaleString()} characters, saved in this browser session. Its authenticity and completeness are unverified; cited quotes come only from what you pasted.` : 'Using the downloaded official GitHub Docs snapshot. No document paste is needed.'}</p><div className="claim-suggestions"><span>Test three claims live</span><button type="button" onClick={() => setText('GitHub never uses personal data to train AI models.')}>“GitHub never uses personal data to train AI models.”</button><button type="button" onClick={() => setText('GitHub collects email addresses when users create an account.')}>“GitHub collects email addresses when users create an account.”</button><button type="button" onClick={() => setText('GitHub shares personal data with service providers.')}>“GitHub shares personal data with service providers.”</button></div></>}
  </section> : null;
  return <div className="page court-page">
    <div className="court-hero"><div><div className="eyebrow"><span className="tiny-line" />{guardian ? 'GUARDIAN / CONTROLLED RELEASE' : mode === 'live' ? 'PRIVACY POLICY / CLAIM CHECK' : 'NEW CHECK / CLAIM'}</div><h1>{guardian ? <>Check before<br /><em>you share.</em></> : mode === 'live' ? <>Read the policy.<br /><em>Check the claim.</em></> : <>Find the source.<br /><em>See both sides.</em></>}</h1><p>{guardian ? 'Watch the release gate hold a draft, route uncertainty to a human, and obey the latest verification decision.' : mode === 'live' ? 'Check a claim against a published privacy policy, or compare a promise with supplied documents. See source passages, exceptions, and unanswered questions.' : 'Start with a claim. Trace it to evidence, see both sides, and review uncertain findings.'}</p></div><div className="hero-seal"><ScanText size={39} strokeWidth={1.25} /><span>QUESTION.<br />VERIFY.<br />UNDERSTAND.</span><span className="seal-corner">↗</span></div></div>
    <div className="court-grid"><section className="panel submission-panel"><div className="panel-header"><div><span className="section-index">01</span><h2>{guardian ? 'Prepare a guarded draft' : mode === 'live' ? officialPolicy ? 'Scan a privacy policy' : 'Compare a promise' : 'Check a claim'}</h2></div><Badge tone="neutral">{mode === 'demo' ? 'Synthetic check' : officialPolicy ? 'Official policy scan' : comparePolicies ? 'Document comparison' : 'Text submission'}</Badge></div>
      <form onSubmit={submit}>{officialPanel}<div className="editor-label"><label htmlFor="claim-text">{comparePolicies ? 'Advertised promise' : 'Text to verify'}</label>{mode === 'live' && <button type="button" className="text-button" onClick={clearForm}>Clear form</button>}{mode === 'demo' && <button type="button" className="text-button example-button" onClick={() => setText(DEMO_TEXT)}><Sparkles size={13} />Use synthetic example</button>}</div><textarea id="claim-text" className={comparePolicies ? 'promise-editor' : undefined} value={text} onChange={event => setText(event.target.value)} placeholder={comparePolicies ? 'Paste the exact advertised subscription promise.' : 'Paste an AI-generated answer, a paragraph, or a factual claim.'} maxLength={8000} required aria-describedby="text-help" /><div className="editor-footer"><span id="text-help"><FileText size={13} />Original wording stays intact.</span><span>{text.length.toLocaleString()} / 8,000</span></div>
      {mode === 'live' && !guardian && !officialPolicy && <div className="policy-input"><label className="policy-toggle"><input type="checkbox" checked={comparePolicies} onChange={event => setComparePolicies(event.target.checked)} /> Compare this advertised promise with supplied policy documents</label>{comparePolicies && <><p className="muted">Pasted policy text stays separate from the promise. Provide up to two versioned documents.</p>{documents.map((document, index) => <fieldset className="policy-document" key={index}><legend>Policy document {index + 1}</legend><div className="policy-meta"><label>Document ID<input value={document.document_id} maxLength={120} onChange={event => updateDocument(index, 'document_id', event.target.value)} /></label><label>Title<input value={document.title} maxLength={200} onChange={event => updateDocument(index, 'title', event.target.value)} /></label><label>Version<input value={document.version ?? ''} maxLength={80} onChange={event => updateDocument(index, 'version', event.target.value)} /></label><label>Effective date<input value={document.effective_date ?? ''} maxLength={80} onChange={event => updateDocument(index, 'effective_date', event.target.value)} /></label></div><label>Exact policy text<textarea value={document.text} maxLength={12000} onChange={event => updateDocument(index, 'text', event.target.value)} /></label></fieldset>)}</>}</div>}
      {mode === 'demo' && <div className="scenario-field"><label htmlFor="scenario">Synthetic scenario</label><select id="scenario" value={scenario} onChange={event => setScenario(event.target.value as Scenario)}><option value="review">Mixed findings · pending review</option><option value="pass">Supported · release permitted</option><option value="disputed">Disputed · hold for review</option><option value="insufficient">Insufficient evidence · hold</option><option value="annotate">Supported with caveats · annotate</option><option value="failed">Verification failed</option><option value="interrupted">Verification interrupted</option><option value="provider_unavailable">Provider unavailable</option></select></div>}
      {error && <ErrorPanel message={error} />}<div className="submit-row"><p>{mode === 'demo' ? 'A local simulation. Your text is never sent for verification.' : 'Submitted to your local FastAPI backend for verification.'}</p><button type="submit" className="button primary" disabled={!text.trim() || busy}>{busy ? <LoaderCircle size={16} className="spin" /> : <ScanText size={17} />}{busy ? 'Opening check…' : officialPolicy ? (policyText.trim() ? 'Scan pasted policy' : 'Scan official policy') : comparePolicies ? 'Compare documents' : 'Verify claims'}{!busy && <ArrowRight size={17} />}</button></div></form></section>
      <aside className="process-panel"><div className="eyebrow">HOW IT WORKS</div><h2>{mode === 'live' && !guardian ? <>Claims checked<br />against the source.</> : <>Every finding<br />has a source.</>}</h2><p className="process-intro">{mode === 'live' && !guardian ? 'We compare your claim with cited policy passages and show what each analyst found.' : 'An answer is a starting point. Evidence is what moves it forward.'}</p><ol className="process-steps">{(mode === 'live' && !guardian ? [['Claim', 'Keep the submitted wording intact.'], ['Evidence', 'Compare exact policy passages and exceptions.'], ['Review', 'Record a human decision with rationale.'], ['Outcome', 'Guardian obeys the backend release action.']] : [['Separate the claims', 'Turn a passage into statements that can be examined.'], ['Follow the evidence', 'Read supporting and challenging records, with their limits.'], ['Keep a human in the loop', 'Route unresolved claims to review before release.']]).map(([heading, description], index) => <li key={heading}><span>{index + 1}</span><div><strong>{heading}</strong><p>{description}</p></div></li>)}</ol><div className="process-footnote"><ShieldCheck size={17} /><span>Provisional findings are always labeled.</span></div></aside></div>
    <div className="docket-heading"><div><div className="eyebrow">YOUR WORKSPACE</div><h2>Recent checks <span className="count-pill">{recent.length}</span></h2></div><span className="muted">{mode === 'demo' ? 'Saved in this browser' : 'Submitted from this browser'}</span></div>
    {recent.length ? <div className="docket-list">{recent.slice(0, 6).map(item => <Link className="docket-row" to={`/${guardian ? 'guardian' : 'jobs'}/${encodeURIComponent(item.id)}`} key={item.id}><div className="docket-icon"><FileText size={19} /></div><div><span className="mono">{shortId(item.id)}</span><h3>{item.text}</h3></div><time>{formatDate(item.created)}</time><ArrowUpRight size={18} /></Link>)}</div> : <div className="docket-empty"><div className="docket-empty-icon"><CornerDownLeft size={22} /></div><div><h3>Your first check starts here.</h3><p>Submit a passage above to see the evidence trail.</p></div><span className="empty-docket-lines"><Check size={18} /><span /></span></div>}
    <div className="court-bottom-note"><span className="asterisk">✳</span><p>Supported is a finding.<br /><strong>Trust is a process.</strong></p><Link to="/about">How this workspace works <ArrowUpRight size={15} /></Link></div>
  </div>;
}
