import { useState } from "react";
import { useParams } from "react-router-dom";
import { useAuthLocale } from "@/components/auth/AuthLocale";
import { BackToHome, WorkspaceShell, useWorkspaceNav } from "@/components/workspace/WorkspaceShell";
import { apiFetch, backendAvailable, newIdempotencyKey } from "@/lib/api";
import { useWorkspace } from "@/components/workspace/WorkspaceContext";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
export default function ReportDetail() {
  const { text } = useAuthLocale(); const nav = useWorkspaceNav(); const { reportId } = useParams(); const { workspaceId } = useWorkspace();
  const [msg, setMsg] = useState<string|null>(null); const [err, setErr] = useState<string|null>(null);
  const act = async (fn: () => Promise<unknown>, ok: string) => { setErr(null); setMsg(null);
    try { if (!backendAvailable() || !workspaceId || !reportId) throw new Error("x"); const r = await fn(); setMsg(ok); return r; } catch { setErr(text({ en: "Try again.", fr: "Impossible." })); } };
  return (
    <WorkspaceShell workspaceName={nav.workspaceName} displayName={nav.displayName} firstName={nav.firstName} role={nav.role} onSettings={() => nav.goWithParams("/settings")} onBilling={() => nav.goWithParams("/workspace/billing")} onCredits={() => nav.goWithParams("/workspace/credits")} onAccount={() => nav.goWithParams("/account")} onNotifications={() => nav.goWithParams("/account/notifications")} onRefer={() => nav.goWithParams("/account/refer")}>
      <BackToHome />
      <p className="mt-6 text-[13px] font-medium uppercase tracking-[0.08em] text-[#6d6d70]">{text({ en: "Report", fr: "Rapport" })}</p>
      <h1 className="mt-1 text-[30px] font-bold text-black">{text({ en: "Share finished results.", fr: "Partagez les résultats finis." })}</h1>
      <p className="mt-3 max-w-[72ch] text-[16px] text-[#6d6d70]">{text({ en: "Get a file or a link. Remove the link anytime.", fr: "Exportez un fichier ou créez un lien. Retirable à tout moment." })}</p>
      {err && <p role="alert" className="mt-4 rounded-lg bg-[#fff2ef] px-4 py-3 text-sm text-[#9c2d20]">{err}</p>}
      {msg && <p role="status" className="mt-4 rounded-lg bg-[#eef6ee] px-4 py-3 text-sm text-[#1d5c1d]">{msg}</p>}
      <Card className="mt-6 rounded-[22px]"><CardHeader><CardTitle>{text({ en: "Export", fr: "Exporter" })}</CardTitle>
        <CardDescription>{text({ en: "PDF or table.", fr: "PDF ou tableau. Petits groupes cachés." })}</CardDescription></CardHeader>
        <CardContent><div className="flex flex-wrap gap-2">
          {(["pdf", "csv", "xlsx", "json"] as const).map((f) => (
            <button key={f} type="button" onClick={() => void act(() => apiFetch(`/workspaces/${workspaceId}/analytics/reports/${reportId}/exports`, { method: "POST", idempotencyKey: newIdempotencyKey(), body: { format: f, scope: "summary" } }), text({ en: "Ready.", fr: "Fichier prêt." }))} className="rounded-full border border-[#e4e4e7] px-5 py-2.5 text-sm uppercase">{f}</button>))}
          <button type="button" onClick={() => void act(() => apiFetch(`/workspaces/${workspaceId}/analytics/reports/${reportId}/approve`, { method: "POST", body: {} }), text({ en: "Approved.", fr: "Approuvé." }))} className="rounded-full bg-[#18181b] px-5 py-2.5 text-sm text-white">{text({ en: "Approve", fr: "Approuver" })}</button>
        </div></CardContent></Card>
    </WorkspaceShell>);
}
