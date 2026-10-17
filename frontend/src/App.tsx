import { useState } from 'react';
import { Link, NavLink, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { ArrowUpRight, BookOpen, FlaskConical, GitBranch, HelpCircle, RotateCcw, ShieldCheck, X, ClipboardCheck } from 'lucide-react';
import { useWorkspace } from './Workspace';
import { CourtPage } from './pages/CourtPage';
import { CasePage, ClaimPage } from './pages/CasePages';
import { QueuePage, ReviewPage } from './pages/ReviewPages';
import { GuardianPage } from './pages/GuardianPage';
import { DocumentPage, LineagePage, AboutPage } from './pages/SupportingPages';

const navigation = [
  { to: '/', label: 'Policy Check', icon: BookOpen, end: true },
  { to: '/reviews', label: 'Reviews', icon: ClipboardCheck },
  { to: '/guardian', label: 'Release Gate', icon: ShieldCheck },
  { to: '/lineage', label: 'Source Trail', icon: GitBranch },
];
export function AppRoutes() {
  const { mode, changeMode, resetDemo, version } = useWorkspace();
  const [confirmReset, setConfirmReset] = useState(false);
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const section = pathname.startsWith('/reviews') ? 'Reviews' : pathname.startsWith('/guardian') ? 'Release Gate' : pathname.startsWith('/lineage') ? 'Source Trail' : pathname.startsWith('/documents') ? 'Source library' : pathname === '/about' ? 'Workspace guide' : 'Policy Check';
  return <div className="app-shell">
    <a className="skip-link" href="#main-content">Skip to content</a>
    <aside className="sidebar">
      <Link to="/" className="brand" aria-label="Veritas home"><span className="brand-mark">V<span /></span><span>veritas<span className="brand-subtitle">EVIDENCE BEFORE CONFIDENCE</span></span></Link>
      <div className="workspace-label"><span className="status-dot" />TEAM WORKSPACE <span className="workspace-code">01</span></div>
      <div className="nav-caption">WORKBENCH</div>
      <nav aria-label="Main navigation">{navigation.map(({ to, label, icon: Icon, end }) => <NavLink key={to} to={to} end={end} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}><Icon size={19} aria-hidden="true" /><span>{label}</span>{to === '/' && <span className="nav-index">01</span>}</NavLink>)}</nav>
      <div className="sidebar-bottom"><div className="principle-card"><BookOpen size={20} /><p>Confidence is earned.<br /><em>Evidence comes first.</em></p><span>Machine findings. Human judgment.</span></div><Link className="guide-link" to="/about"><HelpCircle size={17} /> Workspace guide <ArrowUpRight size={14} /></Link><div className="profile"><span className="avatar">AW</span><div>Abdul Wasay<small>Frontend workspace</small></div><span className="profile-dot" /></div></div>
    </aside>
    <div className="workspace-main"><header className="topbar"><div className="breadcrumb"><span>Workspace</span><span>/</span><strong>{section}</strong></div><div className="topbar-right"><span className="local-label"><span className="status-dot" />Local MVP</span><label className="mode-select"><FlaskConical size={15} /><span className="sr-only">API mode</span><select aria-label="API mode" value={mode} onChange={event => { changeMode(event.target.value as 'live' | 'demo'); navigate('/'); }}><option value="demo">Synthetic demo</option><option value="live">Live API</option></select></label></div></header>
      {mode === 'demo' ? <div className="mode-banner"><div><FlaskConical size={15} /><strong>Demo mode — simulated verification</strong><span>Fictional documents. No real-world fact checking.</span></div><button className="text-button" onClick={() => setConfirmReset(true)}><RotateCcw size={13} />Reset demo</button></div> : <div className="mode-banner live"><div><span className="status-dot" /><strong>Live API mode</strong><span>Results and release decisions require a backend response.</span></div></div>}
      <main id="main-content" key={`${mode}-${version}`}><Routes>
        <Route path="/" element={<CourtPage />} /><Route path="/jobs/:jobId" element={<CasePage />} /><Route path="/claims/:claimId" element={<ClaimPage />} /><Route path="/reviews" element={<QueuePage />} /><Route path="/reviews/:claimId" element={<ReviewPage />} /><Route path="/guardian" element={<GuardianPage />} /><Route path="/guardian/:jobId" element={<GuardianPage />} /><Route path="/lineage" element={<LineagePage />} /><Route path="/lineage/:jobId" element={<LineagePage />} /><Route path="/documents/:documentId" element={<DocumentPage />} /><Route path="/about" element={<AboutPage />} /><Route path="*" element={<div className="empty-state"><h1>Page not found</h1><p>This page is not part of the workspace.</p><Link to="/">Return to Policy Check</Link></div>} />
      </Routes></main>
      <footer className="workspace-footer"><span>VERITAS <span className="footer-divider">/</span> Built for careful judgment.</span><span>{mode === 'demo' ? 'SYNTHETIC WORKSPACE' : 'LIVE API WORKSPACE'} <span className="status-dot" /></span></footer>
    </div>
    {confirmReset && <div className="modal-backdrop"><section role="dialog" aria-modal="true" aria-labelledby="reset-title" className="modal"><button className="icon-button modal-close" aria-label="Cancel reset" onClick={() => setConfirmReset(false)} autoFocus><X size={20} /></button><RotateCcw size={26} /><h2 id="reset-title">Clear synthetic examples?</h2><p>This removes this browser’s synthetic cases and reviews. Live backend records are unaffected.</p><div className="button-row"><button className="button secondary" onClick={() => setConfirmReset(false)}>Keep cases</button><button className="button primary" onClick={() => { resetDemo(); setConfirmReset(false); navigate('/'); }}>Reset demo data</button></div></section></div>}
  </div>;
}
