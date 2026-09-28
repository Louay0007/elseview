import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { apiFetch, backendAvailable } from "@/lib/api";

type WorkspaceSummary = { id: string; name: string };
type WorkspaceContextValue = {
  workspaceId: string | null;
  workspaces: WorkspaceSummary[];
  loading: boolean;
  selectWorkspace: (id: string) => void;
  refresh: () => void;
};

const WorkspaceContext = createContext<WorkspaceContextValue>({
  workspaceId: null,
  workspaces: [],
  loading: false,
  selectWorkspace: () => {},
  refresh: () => {},
});

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [workspaces, setWorkspaces] = useState<WorkspaceSummary[]>([]);
  const [workspaceId, setWorkspaceId] = useState<string | null>(() =>
    new URLSearchParams(window.location.search).get("workspaceId"),
  );
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(() => {
    if (!backendAvailable()) return;
    setLoading(true);
    apiFetch<{ items: WorkspaceSummary[] }>("/workspaces")
      .then((result) => {
        setWorkspaces(result.items ?? []);
        setWorkspaceId((current) => current ?? result.items?.[0]?.id ?? null);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const value = useMemo(
    () => ({
      workspaceId,
      workspaces,
      loading,
      selectWorkspace: setWorkspaceId,
      refresh,
    }),
    [workspaceId, workspaces, loading, refresh],
  );
  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace() {
  return useContext(WorkspaceContext);
}
