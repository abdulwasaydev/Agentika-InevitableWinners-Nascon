import { act, renderHook } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { useJob } from './useJob';
import { getRelease } from '../domain/release';
import type { Job, VeritasApi } from '../api/types';
const job: Job = { job_id: 'j', status: 'completed', overall_action: 'pass', submitted_text: 'A draft', claim_ids: [], created_at: '', limitations: [], reason_codes: [] };
const fakeApi = (getJob: VeritasApi['getJob']): VeritasApi => ({ getJob, getClaim: vi.fn(), listReviews: vi.fn(), review: vi.fn(), submit: vi.fn() });
afterEach(() => vi.useRealTimers());

it('polls sequentially and stops at the terminal state', async () => {
  vi.useFakeTimers();
  const getJob = vi.fn().mockResolvedValueOnce({ ...job, status: 'processing', overall_action: null }).mockResolvedValue(job);
  const api = fakeApi(getJob);
  const { result } = renderHook(() => useJob(api, 'j', 50));
  await act(async () => {});
  expect(result.current.job?.status).toBe('processing');
  await act(async () => { await vi.advanceTimersByTimeAsync(50); });
  expect(result.current.job?.status).toBe('completed');
  await act(async () => { await vi.advanceTimersByTimeAsync(500); });
  expect(getJob).toHaveBeenCalledTimes(2);
});

it('aborts in-flight polling on navigation and ignores a stale response', async () => {
  let resolveOld!: (value: Job) => void;
  let oldSignal: AbortSignal | undefined;
  const api = fakeApi(vi.fn((id: string, signal?: AbortSignal) => id === 'old' ? (oldSignal = signal, new Promise<Job>(resolve => { resolveOld = resolve; })) : Promise.resolve({ ...job, job_id: 'new' })));
  const { result, rerender, unmount } = renderHook(({ id }) => useJob(api, id), { initialProps: { id: 'old' } });
  await act(async () => {});
  rerender({ id: 'new' });
  await act(async () => {});
  expect(oldSignal?.aborted).toBe(true);
  await act(async () => { resolveOld({ ...job, job_id: 'old' }); });
  expect(result.current.job?.job_id).toBe('new');
  unmount();
});

it('invalidates a previously released snapshot before refetching and keeps it unavailable on failure', async () => {
  const api = fakeApi(vi.fn().mockResolvedValueOnce(job).mockRejectedValueOnce(new Error('Backend unavailable')));
  const { result } = renderHook(() => useJob(api, 'j'));
  await act(async () => {});
  expect(getRelease(result.current.job, result.current.claims).kind).toBe('released');
  await act(async () => { result.current.refresh(); });
  expect(result.current.job).toBeNull();
  expect(getRelease(result.current.job, [], result.current.error).output).toBeNull();
  expect(result.current.error).toBe('Backend unavailable');
});
