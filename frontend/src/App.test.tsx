import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, expect, it, vi } from 'vitest';
import { AppRoutes } from './App';
import { WorkspaceProvider } from './Workspace';
import type { Claim, Job, VeritasApi } from './api/types';
import { DEMO_TEXT } from './api/demo';

beforeEach(() => { localStorage.clear(); sessionStorage.clear(); });
function mount(path = '/', api?: VeritasApi, mode: 'live' | 'demo' = 'demo') {
  return render(<MemoryRouter initialEntries={[path]}><WorkspaceProvider initialMode={mode} liveApi={api}><AppRoutes /></WorkspaceProvider></MemoryRouter>);
}

it('creates a demo case, shows extracted claims, and links synthetic evidence documents', async () => {
  const user = userEvent.setup(); mount();
  expect(screen.getByText('Demo mode — simulated verification')).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Use synthetic example' }));
  expect(screen.getByLabelText('Text to verify')).toHaveValue(DEMO_TEXT);
  await user.click(screen.getByRole('button', { name: 'Verify claims' }));
  await screen.findByText('Verification in progress');
  await screen.findByRole('heading', { name: 'Extracted claims' }, { timeout: 6000 });
  expect(screen.getAllByText('Insufficient evidence').length).toBeGreaterThan(0);
  await user.click(screen.getByRole('link', { name: /Inspect claim 2/ }));
  expect(await screen.findByText('insufficient_independent_sources')).toBeVisible();
  await user.click(screen.getByRole('link', { name: /SYN-TECH-002/ }));
  expect(await screen.findByRole('heading', { name: 'Aster Observatory · Instrument inventory' })).toBeVisible();
}, 12000);

