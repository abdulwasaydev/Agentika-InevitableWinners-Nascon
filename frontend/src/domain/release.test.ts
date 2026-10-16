import { describe, expect, it } from 'vitest';
import { getRelease, isTerminal, safeSourceUrl } from './release';
import type { Job } from '../api/types';

const job: Job = { job_id: 'j1', status: 'completed', submitted_text: '<script>draft</script>', overall_action: 'hold_for_review', claim_ids: [], created_at: '', limitations: [], reason_codes: [] };

describe('Guardian release boundary', () => {
  it('withholds held text, even after a successful review has been recorded elsewhere', () => {
    expect(getRelease(job, []).output).toBeNull();
    expect(getRelease(job, []).kind).toBe('held');
  });
  it('releases only a completed job explicitly marked pass', () => {
    expect(getRelease({ ...job, overall_action: 'pass' }, [])).toEqual({ kind: 'released', output: '<script>draft</script>' });
    expect(getRelease({ ...job, status: 'processing', overall_action: 'pass' }, []).output).toBeNull();
    expect(getRelease({ ...job, status: 'review_pending', overall_action: 'pass' }, []).output).toBeNull();
  });
  it('blocks stale approval when the latest request fails or the job is unavailable', () => {
    expect(getRelease({ ...job, overall_action: 'pass' }, [], 'Network unavailable').output).toBeNull();
    expect(getRelease({ ...job, status: 'provider_unavailable', overall_action: 'pass' }, []).output).toBeNull();
    expect(getRelease(null, []).output).toBeNull();
  });
  it('requires hydrated claim caveats before annotated output is available', () => {
    expect(getRelease({ ...job, overall_action: 'annotate', claim_ids: ['missing'] }, []).output).toBeNull();
    expect(getRelease({ ...job, overall_action: 'annotate' }, []).kind).toBe('annotated');
  });
  it('preserves original wording unless the backend explicitly supplies revised output', () => {
    expect(getRelease({ ...job, overall_action: 'pass', revised_output: 'Server revision' }, []).output).toBe('Server revision');
  });
});

it('stops polling for all terminal states including review pending and provider failure', () => {
  for (const state of ['completed', 'review_pending', 'failed', 'interrupted', 'provider_unavailable']) expect(isTerminal(state)).toBe(true);
  expect(isTerminal('processing')).toBe(false);
  expect(isTerminal('queued')).toBe(false);
});

it('only permits absolute HTTP(S) evidence links', () => {
  expect(safeSourceUrl('https://example.org/evidence')).toBe('https://example.org/evidence');
  for (const url of ['javascript:alert(1)', 'data:text/html,test', '/relative', 'file:///secret']) expect(safeSourceUrl(url)).toBeNull();
});
