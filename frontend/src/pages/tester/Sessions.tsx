import { useState } from "react";
import { useAuthLocale } from "@/components/auth/AuthLocale";
import { TesterShell } from "@/components/tester/TesterShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { mockSessions } from "./testerMocks";
type S = { id: string; study_title: string; kind: string; status: string; scheduled_at: string | null };
export default function TesterSessions() {
  const { text } = useAuthLocale(); const [items, setItems] = useState<S[]>(mockSessions as S[]); const [msg, setMsg] = useState<string|null>(null);
  const cancel = (id: string) => { setItems((c) => c.filter((x) => x.id !== id)); setMsg(text({ en: "Cancelled.", fr: "Annulé." })); };
  return (<TesterShell>
    <h1 className="text-[28px] font-bold text-black">{text({ en: "My sessions.", fr: "Mes séances." })}</h1>
    <p className="mt-2 text-[16px] text-[#6d6d70]">{text({ en: "Newest first. Cancel anytime.", fr: "À venir d’abord. Annulez avant le début." })}</p>
    {msg && <p role="status" className="mt-4 rounded-lg bg-[#eef6ee] px-4 py-3 text-sm text-[#1d5c1d]">{msg}</p>}
    <div className="mt-6 grid gap-3">{items.map((s) => (
      <Card key={s.id} className="rounded-[18px]"><CardHeader><CardTitle className="text-[16px]">{s.study_title}</CardTitle></CardHeader>
        <CardContent className="flex flex-wrap items-center gap-2"><Badge variant="secondary">{s.kind} · {s.status}</Badge><span className="text-sm text-[#6d6d70]">{s.scheduled_at}</span><span className="flex-1" />
        {(s.status === "booked") && <button type="button" onClick={() => void cancel(s.id)} className="rounded-full border border-[#e4e4e7] px-4 py-2 text-xs">{text({ en: "Cancel", fr: "Annuler" })}</button>}</CardContent></Card>))}
    </div>{items.length === 0 && <p className="mt-6 text-sm text-[#6d6d70]">{text({ en: "No sessions.", fr: "Aucune séance." })}</p>}
  </TesterShell>);
}
