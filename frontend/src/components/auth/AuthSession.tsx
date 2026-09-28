/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

type SessionStatus = "restoring" | "authenticated" | "anonymous";
type AuthSessionValue = { status: SessionStatus; completeSession: () => void; endSession: () => void };

const AuthSessionContext = createContext<AuthSessionValue | null>(null);
const previewSessionKey = "mediterra-auth-ui-session";

export function AuthSessionProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<SessionStatus>("restoring");

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => {
      setStatus(window.sessionStorage.getItem(previewSessionKey) === "active" ? "authenticated" : "anonymous");
    });
    return () => window.cancelAnimationFrame(frame);
  }, []);

  const value = useMemo<AuthSessionValue>(() => ({
    status,
    completeSession: () => { window.sessionStorage.setItem(previewSessionKey, "active"); setStatus("authenticated"); },
    endSession: () => { window.sessionStorage.removeItem(previewSessionKey); setStatus("anonymous"); },
  }), [status]);

  return <AuthSessionContext.Provider value={value}>{children}</AuthSessionContext.Provider>;
}

export function useAuthSession() {
  const context = useContext(AuthSessionContext);
  if (!context) throw new Error("useAuthSession must be used inside AuthSessionProvider");
  return context;
}
