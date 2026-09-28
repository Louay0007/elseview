import { useState } from "react";
import { useAuthLocale } from "@/components/auth/AuthLocale";
import { BackToHome, WorkspaceShell, useWorkspaceNav } from "@/components/workspace/WorkspaceShell";
import { apiFetch, backendAvailable } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
export default function RunnerPreview() {
  const { text } = useAuthLocale(); const nav = useWorkspaceNav();
  const [token, setToken] = useState(""); const [step, setStep] = useState<{ prompt?: string; done?: boolean; page?: { slot?: string; title?: string; body?: string } | null } | null>(null);
  const load = async () => { try { if (!backendAvailable()) throw new Error("x");
    const r = await apiFetch<{ prompt?: string; done?: boolean }>("/study-preview", { method: "POST", previewToken: token, body: {} }); setStep(r); }
    catch { setStep({ prompt: text({ en: "No preview for this link.", fr: "Pas d’aperçu avec ce lien." }) }); } };
  return (
    <WorkspaceShell workspaceName={nav.workspaceName} displayName={nav.displayName} firstName={nav.firstName} role={nav.role} onSettings={() => nav.goWithParams("/settings")} onBilling={() => nav.goWithParams("/workspace/billing")} onCredits={() => nav.goWithParams("/workspace/credits")} onAccount={() => nav.goWithParams("/account")} onNotifications={() => nav.goWithParams("/account/notifications")} onRefer={() => nav.goWithParams("/account/refer")}>
      <BackToHome />
      <p className="mt-6 text-[13px] font-medium uppercase tracking-[0.08em] text-[#6d6d70]">{text({ en: "Preview", fr: "Aperçu" })}</p>
      <h1 className="mt-1 text-[30px] font-bold text-black">{text({ en: "See the tester view.", fr: "Voyez comme un testeur." })}</h1>
      <p className="mt-3 max-w-[72ch] text-[16px] text-[#6d6d70]">{text({ en: "View only. Nothing saves.", fr: "Lecture seule. Rien n’est enregistré." })}</p>
      <Card className="mt-6 rounded-[22px]"><CardHeader><CardTitle>{text({ en: "Preview", fr: "Ouvrir un aperçu" })}</CardTitle>
        <CardDescription>{text({ en: "Paste the code from the editor.", fr: "Collez le code d’aperçu." })}</CardDescription></CardHeader>
        <CardContent><div className="flex flex-wrap gap-2">
          <input aria-label={text({ en: "Preview token", fr: "Code d’aperçu" })} value={token} onChange={(e) => setToken(e.target.value)} placeholder="preview token" className="min-h-[44px] min-w-[220px] flex-1 rounded-lg border border-[#e4e4e7] px-3 text-sm" />
          <button type="button" onClick={() => void load()} className="rounded-full bg-[#18181b] px-5 py-2.5 text-sm text-white">{text({ en: "Open preview", fr: "Ouvrir l’aperçu" })}</button>
        </div>{step && <div className="mt-6 rounded-2xl bg-[#f7f9fc] p-6"><span className="text-xs font-semibold uppercase tracking-[0.1em] text-[#6d6d70]">{step.page?.slot === "thanks" ? text({ en: "Thanks", fr: "Merci" }) : step.page?.slot === "welcome" ? text({ en: "Welcome", fr: "Accueil" }) : text({ en: "Task", fr: "Tâche" })}</span><h2 className="mt-2 text-xl font-semibold text-black">{step.page?.title ?? (step.done ? text({ en: "End of preview.", fr: "Fin de l’aperçu." }) : step.prompt)}</h2>{step.page?.body && <p className="mt-3 text-sm leading-6 text-[#52525b]">{step.page.body}</p>}<p className="mt-5 text-xs text-[#6d6d70]">{text({ en: "Preview only · answers are not saved", fr: "Aperçu uniquement · les réponses ne sont pas enregistrées" })}</p></div>}</CardContent></Card>
    </WorkspaceShell>);
}
