import { useEffect, useState } from 'react';
export function useResource<T>(load: (signal: AbortSignal) => Promise<T>) {
  const [state, setState] = useState<{ data: T | null; error: string | null; loading: boolean }>({ data: null, error: null, loading: true });
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const controller = new AbortController(); let active = true;
    setState({ data: null, error: null, loading: true });
    load(controller.signal).then(data => { if (active) setState({ data, error: null, loading: false }); }).catch(error => { if (active) setState({ data: null, error: error instanceof Error ? error.message : 'Request failed.', loading: false }); });
    return () => { active = false; controller.abort(); };
  }, [load, revision]);
  return { ...state, refresh: () => { setState({ data: null, error: null, loading: true }); setRevision(v => v + 1); } };
}
