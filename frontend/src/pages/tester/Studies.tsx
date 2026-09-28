import { useState } from "react";
import { useAuthLocale } from "@/components/auth/AuthLocale";
import { BackToTesterHome, TesterShell } from "@/components/tester/TesterShell";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { mockStudies } from "./testerMocks";
type Item = { id: string; title: string; method: string; credits: number; minutes: number; languages: string[] };
export default function TesterStudies() {
  const { text } = useAuthLocale(); const [items, setItems] = useState<Item[]>(mockStudies as Item[]);
  const [msg, setMsg] = useState<string|null>(null); const [err, setErr] = useState<string|null>(null);
  const [booked, setBooked] = useState<string[]>([]);
  const apply = (id: string) => { setErr(null); setBooked((b) => [...b, id]);
    setMsg(text({ en: "Booked. See Sessions.", fr: "Réservé. Voir Séances." })); };
  return (<TesterShell>
    <BackToTesterHome />
    <h1 className="text-[28px] font-bold text-black">{text({ en: "Studies for you.", fr: "Études pour vous." })}</h1>
    <p className="mt-2 max-w-[68ch] text-[16px] text-[#6d6d70]">{text({ en: "Pick one. Answer honestly.", fr: "Choisissez-en une. Répondez honnêtement." })}</p>
    {err && <p role="alert" className="mt-4 rounded-lg bg-[#fff2ef] px-4 py-3 text-sm text-[#9c2d20]">{err}</p>}
    {msg && <p role="status" className="mt-4 rounded-lg bg-[#eef6ee] px-4 py-3 text-sm text-[#1d5c1d]">{msg}</p>}
    <div className="mt-6 grid gap-4">{items.map((s) => (
      <Card key={s.id} className="rounded-[18px]"><CardHeader><CardTitle>{s.title}</CardTitle>
        <CardDescription>{s.method} · {s.minutes || 5} min · {s.languages.join(", ")} · {s.credits} credits</CardDescription></CardHeader>
        <CardContent><button type="button" onClick={() => apply(s.id)} className="rounded-full bg-[#18181b] px-5 py-2.5 text-sm text-white">{booked.includes(s.id) ? text({ en: "Booked", fr: "Réservé" }) : text({ en: "Apply", fr: "Participer" })}</button></CardContent></Card>))}
    </div>{items.length === 0 && !err && <p className="mt-6 text-sm text-[#6d6d70]">{text({ en: "No studies now.", fr: "Aucune étude." })}</p>}
  </TesterShell>);
}
