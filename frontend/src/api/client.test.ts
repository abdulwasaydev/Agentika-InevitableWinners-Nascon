import { expect, it, vi } from 'vitest';
import { createLiveApi } from './client';

it('posts the original text to the relative verification endpoint and requires HTTP 202', async () => {
  const fetcher = vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify({ job_id: 'case-1' }), { status: 202 }));
  const api = createLiveApi(fetcher);
  expect(await api.submit({ text: '  Original wording.  ', scenario: 'pass' })).toEqual({ job_id: 'case-1' });
  const [url, init] = fetcher.mock.calls[0];
  expect(url).toBe('/api/v1/verify');
  expect(init?.method).toBe('POST');
  expect(JSON.parse(init?.body as string)).toEqual({ text: '  Original wording.  ' });
});

it('never replaces a live network failure with synthetic success', async () => {
  const api = createLiveApi(vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));
  await expect(api.submit({ text: 'A claim' })).rejects.toThrow(/unavailable/i);
});

it('fails closed on an unknown job status, missing action, or malformed response', async () => {
  const bodies = [
    { job_id: 'j', status: 'approved_by_magic', overall_action: 'pass' },
    { job_id: 'j', status: 'completed', claim_ids: [], submitted_text: 'Text' },
    { job_id: 'j', status: 'completed', overall_action: 'pass', claim_ids: [7] },
  ];
  for (const body of bodies) {
    const api = createLiveApi(vi.fn().mockResolvedValue(new Response(JSON.stringify(body))));
    await expect(api.getJob('j')).rejects.toThrow(/contract/i);
  }
});

it('uses the pending review query and sends correction separately from the original claim', async () => {
  const fetcher = vi.fn<typeof fetch>()
    .mockResolvedValueOnce(new Response(JSON.stringify({ items: [] })))
    .mockResolvedValueOnce(new Response(JSON.stringify({ review_id: 'r', claim_id: 'c/a', decision: 'challenged', rationale: 'Conflicting source', correction: 'Separate correction', created_at: '2026-10-16' })));
  const api = createLiveApi(fetcher);
  expect(await api.listReviews()).toEqual([]);
  await api.review('c/a', { decision: 'challenged', rationale: 'Conflicting source', correction: 'Separate correction' });
  expect(fetcher.mock.calls[0][0]).toBe('/api/v1/reviews?status=pending');
  expect(fetcher.mock.calls[1][0]).toBe('/api/v1/claims/c%2Fa/reviews');
  expect(JSON.parse(fetcher.mock.calls[1][1]?.body as string)).toEqual({ decision: 'challenged', rationale: 'Conflicting source', correction: 'Separate correction' });
});

it('rejects whitespace submissions and non-202 responses', async () => {
  const api = createLiveApi(vi.fn().mockResolvedValue(new Response(JSON.stringify({ job_id: 'j' }), { status: 200 })));
  await expect(api.submit({ text: '  ' })).rejects.toThrow(/text/i);
  await expect(api.submit({ text: 'Claim' })).rejects.toThrow(/202/);
});
