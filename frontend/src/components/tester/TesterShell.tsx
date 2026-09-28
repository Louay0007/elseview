import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowLeft, Bell, CircleHelp, LogOut, Settings, User, ChevronDown } from "lucide-react";
import { useAuthLocale } from "@/components/auth/AuthLocale";
import { SupportCenter } from "@/components/workspace/SupportCenter";
import { MenuShell } from "@/components/workspace/WorkspaceMenus";
import { cn } from "@/lib/utils";

export function useTesterNav() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const firstName = params.get("firstName")?.trim() ?? "";
  const displayName = firstName || "tester";
  const go = (path: string) => navigate(firstName ? `${path}?firstName=${encodeURIComponent(firstName)}` : path);
  return { navigate, firstName, displayName, go };
}

function TesterMenu({ open, onClose, onAccount, onNotifications, onSupport, onLogOut }: {
  open: boolean; onClose: () => void; onAccount: () => void; onNotifications: () => void; onSupport: () => void; onLogOut: () => void;
}) {
  const { text } = useAuthLocale();
  const row = "ws-row";
  return (
    <MenuShell open={open} onClose={onClose} align="right" label={text({ en: "Account menu", fr: "Menu compte" })}>
      <div className="ws-list ws-list--divided">
        <button type="button" role="menuitem" onClick={() => { onClose(); onAccount(); }} className={row}><span className="ws-row__icon" aria-hidden="true"><Settings className="ws-svg" strokeWidth={1.5} /></span><span className="ws-row__label">{text({ en: "Profile", fr: "Profil" })}</span></button>
        <button type="button" role="menuitem" onClick={() => { onClose(); onNotifications(); }} className={row}><span className="ws-row__icon" aria-hidden="true"><Bell className="ws-svg" strokeWidth={1.5} /></span><span className="ws-row__label">{text({ en: "Notifications settings", fr: "Notifications" })}</span></button>
        <button type="button" role="menuitem" onClick={() => { onClose(); onSupport(); }} className={row}><span className="ws-row__icon" aria-hidden="true"><CircleHelp className="ws-svg" strokeWidth={1.5} /></span><span className="ws-row__label">{text({ en: "Support", fr: "Assistance" })}</span></button>
        <button type="button" role="menuitem" onClick={onLogOut} className={row}><span className="ws-row__icon" aria-hidden="true"><LogOut className="ws-svg" strokeWidth={1.5} /></span><span className="ws-row__label">{text({ en: "Log out", fr: "Se deconnecter" })}</span></button>
      </div>
    </MenuShell>
  );
}

export function TesterShell({ children }: { children: React.ReactNode }) {
  const { text } = useAuthLocale();
  const { navigate, firstName, displayName, go } = useTesterNav();
  const [userOpen, setUserOpen] = useState(false);
  const [supportOpen, setSupportOpen] = useState(false);
  return (
    <main className="flex min-h-dvh flex-col bg-white text-[#18181b]">
      <header className="bg-black text-white">
        <div className="mx-auto flex w-full max-w-[1440px] items-center gap-5 px-6 py-3.5">
          <Link to="/tester" aria-label="Elseview tester home" className="flex shrink-0 items-center gap-2.5 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white">
            <img src="/images/brand/elseview-logo-white.png" alt="" aria-hidden="true" className="h-9 w-9 object-contain" />
            <span className="text-[24px] font-bold tracking-tight text-white">Elseview</span>
          </Link>
          <span className="hidden h-8 w-px bg-white/25 sm:block" aria-hidden="true" />
          <span className="hidden items-center gap-2 text-[14px] text-white/85 sm:flex"><User className="size-4" strokeWidth={1.8} aria-hidden="true" />{text({ en: "Tester space", fr: "Espace testeur" })}</span>
          <span className="flex-1" />
          <div className="relative" data-menu-root>
            <button type="button" onClick={() => setUserOpen((v) => !v)} aria-expanded={userOpen} aria-haspopup="menu" className={cn("ws-user-trigger", userOpen && "ws-user-trigger--open")}>
              <span className="ws-user-trigger__name">{displayName}</span>
              <ChevronDown className={cn("ws-trigger__chev", userOpen && "ws-trigger__chev--open")} aria-hidden="true" />
            </button>
            <TesterMenu open={userOpen} onClose={() => setUserOpen(false)} onAccount={() => go("/tester/profile")} onNotifications={() => go("/tester/profile")} onSupport={() => setSupportOpen(true)} onLogOut={() => navigate("/auth/login?role=tester")} />
          </div>
        </div>
      </header>
      <section className="mx-auto w-full max-w-[1440px] flex-1 px-6 pb-24 pt-8">
        {children}
      </section>
      <footer className="flex items-center justify-between gap-4 bg-[#f5f5f6] px-6 py-[18px] text-[14px] text-[#3a3a3c]">
        <p className="m-0">{text({ en: "© 2026 Elseview. All rights reserved.", fr: "© 2026 Elseview. Tous droits réservés." })}</p>
        <nav className="flex gap-12" aria-label="Legal">
          <Link to="/terms" className="rounded text-[#3a3a3c] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff] focus-visible:ring-offset-2">{text({ en: "Terms of use", fr: "Conditions d'utilisation" })}</Link>
          <Link to="/privacy" className="rounded text-[#3a3a3c] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff] focus-visible:ring-offset-2">{text({ en: "Privacy policy", fr: "Politique de confidentialité" })}</Link>
        </nav>
      </footer>
      <button type="button" aria-label={text({ en: "Help", fr: "Aide" })} onClick={() => setSupportOpen(true)} className="fixed bottom-6 right-6 z-30 grid size-[60px] place-items-center rounded-full text-white shadow-xl transition-transform hover:scale-105" style={{ background: "linear-gradient(135deg,#1d4ed8,#0ea5e9)", boxShadow: "0 18px 40px -16px rgba(29,78,216,.8)" }}>
        <CircleHelp className="size-6" strokeWidth={1.6} aria-hidden="true" />
      </button>
      <SupportCenter open={supportOpen} onClose={() => setSupportOpen(false)} />
    </main>
  );
}

export function BackToTesterHome() {
  const { text } = useAuthLocale();
  const { go } = useTesterNav();
  return (
    <button type="button" onClick={() => go("/tester")}
      className="inline-flex min-h-[44px] items-center gap-2 rounded-full border border-[#e4e4e7] px-5 text-[14px] font-medium text-black hover:bg-[#f7f8fa] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff]">
      <ArrowLeft className="size-4" strokeWidth={1.8} aria-hidden="true" />
      {text({ en: "Back to home", fr: "Retour à l'accueil" })}
    </button>
  );
}
