import { useState } from "react";
import { useAuthLocale } from "@/components/auth/AuthLocale";
import { BackToTesterHome, TesterShell } from "@/components/tester/TesterShell";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
export default function TesterProfile() {
  const { text } = useAuthLocale(); const [stats] = useState<{ quality_score: number; no_show_count: number; completed_count: number } | null>({ quality_score: 92, no_show_count: 1, completed_count: 12 });
  const [name, setName] = useState("Louay"); const [lang, setLang] = useState("French · Arabic");
  const [saved, setSaved] = useState<string | null>(null);
  return (<TesterShell>
    <BackToTesterHome />
    <h1 className="text-[28px] font-bold text-black">{text({ en: "Your profile.", fr: "Votre profil." })}</h1>
    <p className="mt-2 text-[16px] text-[#6d6d70]">{text({ en: "Good scores get more invites.", fr: "Un bon score donne plus d’invitations." })}</p>
    <Card className="mt-6 rounded-[18px]"><CardHeader><CardTitle>{text({ en: "Score", fr: "Score" })}</CardTitle>
      <CardDescription>{text({ en: "Out of 100.", fr: "Sur 100. Les absences le baissent." })}</CardDescription></CardHeader>
      <CardContent><p className="text-[28px] font-bold">{stats?.quality_score ?? 100}</p>
        <p className="mt-1 text-sm text-[#6d6d70]">{text({ en: `${stats?.completed_count ?? 0} done · ${stats?.no_show_count ?? 0} missed`, fr: `${stats?.completed_count ?? 0} finies · ${stats?.no_show_count ?? 0} manquées` })}</p></CardContent></Card>
  </TesterShell>);
}
