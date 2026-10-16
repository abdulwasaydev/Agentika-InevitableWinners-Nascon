import { expect, it, vi } from 'vitest';
import accepted from '../../../contracts/examples/verify-accepted.json';
import completed from '../../../contracts/examples/job-completed.json';
import { createLiveApi } from './client';
import { getRelease } from '../domain/release';

const claim = {
  ...completed.claims[0],
  evidence: [{
    id: '00000000-0000-4000-8000-000000000003', stance: 'support', source_type: 'synthetic_demo',
    provenance: 'synthetic_fixture', url: null, document_id: 'synthetic:aster-chronology',
    title: 'Synthetic Aster chronology', excerpt: 'The fictional Aster Archive opened in 2020.',
    retrieved_at: '2026-10-16T10:00:00Z', published_at: null, validity_status: 'valid',
  }],
  assessments: [{
    id: '00000000-0000-4000-8000-000000000004', role: 'support', position: 'supports',
    reasoning_summary: 'The document states the year.', evidence_ids: ['00000000-0000-4000-8000-000000000003'],
    limitations: 'Synthetic corpus only.', created_at: '2026-10-16T10:00:00Z',
  }],
  reviews: [], parent_claim_ids: [],
};
const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status });

it('submits the canonical Guardian request and requires HTTP 202', async () => {
  const fetcher = vi.fn<typeof fetch>().mockResolvedValue(json(accepted, 202));
  const api = createLiveApi(fetcher);
  expect(await api.submit({ text: '  Original wording.  ', mode: 'guardian', scenario: 'pass' })).toEqual({ job_id: accepted.job_id });
  const [url, init] = fetcher.mock.calls[0];
  expect(url).toBe('/api/v1/verify');
  expect(init?.method).toBe('POST');
  expect(JSON.parse(init?.body as string)).toEqual({
    text: '  Original wording.  ', mode: 'guardian', policy: 'strict', origin: 'agent_output',
  });
});

it('reads the canonical completed job and detailed evidence before Guardian release', async () => {
  const fetcher = vi.fn<typeof fetch>()
    .mockResolvedValueOnce(json(completed))
    .mockResolvedValueOnce(json(claim));
  const api = createLiveApi(fetcher);
  const job = await api.getJob(completed.id);
  expect(job.status).toBe('completed');
  expect(job.claim_ids).toEqual([claim.id]);
  expect(getRelease(job, []).output).toBeNull();
  const detail = await api.getClaim(claim.id);
  expect(detail.evidence[0].document_id).toBe('synthetic:aster-chronology');
  expect(detail.assessments?.[0].reasoning_summary).toBe('The document states the year.');
  expect(getRelease(job, [detail]).output).toBe(completed.input_text);
});

it('never replaces a live network or database failure with synthetic success', async () => {
  const api = createLiveApi(vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));
  await expect(api.submit({ text: 'A claim' })).rejects.toThrow(/unavailable/i);
  const unavailable = createLiveApi(vi.fn().mockResolvedValue(json({
    code: 'DATABASE_UNAVAILABLE', message: 'Configure PostgreSQL and apply the reviewed migration',
  }, 503)));
  await expect(unavailable.submit({ text: 'A claim' })).rejects.toThrow(/Configure PostgreSQL/);
});

it('fails closed on unknown statuses, missing actions, or malformed claim details', async () => {
  for (const body of [
    { ...completed, status: 'approved_by_magic' },
    { ...completed, overall_action: null },
    { ...completed, claims: [{ ...completed.claims[0], effective_status: 'magic' }] },
  ]) {
    const api = createLiveApi(vi.fn().mockResolvedValue(json(body)));
    await expect(api.getJob(completed.id)).rejects.toThrow(/contract/i);
  }
  const malformed = createLiveApi(vi.fn().mockResolvedValue(json({ ...claim, evidence: [{ title: 'Invented' }] })));
  await expect(malformed.getClaim(claim.id)).rejects.toThrow(/contract/i);
});

it('uses the canonical pending queue and review envelope; corrections stay separate', async () => {
  const response = {
    review: {
      id: 'r', claim_id: claim.id, decision: 'correct', reviewer_id: 'local-reviewer',
      rationale: 'Conflicting source', corrected_text: 'Separate correction', created_at: '2026-10-16T10:00:00Z',
    },
    claim: { ...claim, corrected_text: 'Separate correction', reviews: [] },
    overall_action: 'hold_for_review',
  };
  const fetcher = vi.fn<typeof fetch>()
    .mockResolvedValueOnce(json({ items: [completed.claims[0]] }))
    .mockResolvedValueOnce(json(response));
  const api = createLiveApi(fetcher);
  const queue = await api.listReviews();
  expect(queue[0].claim_id).toBe(claim.id);
  const review = await api.review(claim.id, { decision: 'challenged', rationale: 'Conflicting source', correction: 'Separate correction' });
  expect(review.correction).toBe('Separate correction');
  expect(fetcher.mock.calls[0][0]).toBe('/api/v1/reviews?status=pending');
  expect(fetcher.mock.calls[1][0]).toBe(`/api/v1/claims/${claim.id}/reviews`);
  expect(JSON.parse(fetcher.mock.calls[1][1]?.body as string)).toEqual({
    decision: 'correct', reviewer_id: 'local-reviewer',
    rationale: 'Conflicting source', corrected_text: 'Separate correction',
  });
});

it('rejects whitespace, oversized input, and non-202 responses', async () => {
  const api = createLiveApi(vi.fn().mockResolvedValue(json(accepted)));
  await expect(api.submit({ text: '  ' })).rejects.toThrow(/text/i);
  await expect(api.submit({ text: 'A'.repeat(8001) })).rejects.toThrow(/8,000/);
  await expect(api.submit({ text: 'Claim' })).rejects.toThrow(/202/);
});
