import { useState } from "react";
import { useAuthLocale } from "@/components/auth/AuthLocale";
import { BackToTesterHome, TesterShell } from "@/components/tester/TesterShell";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { mockEarnings } from "./testerMocks";
type E = { total_millimes: number; pending_millimes: number; paid_millimes: number; items: { id: string; amount_millimes: number; state: string }[] };
export default function TesterEarnings() {
  const { text } = useAuthLocale(); const [data] = useState<E | null>(mockEarnings as E);
  const tnd = (m: number) => `${(m / 1000).toFixed(2)} TND`;
  return (<TesterShell>
    <BackToTesterHome />
    <h1 className="text-[28px] font-bold text-black">{text({ en: "Your earnings.", fr: "Vos gains." })}</h1>
    <p className="mt-2 text-[16px] text-[#6d6d70]">{text({ en: "Paid by hand. No bank in the app.", fr: "Payé à la main, enregistré seulement." })}</p>
    <div className="mt-6 grid gap-4 sm:grid-cols-3">
      <Card className="rounded-[18px]"><CardHeader><CardTitle>{text({ en: "Total", fr: "Total" })}</CardTitle></CardHeader><CardContent><p className="text-[24px] font-bold">{tnd(data?.total_millimes ?? 0)}</p></CardContent></Card>
      <Card className="rounded-[18px]"><CardHeader><CardTitle>{text({ en: "Waiting", fr: "En attente" })}</CardTitle></CardHeader><CardContent><p className="text-[24px] font-bold">{tnd(data?.pending_millimes ?? 0)}</p></CardContent></Card>
      <Card className="rounded-[18px]"><CardHeader><CardTitle>{text({ en: "Paid", fr: "Payé" })}</CardTitle></CardHeader><CardContent><p className="text-[24px] font-bold">{tnd(data?.paid_millimes ?? 0)}</p></CardContent></Card>
    </div>
    <ul className="mt-6 grid gap-2">{(data?.items ?? []).map((i) => (<li key={i.id} className="flex items-center gap-2 rounded-xl border border-[#e4e4e7] p-3 text-sm"><span className="font-medium">{tnd(i.amount_millimes)}</span><span className="text-[#6d6d70]">{i.state}</span></li>))}</ul>
    {(data?.items ?? []).length === 0 && <p className="mt-6 text-sm text-[#6d6d70]">{text({ en: "No earnings yet.", fr: "Aucun gain. Finissez une étude." })}</p>}
  </TesterShell>);
}
