import { createContext, useContext, useMemo, useState, type ReactNode } from 'react';
import { createLiveApi } from './api/client';
import { createDemoApi } from './api/demo';
import type { Mode, VeritasApi } from './api/types';

interface RecentCase { id: string; text: string; created: string }
interface Workspace {
  mode: Mode; api: VeritasApi; recent: RecentCase[]; version: number;
  changeMode: (mode: Mode) => void; remember: (id: string, text: string) => void; resetDemo: () => void;
}
const Context = createContext<Workspace | null>(null);
function loadRecent(mode: Mode): RecentCase[] {
  try {
    const stored: unknown = JSON.parse(localStorage.getItem(`veritas.recent.${mode}`) ?? '[]');
    return Array.isArray(stored) ? stored.filter((item): item is RecentCase => item && typeof item.id === 'string' && typeof item.text === 'string' && typeof item.created === 'string').slice(0, 20) : [];
  } catch { return []; }
}
export function WorkspaceProvider({ children, initialMode, liveApi }: { children: ReactNode; initialMode?: Mode; liveApi?: VeritasApi }) {
  const [mode, setMode] = useState<Mode>(initialMode ?? (import.meta.env.VITE_API_MODE === 'demo' ? 'demo' : 'live'));
  const [recent, setRecent] = useState(() => loadRecent(mode));
  const [version, setVersion] = useState(0);
  const live = useMemo(() => liveApi ?? createLiveApi(), [liveApi]);
  const demo = useMemo(() => createDemoApi(typeof localStorage === 'undefined' ? undefined : localStorage), []);
  function persist(next: RecentCase[], target: Mode) { try { localStorage.setItem(`veritas.recent.${target}`, JSON.stringify(next)); } catch { /* Browser storage is optional. */ } }
  const value: Workspace = {
    mode, api: mode === 'demo' ? demo : live, recent, version,
    changeMode(next) { setMode(next); setRecent(loadRecent(next)); setVersion(v => v + 1); },
    remember(id, text) { setRecent(current => { const next = [{ id, text, created: new Date().toISOString() }, ...current.filter(c => c.id !== id)].slice(0, 20); persist(next, mode); return next; }); },
    resetDemo() { demo.reset(); setRecent([]); persist([], 'demo'); setVersion(v => v + 1); },
  };
  return <Context.Provider value={value}>{children}</Context.Provider>;
}
export function useWorkspace() { const context = useContext(Context); if (!context) throw new Error('WorkspaceProvider is required'); return context; }
