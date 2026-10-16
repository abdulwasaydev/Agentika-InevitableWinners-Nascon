import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, expect, it, vi } from 'vitest';
import { AppRoutes } from './App';
import { WorkspaceProvider } from './Workspace';
import type { Claim, Job, VeritasApi } from './api/types';
import { DEMO_TEXT } from './api/demo';

beforeEach(() => localStorage.clear());
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
  await user.click(screen.getByLabelText('Supported'));
  await user.type(screen.getByLabelText('Rationale'), 'Reviewed the provided records.');
  await user.click(screen.getByRole('button', { name: 'Save review' }));
  await screen.findByRole('status');
  await waitFor(() => expect(api.getJob).toHaveBeenCalledTimes(2));
  await user.click(screen.getByRole('link', { name: 'Return to Guardian' }));
  expect(await screen.findByRole('heading', { name: 'Output held for review' })).toBeVisible();
  expect(within(screen.getByLabelText('Release gate')).queryByText('HELD ORIGINAL TEXT')).not.toBeInTheDocument();
});
