import { useState } from "react";
import { useAuthLocale } from "@/components/auth/AuthLocale";
import { BackToTesterHome, TesterShell, useTesterNav } from "@/components/tester/TesterShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
export default function TesterDashboard() {
  const { text } = useAuthLocale(); const { go, firstName } = useTesterNav();
  const [avail] = useState(4); const [earn] = useState(4500); const [upcoming] = useState(2);
  const [names] = useState(["Coffee cups", "Checkout page", "Bus app survey"]);
  return (<TesterShell>
    <div className="flex flex-wrap items-center justify-between gap-4">
      <div>
        <p className="text-[13px] font-medium uppercase tracking-[0.08em] text-[#6d6d70]">{text({ en: "Your work", fr: "Votre travail" })}</p>
        <h1 className="mt-1 text-[30px] font-bold tracking-[-0.02em] text-black">{text({ en: `Hello${firstName ? ` ${firstName}` : ""}`, fr: `Bonjour${firstName ? ` ${firstName}` : ""}` })}</h1>
      </div>
      <div className="flex flex-wrap gap-3">
        <button type="button" onClick={() => go("/tester/studies")} className="inline-flex min-h-[46px] items-center gap-2 rounded-full bg-[#18181b] px-6 text-[15px] font-medium text-white hover:bg-black focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff] focus-visible:ring-offset-2">{text({ en: "See studies", fr: "Voir les études" })}</button>
        <button type="button" onClick={() => go("/tester/sessions")} className="inline-flex min-h-[46px] items-center gap-2 rounded-full border border-[#18181b] px-6 text-[15px] font-medium text-black hover:bg-[#f7f8fa] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff] focus-visible:ring-offset-2">{text({ en: "My sessions", fr: "Mes séances" })}</button>
        <button type="button" onClick={() => go("/tester/earnings")} className="inline-flex min-h-[46px] items-center gap-2 rounded-full bg-[#1d4ed8] px-6 text-[15px] font-medium text-white hover:bg-[#1e40af] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff] focus-visible:ring-offset-2">{text({ en: "Earnings", fr: "Gains" })}</button>
      </div>
    </div>
    <p className="mt-2 max-w-[68ch] text-[16px] text-[#6d6d70]">{text({ en: "Pick a study. Finish it. Earn credit.", fr: "Choisissez une étude, finissez-la, gagnez du crédit. Payé à la main." })}</p>
    <div className="mt-6 grid gap-4 sm:grid-cols-3">
      <Card className="rounded-[18px]"><CardHeader><CardTitle>{text({ en: "Studies for you", fr: "Études pour vous" })}</CardTitle></CardHeader>
        <CardContent><p className="text-[28px] font-bold">{avail}</p><button type="button" onClick={() => go("/tester/studies")} className="mt-2 rounded-full bg-[#18181b] px-4 py-2 text-sm text-white">{text({ en: "See studies", fr: "Voir" })}</button></CardContent></Card>
      <Card className="rounded-[18px]"><CardHeader><CardTitle>{text({ en: "Upcoming", fr: "À venir" })}</CardTitle></CardHeader>
        <CardContent><p className="text-[28px] font-bold">{upcoming}</p><button type="button" onClick={() => go("/tester/sessions")} className="mt-2 rounded-full border border-[#e4e4e7] px-4 py-2 text-sm">{text({ en: "My sessions", fr: "Mes séances" })}</button></CardContent></Card>
      <Card className="rounded-[18px]"><CardHeader><CardTitle>{text({ en: "Pending", fr: "En attente" })}</CardTitle></CardHeader>
        <CardContent><p className="text-[28px] font-bold">{(earn / 1000).toFixed(0)} TND</p><button type="button" onClick={() => go("/tester/earnings")} className="mt-2 rounded-full border border-[#e4e4e7] px-4 py-2 text-sm">{text({ en: "Earnings", fr: "Gains" })}</button></CardContent></Card>
    </div>
    <div className="mt-6 grid gap-4 md:grid-cols-3">{names.map((n) => (
      <div key={n} className="rounded-[18px] border border-[#e4e4e7] bg-white p-5"><p className="font-semibold text-black">{n}</p>
        <p className="mt-1 text-sm text-[#6d6d70]">{text({ en: "5 min · French · 200 credits", fr: "5 min · Français · 200 crédits" })}</p>
        <button type="button" onClick={() => go("/tester/studies")} className="mt-3 rounded-full border border-[#e4e4e7] px-4 py-2 text-sm">{text({ en: "Open", fr: "Ouvrir" })}</button></div>))}</div>
  </TesterShell>);
}
