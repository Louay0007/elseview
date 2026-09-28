import { useEffect, useState } from "react";
import { useAuthLocale } from "@/components/auth/AuthLocale";
import { BackToHome, WorkspaceShell, useWorkspaceNav } from "@/components/workspace/WorkspaceShell";
import { apiFetch, backendAvailable, newIdempotencyKey } from "@/lib/api";
import { useWorkspace } from "@/components/workspace/WorkspaceContext";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
type Case = { session_id: string; state?: string; id?: string };
export default function Reviews() {
  const { text } = useAuthLocale(); const nav = useWorkspaceNav(); const { workspaceId } = useWorkspace();
  const [studyId, setStudyId] = useState(""); const [items, setItems] = useState<Case[]>([]);
  const [err, setErr] = useState<string|null>(null); const [msg, setMsg] = useState<string|null>(null);
  const [rationale, setRationale] = useState("");
  const load = async () => { if (!backendAvailable() || !workspaceId || !studyId) return;
    try { const r = await apiFetch<{ items: Case[] }>(`/workspaces/${workspaceId}/reviews/studies/${studyId}/cases`); setItems(r.items); }
    catch { setErr(text({ en: "No replies to check.", fr: "File impossible à charger." })); } };
  useEffect(() => { void load(); }, [workspaceId, studyId]);
  const decide = async (sessionId: string, verdict: "accepted"|"rejected") => { setErr(null); setMsg(null);
    try {
      const me = await apiFetch<{ id: string }>(`/auth/me`, {});
      const asg = await apiFetch<{ id: string }>(`/workspaces/${workspaceId}/reviews/sessions/${sessionId}/assignments`, { method: "POST", idempotencyKey: newIdempotencyKey(), body: { reviewer_id: (me as { id: string }).id, kind: "independent" } });
      await apiFetch(`/workspaces/${workspaceId}/reviews/assignments/${asg.id}/decision`, { method: "POST", idempotencyKey: newIdempotencyKey(), body: { command_key: newIdempotencyKey(), verdict, rationale: rationale || "Checked by hand.", evidence: [] } });
      setMsg(text({ en: "Choice saved.", fr: "Choix enregistré." })); } catch { setErr(text({ en: "Save failed. Try again.", fr: "Échec. Réessayez." })); } };
  return (
    <WorkspaceShell workspaceName={nav.workspaceName} displayName={nav.displayName} firstName={nav.firstName} role={nav.role} onSettings={() => nav.goWithParams("/settings")} onBilling={() => nav.goWithParams("/workspace/billing")} onCredits={() => nav.goWithParams("/workspace/credits")} onAccount={() => nav.goWithParams("/account")} onNotifications={() => nav.goWithParams("/account/notifications")} onRefer={() => nav.goWithParams("/account/refer")}>
      <BackToHome />
      <p className="mt-6 text-[13px] font-medium uppercase tracking-[0.08em] text-[#6d6d70]">{text({ en: "Check replies", fr: "Vérifier" })}</p>
      <h1 className="mt-1 text-[30px] font-bold text-black">{text({ en: "Say yes or no to each reply.", fr: "Acceptez ou refusez chaque réponse." })}</h1>
      <p className="mt-3 max-w-[72ch] text-[16px] text-[#6d6d70]">{text({ en: "People check. Appeals get a second look.", fr: "Deux personnes vérifient. Les appels sont revus." })}</p>
      {err && <p role="alert" className="mt-4 rounded-lg bg-[#fff2ef] px-4 py-3 text-sm text-[#9c2d20]">{err}</p>}
      {msg && <p role="status" className="mt-4 rounded-lg bg-[#eef6ee] px-4 py-3 text-sm text-[#1d5c1d]">{msg}</p>}
      <Card className="mt-6 rounded-[22px]"><CardHeader><CardTitle>{text({ en: "Queue", fr: "File d’attente" })}</CardTitle>
        <CardDescription>{text({ en: "Pick a study, then decide.", fr: "Collez un identifiant d’étude." })}</CardDescription></CardHeader>
        <CardContent><div className="flex flex-wrap gap-2">
          <input value={studyId} onChange={(e) => setStudyId(e.target.value)} placeholder="Study id" className="min-h-[44px] rounded-lg border border-[#e4e4e7] px-3 text-sm" />
          <input value={rationale} onChange={(e) => setRationale(e.target.value)} placeholder={text({ en: "Why?", fr: "Pourquoi ? (une phrase)" })} className="min-h-[44px] min-w-[220px] flex-1 rounded-lg border border-[#e4e4e7] px-3 text-sm" />
        </div>
        <ul className="mt-4 grid gap-2">{items.map((c) => (
          <li key={c.session_id} className="flex flex-wrap items-center gap-2 rounded-xl border border-[#e4e4e7] p-3">
            <span className="text-sm font-medium">{c.session_id.slice(0, 8)}</span><Badge variant="secondary">{c.state ?? "pending"}</Badge><span className="flex-1" />
            <button type="button" onClick={() => void decide(c.session_id, "accepted")} className="rounded-full bg-[#18181b] px-4 py-2 text-xs text-white">{text({ en: "Accept", fr: "Accepter" })}</button>
            <button type="button" onClick={() => void decide(c.session_id, "rejected")} className="rounded-full border border-[#e4e4e7] px-4 py-2 text-xs">{text({ en: "Reject", fr: "Refuser" })}</button>
          </li>))}
        </ul>{items.length === 0 && <p className="mt-4 text-sm text-[#6d6d70]">{text({ en: "Nothing to check yet.", fr: "Rien à vérifier." })}</p>}</CardContent></Card>
    </WorkspaceShell>);
}
