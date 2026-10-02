import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Bell, CircleHelp, Database, History, LogOut, Settings, Star, User, ChevronDown } from "lucide-react";
import { useAuthLocale } from "@/components/auth/AuthLocale";
import { SupportCenter } from "@/components/workspace/SupportCenter";
import { MenuShell } from "@/components/workspace/WorkspaceMenus";
import { cn } from "@/lib/utils";
import { authWords as words } from "@/lib/auth";
import { mockEarnings, mockTesterRating } from "@/pages/tester/testerMocks";
import { readTesterProfile } from "@/pages/tester/testerProfileStore";
import { authRoute, routes } from "@/lib/routes";

export function useTesterNav() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  // The onboarding wizard and the profile page both save the name, so a tester
  // arriving without a query param is still greeted by name rather than by the
  // anonymous "tester" label.
  const firstName = params.get("firstName")?.trim() || readTesterProfile().firstName.trim();
  const displayName = firstName || "tester";
  // A destination may already carry a query string (`/tester/runner?demo=…`) or a
  // fragment (`/tester/profile#notifications`), so the name is spliced in after
  // the query and before the hash to keep every parameter readable.
  const go = (path: string) => {
    if (!firstName) return navigate(path);
    const [target, hash] = path.split("#");
    const separator = target.includes("?") ? "&" : "?";
    return navigate(`${target}${separator}firstName=${encodeURIComponent(firstName)}${hash ? `#${hash}` : ""}`);
  };
  return { navigate, firstName, displayName, go };
}

function TesterMenu({ open, onClose, go, onLogOut }: {
  open: boolean; onClose: () => void; go: (path: string) => void; onLogOut: () => void;
}) {
  const { text } = useAuthLocale();
  const row = "ws-row";
  // The menu mirrors the account tabs, so a tester moves between sections the
  // same way from either place. Testers never see workspace pages, so every
  // destination stays inside the tester space. Log out is last because it
  // leaves that space, and support is reached from the help button instead.
  const pages = [
    { path: routes.testerProfile, label: words("Your profile", "Votre profil"), Icon: Settings },
    { path: routes.testerHistory, label: words("Test history", "Historique des tests"), Icon: History },
    { path: routes.testerEarnings, label: words("Wallet", "Portefeuille"), Icon: Database },
    { path: routes.testerNotifications, label: words("Notification settings", "Notifications"), Icon: Bell },
  ];
  return (
    <MenuShell open={open} onClose={onClose} align="right" label={text({ en: "Account menu", fr: "Menu compte" })}>
      <div className="ws-list ws-list--divided">
        {pages.map(({ path, label, Icon }) => (
          <button key={path} type="button" role="menuitem" onClick={() => { onClose(); go(path); }} className={row}>
            <span className="ws-row__icon" aria-hidden="true"><Icon className="ws-svg" strokeWidth={1.5} /></span>
            <span className="ws-row__label">{text(label)}</span>
          </button>
        ))}
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
  // Balance and rating are read here rather than passed in, so the header shows
  // the same two figures on every tester page instead of differing per route.
  const credits = `${((mockEarnings.total_millimes - mockEarnings.paid_millimes) / 1000).toFixed(2)} TND`;
  const rating = mockTesterRating;
  return (
    <main className="flex min-h-dvh flex-col bg-white text-[#18181b]">
      <header className="bg-black text-white">
        <div className="mx-auto flex w-full max-w-[1440px] items-center gap-3 px-4 py-3.5 sm:gap-5 sm:px-6">
          <Link to={routes.tester} aria-label="Elseview tester home" className="flex shrink-0 items-center gap-2.5 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white">
            <img src="/images/brand/elseview-logo-white.png" alt="" aria-hidden="true" className="h-9 w-9 object-contain" />
            <span className="hidden text-[24px] font-bold tracking-tight text-white sm:inline">Elseview</span>
          </Link>
          <span className="hidden h-8 w-px bg-white/25 sm:block" aria-hidden="true" />
          <span className="hidden items-center gap-2 text-[14px] text-white/85 sm:flex"><User className="size-4" strokeWidth={1.8} aria-hidden="true" />{text({ en: "Tester space", fr: "Espace testeur" })}</span>
          <span className="flex-1" />
          {(
            <Link to={routes.testerEarnings} className="inline-flex min-h-11 shrink-0 items-center gap-2 rounded-lg px-1 text-[14px] text-white/90 transition hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white sm:px-2">
              <Database className="size-[18px] shrink-0" strokeWidth={1.7} aria-hidden="true" />
              <span>{credits}</span>
              <span className="sr-only">{text({ en: "Earnings", fr: "Gains" })}</span>
            </Link>
          )}
          {(
            <p className="inline-flex min-h-11 shrink-0 items-center gap-2 px-1 text-[14px] sm:px-2">
              <Star className="size-[18px] shrink-0 text-[#3fbf6f]" strokeWidth={1.7} aria-hidden="true" />
              <span className="text-[#3fbf6f]">{rating}%</span>
              <span className="sr-only">{text({ en: "Tester rating", fr: "Note du testeur" })}</span>
            </p>
          )}
          <div className="relative shrink-0" data-menu-root>
            <button type="button" onClick={() => setUserOpen((v) => !v)} aria-expanded={userOpen} aria-haspopup="menu" className={cn("ws-user-trigger", userOpen && "ws-user-trigger--open")}>
              <span className="ws-user-trigger__name">{displayName}</span>
              <ChevronDown className={cn("ws-trigger__chev", userOpen && "ws-trigger__chev--open")} aria-hidden="true" />
            </button>
            <TesterMenu open={userOpen} onClose={() => setUserOpen(false)} go={go} onLogOut={() => navigate(authRoute("login", "tester"))} />
          </div>
        </div>
      </header>
      <section className="mx-auto w-full max-w-[1440px] flex-1 px-6 pb-24 pt-8">
        <div className="mx-auto w-full max-w-[1200px]">{children}</div>
      </section>
      <footer className="flex flex-wrap items-center justify-between gap-4 bg-[#f5f5f6] px-4 py-[18px] text-[14px] text-[#3a3a3c] sm:px-6">
        <p className="m-0">{text({ en: "© 2026 Elseview. All rights reserved.", fr: "© 2026 Elseview. Tous droits réservés." })}</p>
        <nav className="flex flex-wrap gap-x-6 gap-y-2 sm:gap-x-12" aria-label="Legal">
          <Link to={routes.terms} className="rounded text-[#3a3a3c] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff] focus-visible:ring-offset-2">{text({ en: "Terms of use", fr: "Conditions d'utilisation" })}</Link>
          <Link to={routes.privacy} className="rounded text-[#3a3a3c] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff] focus-visible:ring-offset-2">{text({ en: "Privacy policy", fr: "Politique de confidentialité" })}</Link>
        </nav>
      </footer>
      <button type="button" aria-label={text({ en: "Help", fr: "Aide" })} onClick={() => setSupportOpen(true)} className="fixed bottom-6 right-6 z-30 grid size-[60px] place-items-center rounded-full text-white shadow-xl transition-transform hover:scale-105" style={{ background: "linear-gradient(135deg,#1d4ed8,#0ea5e9)", boxShadow: "0 18px 40px -16px rgba(29,78,216,.8)" }}>
        <CircleHelp className="size-6" strokeWidth={1.6} aria-hidden="true" />
      </button>
      <SupportCenter open={supportOpen} onClose={() => setSupportOpen(false)} />
    </main>
  );
}
