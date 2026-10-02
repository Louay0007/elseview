import { useState } from "react";
import { useAuthLocale } from "@/components/auth/AuthLocale";
import { TesterShell } from "@/components/tester/TesterShell";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { mockRunnerSteps } from "./testerMocks";
export default function TesterRunner() {
  const { text } = useAuthLocale(); const [sessionId, setSessionId] = useState(""); const [answer, setAnswer] = useState("");
  const [msg, setMsg] = useState<string|null>(null);
  const [step, setStep] = useState(0); const [consent, setConsent] = useState(false);
  const current = mockRunnerSteps[Math.min(step, mockRunnerSteps.length - 1)];
  const act = (ok: string) => setMsg(ok);
  return (<TesterShell>
    <h1 className="text-[28px] font-bold text-black">{text({ en: "Answer the study.", fr: "Répondez à l’étude." })}</h1>
    <p className="mt-2 text-[16px] text-[#6d6d70]">{text({ en: "Read, answer, send.", fr: "Lisez, répondez, envoyez. Partez quand vous voulez." })}</p>
    {!consent ? (<Card className="mt-6 rounded-[18px]"><CardHeader><CardTitle>{text({ en: "Before you start", fr: "Avant de commencer" })}</CardTitle>
      <CardDescription>{text({ en: "Private answers. Leave anytime.", fr: "Vos réponses restent privées. Partez quand vous voulez." })}</CardDescription></CardHeader>
      <CardContent><button type="button" onClick={() => setConsent(true)} className="rounded-full bg-[#18181b] px-5 py-2.5 text-sm text-white">{text({ en: "I agree — start", fr: "D’accord — commencer" })}</button></CardContent></Card>)
    : (<Card className="mt-6 rounded-[18px]"><CardHeader><CardTitle>{current.title}</CardTitle><CardDescription>{`Step ${step + 1} of ${mockRunnerSteps.length}`}</CardDescription></CardHeader>
      <CardContent><p className="text-[16px]">{current.body}</p>
        <div className="mt-3 flex flex-wrap gap-2">
          {step > 0 && <button type="button" onClick={() => setStep(step - 1)} className="rounded-full border border-[#e4e4e7] px-5 py-2.5 text-sm">{text({ en: "Back", fr: "Retour" })}</button>}
          {step < mockRunnerSteps.length - 1
            ? <button type="button" onClick={() => setStep(step + 1)} className="rounded-full bg-[#18181b] px-5 py-2.5 text-sm text-white">{text({ en: "Next", fr: "Suivant" })}</button>
            : <span className="text-sm text-[#1d5c1d]">{text({ en: "Done — now send below.", fr: "Fini — envoyez ci-dessous." })}</span>}
        </div></CardContent></Card>)}
    {msg && <p role="status" className="mt-4 rounded-lg bg-[#eef6ee] px-4 py-3 text-sm text-[#1d5c1d]">{msg}</p>}
    <Card className="mt-6 rounded-[18px]"><CardHeader><CardTitle>{text({ en: "Your answer", fr: "Votre réponse" })}</CardTitle>
      <CardDescription>{text({ en: "Paste the session id.", fr: "Collez l’identifiant depuis Mes séances." })}</CardDescription></CardHeader>
      <CardContent><div className="grid gap-2">
        <input value={sessionId} onChange={(e) => setSessionId(e.target.value)} placeholder="session id" className="min-h-[44px] rounded-lg border border-[#e4e4e7] px-3 text-sm" />
        <textarea value={answer} onChange={(e) => setAnswer(e.target.value)} rows={4} placeholder={text({ en: "Your answer…", fr: "Écrivez votre réponse…" })} className="rounded-lg border border-[#e4e4e7] px-3 py-2 text-sm" />
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={() => act(text({ en: "Saved.", fr: "Enregistré." }))} className="rounded-full border border-[#e4e4e7] px-5 py-2.5 text-sm">{text({ en: "Save", fr: "Enregistrer" })}</button>
          <button type="button" onClick={() => act(text({ en: "Sent. Thanks.", fr: "Envoyé. Merci." }))} className="rounded-full bg-[#18181b] px-5 py-2.5 text-sm text-white">{text({ en: "Send", fr: "Envoyer" })}</button>
          <button type="button" onClick={() => act(text({ en: "Withdrawn.", fr: "Retiré." }))} className="rounded-full border border-[#e4e4e7] px-5 py-2.5 text-sm">{text({ en: "Leave", fr: "Partir" })}</button>
        </div></div></CardContent></Card>
  </TesterShell>);
}
