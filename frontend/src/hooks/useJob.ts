import type { VeritasApi, Job, Claim } from '../api/types';
import { useCallback, useEffect, useState } from 'react';
import { isTerminal } from '../domain/release';
type Snapshot = { id: string; api: VeritasApi; revision: number; job: Job | null; claims: Claim[]; loading: boolean; error: string | null };
export function useJob(api: VeritasApi, id: string, interval = 1000) {
  const [revision, setRevision] = useState(0);
  const [state, setState] = useState<Snapshot | null>(null);
  const refresh = useCallback(() => { setState(null); setRevision(value => value + 1); }, []);
  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    setState(null);
    async function poll() {
      try {
        const job = await api.getJob(id, controller.signal);
        if (job.job_id !== id) throw new Error('API contract mismatch: returned case does not match the requested case.');
        const claims = isTerminal(job.status) ? await Promise.all(job.claim_ids.map(claimId => api.getClaim(claimId, controller.signal))) : [];
        if (claims.some((claim, index) => claim.job_id !== id || claim.claim_id !== job.claim_ids[index])) throw new Error('API contract mismatch: claim ownership does not match this case.');
        if (!active) return;
        setState({ id, api, revision, job, claims, loading: false, error: null });
        if (!isTerminal(job.status)) timer = setTimeout(poll, interval);
      } catch (error) {
        if (!active || controller.signal.aborted) return;
        setState({ id, api, revision, job: null, claims: [], loading: false, error: error instanceof Error ? error.message : 'The case could not be loaded.' });
      }
    }
    void poll();
    return () => { active = false; controller.abort(); clearTimeout(timer); };
  }, [api, id, revision, interval]);
  const current = state?.id === id && state.api === api && state.revision === revision ? state : null;
  return { job: current?.job ?? null, claims: current?.claims ?? [], loading: current?.loading ?? true, error: current?.error ?? null, refresh };
}