it('shows live failure without claiming synthetic verification', async () => {
  const user = userEvent.setup();
  const api = { submit: vi.fn().mockRejectedValue(new Error('Live API unavailable')), getJob: vi.fn(), getClaim: vi.fn(), listReviews: vi.fn(), review: vi.fn() };
  mount('/', api, 'live');
  await user.type(screen.getByLabelText('Text to verify'), 'A live claim.');
  await user.click(screen.getByRole('button', { name: 'Verify claims' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Live API unavailable');
  expect(screen.queryByText('Demo mode — simulated verification')).not.toBeInTheDocument();
  expect(screen.queryByText('Extracted claims')).not.toBeInTheDocument();
});

it('accepts manually supplied policy text without a fictional picker or a prefilled verdict', async () => {
  const user = userEvent.setup();
  const api = { submit: vi.fn().mockRejectedValue(new Error('Database unavailable')), getJob: vi.fn(), getClaim: vi.fn(), listReviews: vi.fn(), review: vi.fn() };
  mount('/', api, 'live');
  expect(screen.queryByLabelText('Try a fictional subscription case')).not.toBeInTheDocument();
  await user.click(screen.getByRole('checkbox', { name: /Compare this advertised promise/ }));
  await user.type(screen.getByLabelText('Advertised promise'), 'An account can be closed at any time.');
  await user.type(screen.getAllByLabelText('Title')[0], 'Account policy');
  await user.type(screen.getAllByLabelText('Exact policy text')[0], 'You can close your account at any time.');
  await user.click(screen.getByRole('button', { name: 'Compare documents' }));
  await waitFor(() => expect(api.submit).toHaveBeenCalled());
  const submitted = api.submit.mock.calls[0][0];
  expect(submitted.documents).toHaveLength(1);
  expect(submitted.documents[0].text).toContain('close your account');
  expect(submitted).not.toHaveProperty('comparison_result');
  expect(await screen.findByRole('alert')).toHaveTextContent('Database unavailable');
  await user.click(screen.getByRole('button', { name: 'Clear form' }));
  expect(screen.getByLabelText('Text to verify')).toHaveValue('');
  expect(api.submit).toHaveBeenCalledTimes(1);
});

it('starts without a company preset or suggested claims and keeps live errors visible', async () => {
  const user = userEvent.setup();
  const api: VeritasApi = { submit: vi.fn().mockRejectedValue(new Error('LLM not configured')), getJob: vi.fn(), getClaim: vi.fn(), listReviews: vi.fn(), review: vi.fn() };
  mount('/', api, 'live');
  expect(screen.queryByRole('checkbox', { name: /Scan GitHub/ })).not.toBeInTheDocument();
  expect(screen.queryByText('Test three claims live')).not.toBeInTheDocument();
  expect(screen.getByLabelText('Text to verify')).toHaveValue('');
  expect(screen.getByLabelText('Full privacy policy (optional)')).toHaveValue('');
  await user.type(screen.getByLabelText('Text to verify'), 'A claim to investigate.');
  await user.click(screen.getByRole('button', { name: 'Verify claims' }));
  await waitFor(() => expect(api.submit).toHaveBeenCalledWith(expect.not.objectContaining({ policy_source: 'github_privacy' }), expect.anything()));
  expect(await screen.findByRole('alert')).toHaveTextContent('LLM not configured');
});

it('submits a full pasted GitHub policy and retains it for the next claim in this session', async () => {
  const user = userEvent.setup();
  const api: VeritasApi = { submit: vi.fn().mockRejectedValue(new Error('Provider unavailable')), getJob: vi.fn(), getClaim: vi.fn(), listReviews: vi.fn(), review: vi.fn() };
  const view = mount('/', api, 'live');
  const policy = 'GitHub privacy policy text. '.repeat(500);
  fireEvent.change(screen.getByLabelText('Full privacy policy (optional)'), { target: { value: policy } });
  await user.type(screen.getByLabelText('Text to verify'), 'An account uses email addresses.');
  await user.click(screen.getByRole('button', { name: 'Scan pasted policy' }));
  await waitFor(() => expect(api.submit).toHaveBeenCalledWith(expect.objectContaining({ policy_source: 'github_privacy', policy_text: policy.trim() }), expect.anything()));
  view.unmount();
  mount('/', api, 'live');
  expect(screen.getByLabelText('Full privacy policy (optional)')).toHaveValue(policy);
});

it('shows separate in-favor and against notes with the cited policy passage', async () => {
  const detail: Claim = {
    claim_id: 'c', job_id: 'j', text: 'GitHub never uses personal data to train AI models.',
    finding: 'challenged', effective_status: 'pending_review', needs_review: true,
    explanation: 'Two agents examined the policy.', limitations: [], reason_codes: [], human_review: null,
    evidence: [{ evidence_id: 'e', title: 'GitHub Privacy Statement', url: 'https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement', excerpt: 'including training models', stance: 'challenging', source_type: 'official_privacy_policy', validity_status: 'valid' }],
    assessments: [
      { role: 'support', position: 'no_support', reasoning_summary: 'No direct support found.', evidence_ids: [] },
      { role: 'challenge', position: 'challenges', reasoning_summary: 'The policy mentions training models.', evidence_ids: ['e'] },
    ],
  };
  const api: VeritasApi = { submit: vi.fn(), getJob: vi.fn(), getClaim: vi.fn().mockResolvedValue(detail), listReviews: vi.fn(), review: vi.fn() };
  mount('/claims/c', api, 'live');
  expect(await screen.findByText('No direct support found.')).toBeVisible();
  expect(screen.getByText('The policy mentions training models.')).toBeVisible();
  expect(screen.getAllByText('including training models').length).toBeGreaterThan(0);
});

it('records review then refetches the job; a successful review alone never releases Guardian output', async () => {
  const user = userEvent.setup();
  const job: Job = { job_id: 'j', status: 'review_pending', overall_action: 'hold_for_review', submitted_text: 'HELD ORIGINAL TEXT', claim_ids: ['c'], created_at: '', limitations: [], reason_codes: ['human_review_required'] };
  const claim: Claim = { claim_id: 'c', job_id: 'j', text: 'HELD ORIGINAL TEXT', finding: 'insufficient_evidence', explanation: 'Missing evidence.', evidence: [], limitations: [], reason_codes: [], human_review: null };
  const api: VeritasApi = { submit: vi.fn(), getJob: vi.fn().mockResolvedValue(job), getClaim: vi.fn().mockResolvedValue(claim), listReviews: vi.fn().mockResolvedValue([claim]), review: vi.fn().mockResolvedValue({ review_id: 'r', claim_id: 'c', decision: 'supported', rationale: 'Reviewed' }) };
  mount('/guardian/j', api, 'live');
  expect(await screen.findByRole('heading', { name: 'Output held for review' })).toBeVisible();
  expect(within(screen.getByLabelText('Release gate')).queryByText('HELD ORIGINAL TEXT')).not.toBeInTheDocument();
  await user.click(screen.getByRole('link', { name: 'Review claim' }));
  await screen.findByRole('heading', { name: 'Record a human decision' });
  await user.click(screen.getByRole('radio', { name: /Supported/ }));
  await user.type(screen.getByLabelText(/^Rationale/), 'Reviewed the provided records.');
  await user.click(screen.getByRole('button', { name: 'Save review' }));
  await screen.findByRole('status');
  await waitFor(() => expect(api.getJob).toHaveBeenCalledTimes(2));
  await user.click(screen.getByRole('link', { name: 'Return to Guardian' }));
  expect(await screen.findByRole('heading', { name: 'Output held for review' })).toBeVisible();
  expect(within(screen.getByLabelText('Release gate')).queryByText('HELD ORIGINAL TEXT')).not.toBeInTheDocument();
});
