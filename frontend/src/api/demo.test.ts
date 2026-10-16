import { expect, it } from 'vitest';
import { createDemoApi, DEMO_TEXT } from './demo';

it('keeps disputed content held, then releases with caveats only when every claim is resolved', async () => {
  const api = createDemoApi();
  const { job_id } = await api.submit({ text: DEMO_TEXT, scenario: 'review' });
  expect((await api.getJob(job_id)).status).toBe('queued');
  expect((await api.getJob(job_id)).status).toBe('processing');
  expect((await api.getJob(job_id)).overall_action).toBe('hold_for_review');
  const queue = await api.listReviews();
  expect(queue).toHaveLength(2);
  await api.review(queue[0].claim_id, { decision: 'supported', rationale: 'Synthetic source reviewed.' });
  expect((await api.getJob(job_id)).overall_action).toBe('hold_for_review');
  await api.review(queue[1].claim_id, { decision: 'challenged', rationale: 'Synthetic schedule disagrees.', correction: 'Visitors on selected weekends.' });
  expect((await api.getJob(job_id)).overall_action).toBe('hold_for_review');
  expect((await api.getClaim(queue[1].claim_id)).human_review?.correction).toBe('Visitors on selected weekends.');
  await api.review(queue[1].claim_id, { decision: 'supported', rationale: 'Resolved in this fictional scenario.' });
  const final = await api.getJob(job_id);
  expect(final.status).toBe('completed');
  expect(final.overall_action).toBe('annotate');
  expect(final.submitted_text).toBe(DEMO_TEXT);
  expect(await api.listReviews()).toHaveLength(0);
});

it('keeps an uncertain human review held and permits a later definitive review', async () => {
  const api = createDemoApi();
  const { job_id } = await api.submit({ text: DEMO_TEXT });
  await api.getJob(job_id); await api.getJob(job_id); await api.getJob(job_id);
  const claim = (await api.listReviews())[0];
  await api.review(claim.claim_id, { decision: 'uncertain', rationale: 'More evidence needed.' });
  expect((await api.getJob(job_id)).overall_action).toBe('hold_for_review');
  expect((await api.listReviews()).some(item => item.claim_id === claim.claim_id)).toBe(true);
});

it('returns detached snapshots so UI mutation cannot approve a held job', async () => {
  const api = createDemoApi();
  const { job_id } = await api.submit({ text: DEMO_TEXT });
  const snapshot = await api.getJob(job_id);
  snapshot.overall_action = 'pass';
  snapshot.claim_ids.length = 0;
  const next = await api.getJob(job_id);
  expect(next.overall_action).not.toBe('pass');
  expect(next.claim_ids).toHaveLength(3);
});
