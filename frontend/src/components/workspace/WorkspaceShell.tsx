import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowLeft, CircleHelp, Coins, type LucideIcon } from "lucide-react";
import { useAuthLocale } from "@/components/auth/AuthLocale";
import { UserTrigger, WorkspaceTrigger } from "@/components/workspace/WorkspaceMenus";
import { SupportCenter } from "@/components/workspace/SupportCenter";
import { Card, CardContent, CardDescription, CardHeader } from "@/components/ui/card";

export function useWorkspaceNav() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const role = params.get("role") === "tester" ? "tester" : "researcher";
  const welcome = params.get("welcome") === "1";
  const firstName = params.get("firstName")?.trim() ?? "";
  const displayName = firstName || "louay";
  const workspaceName = firstName ? `${firstName}'s workspace` : "louay's workspace";
  const goWithParams = (path: string) => {
    const qs = new URLSearchParams({ role });
    if (firstName) qs.set("firstName", firstName);
    navigate(`${path}${path.includes("?") ? "&" : "?"}${qs.toString()}`);
  };
  return { navigate, role, welcome, firstName, displayName, workspaceName, goWithParams };
}

export function WorkspaceShell({ workspaceName, displayName, firstName, role, onSettings, onBilling, onCredits, onAccount, onNotifications, onRefer, fluid, children }: {
  workspaceName: string;
  displayName: string;
  firstName: string;
  role: string;
  onSettings: () => void;
  onBilling?: () => void;
  onCredits?: () => void;
  onAccount?: () => void;
  onNotifications?: () => void;
  onRefer?: () => void;
  fluid?: boolean;
  children: React.ReactNode;
}) {
  const navigate = useNavigate();
  const { text } = useAuthLocale();
  const [wsOpen, setWsOpen] = useState(false);
  const [userOpen, setUserOpen] = useState(false);
  const [supportOpen, setSupportOpen] = useState(false);
  return (
    <main className="flex min-h-dvh flex-col bg-white text-[#18181b]">
      <header className="bg-black text-white">
        <div className={`flex w-full items-center gap-5 px-6 py-3.5 ${fluid ? "" : "mx-auto max-w-[1440px]"}`}>
          <Link to={`/dashboard?role=${role}${firstName ? "&firstName=" + encodeURIComponent(firstName) : ""}`} aria-label="Elseview home" className="flex shrink-0 items-center gap-2.5 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white">
            <img src="/images/brand/elseview-logo-white.png" alt="" aria-hidden="true" className="h-9 w-9 object-contain" />
            <span className="text-[24px] font-bold tracking-tight text-white">Elseview</span>
          </Link>
          <span className="hidden h-8 w-px bg-white/25 sm:block" aria-hidden="true" />
          <WorkspaceTrigger workspaceName={workspaceName} open={wsOpen} onToggle={() => { setWsOpen((v) => !v); setUserOpen(false); }} onClose={() => setWsOpen(false)} onSettings={onSettings} onBilling={onBilling} onCredits={onCredits} />
          <button type="button" onClick={onSettings} aria-label={text({ en: "Open settings", fr: "Ouvrir les réglages" })} className="grid size-7 shrink-0 cursor-pointer place-items-center rounded-full bg-[#2563eb] text-[13px] font-bold text-white ring-1 ring-[#bfdbfe]/50 hover:bg-[#1d4ed8] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white">{displayName.charAt(0).toUpperCase()}</button>
          <button type="button" onClick={onCredits} className="hidden min-h-[34px] cursor-pointer items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-[13px] text-white/90 hover:bg-white/15 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white md:flex"><Coins className="size-4" strokeWidth={1.6} aria-hidden="true" />{text({ en: "0 Credits", fr: "0 crédit" })}</button>
          <span className="flex-1" />
          <UserTrigger displayName={displayName} fullName={firstName ? `${firstName} rjili` : "louay rjili"} initial={displayName.charAt(0).toUpperCase()} open={userOpen} onToggle={() => { setUserOpen((v) => !v); setWsOpen(false); }} onClose={() => setUserOpen(false)} onAccount={onAccount} onNotifications={onNotifications} onRefer={onRefer} onSupport={() => setSupportOpen(true)} onLogOut={() => navigate("/auth/login?role=" + role)} />
        </div>
      </header>
      <section className={`w-full flex-1 px-6 pb-24 pt-8 ${fluid ? "" : "mx-auto max-w-[1440px]"}`}>
        {children}
      </section>
      <footer className="flex items-center justify-between gap-4 bg-[#f5f5f6] px-6 py-[18px] text-[14px] text-[#3a3a3c]">
        <p className="m-0">{text({ en: "© 2026 Elseview. All rights reserved.", fr: "© 2026 Elseview. Tous droits réservés." })}</p>
        <nav className="flex gap-12" aria-label="Legal">
          <Link to="/terms" className="text-[#3a3a3c] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff] focus-visible:ring-offset-2 rounded">{text({ en: "Terms of use", fr: "Conditions d'utilisation" })}</Link>
          <Link to="/privacy" className="text-[#3a3a3c] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff] focus-visible:ring-offset-2 rounded">{text({ en: "Privacy policy", fr: "Politique de confidentialité" })}</Link>
        </nav>
      </footer>
      <button type="button" aria-label={text({ en: "Help", fr: "Aide" })} onClick={() => setSupportOpen(true)} className="fixed bottom-6 right-6 z-30 grid size-[60px] place-items-center rounded-full text-white shadow-xl transition-transform hover:scale-105" style={{ background: "linear-gradient(135deg,#1d4ed8,#0ea5e9)", boxShadow: "0 18px 40px -16px rgba(29,78,216,.8)" }}>
        <CircleHelp className="size-6" strokeWidth={1.6} aria-hidden="true" />
      </button>
      <SupportCenter open={supportOpen} onClose={() => setSupportOpen(false)} />
    </main>
  );
}

export type KpiItem = {
  icon: LucideIcon;
  label: { en: string; fr: string };
  value: string;
  sub: string;
};

export function KpiGrid({ items }: { items: KpiItem[] }) {
  const { text } = useAuthLocale();
  return (
    <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {items.map((k) => (
        <Card key={k.value} className="rounded-[22px] border-[#e4e4e7]">
          <CardHeader className="flex flex-row items-center gap-3 space-y-0 pb-2">
            <span className="grid size-10 place-items-center rounded-full bg-[#f2f2f7]"><k.icon className="size-5" strokeWidth={1.6} aria-hidden="true" /></span>
            <CardDescription>{text(k.label)}</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-[22px] font-bold tracking-tight text-black">{k.value}</p>
            <p className="mt-1 text-[13px] text-[#6d6d70]">{k.sub}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

export function BackToHome() {
  const { text } = useAuthLocale();
  const { goWithParams } = useWorkspaceNav();
  return (
    <button
      type="button"
      onClick={() => goWithParams("/dashboard")}
      className="inline-flex min-h-[44px] items-center gap-2 rounded-full border border-[#e4e4e7] px-5 text-[14px] font-medium text-black hover:bg-[#f7f8fa] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff]"
    >
      <ArrowLeft className="size-4" strokeWidth={1.8} aria-hidden="true" />
      {text({ en: "Back to home", fr: "Retour à l'accueil" })}
    </button>
  );
}
