import { useEffect } from "react";
import { Bell, CircleHelp, FileText, LogOut, Plus, Settings, User, UserPlus, Wallet, ChevronDown } from "lucide-react";
import { useAuthLocale } from "@/components/auth/AuthLocale";
import { cn } from "@/lib/utils";
import "./WorkspaceMenus.css";

function useDismiss(open: boolean, onClose: () => void) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    const onPointer = (e: PointerEvent) => {
      if (!(e.target as HTMLElement).closest("[data-menu-root]")) onClose();
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onPointer);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onPointer);
    };
  }, [open, onClose]);
}
type ShellProps = { open: boolean; onClose: () => void; label: string; align?: "left" | "right"; children: React.ReactNode };
export function MenuShell({ open, onClose, label, align = "left", children }: ShellProps) {
  useDismiss(open, onClose);
  if (!open) return null;
  return (
    <div data-menu-root role="menu" aria-label={label} className={cn("ws-menu", align === "right" && "ws-menu--right")}>
      {children}
    </div>
  );
}

function Row({ icon, label, onSelect }: { icon: React.ReactNode; label: string; onSelect: () => void }) {
  return (
    <button type="button" role="menuitem" onClick={onSelect} className="ws-row">
      <span className="ws-row__icon" aria-hidden="true">{icon}</span>
      <span className="ws-row__label">{label}</span>
    </button>
  );
}

const sw = { className: "ws-svg", strokeWidth: 1.5 } as const;

export function WorkspaceTrigger(p: { workspaceName: string; open: boolean; onToggle: () => void; onClose: () => void; onSettings?: () => void; onBilling?: () => void; onCredits?: () => void }) {
  const { text } = useAuthLocale();
  return (
    <div className="relative" data-menu-root>
      <button type="button" onClick={p.onToggle} aria-expanded={p.open} aria-haspopup="menu" className={cn("ws-trigger", p.open && "ws-trigger--open")}>
        <span className="ws-trigger__avatar" aria-hidden="true"><User className="size-[18px]" strokeWidth={1.8} /></span>
        <span className="ws-trigger__name">{p.workspaceName}</span>
        <ChevronDown className={cn("ws-trigger__chev", p.open && "ws-trigger__chev--open")} aria-hidden="true" />
      </button>
      <MenuShell open={p.open} onClose={p.onClose} label={text({ en: "Workspace menu", fr: "Menu espace" })}>
        <div className="ws-head">
          <span className="ws-head__avatar" aria-hidden="true"><User className="size-6" strokeWidth={1.7} /></span>
          <p className="ws-head__title">{p.workspaceName}</p>
          <p className="ws-head__sub">{text({ en: "Individual workspace", fr: "Espace individuel" })}</p>
          <button type="button" onClick={p.onClose} className="ws-upgrade">{text({ en: "Upgrade to Team plan", fr: "Passer au plan Equipe" })}</button>
        </div>
        <div className="ws-sep" aria-hidden="true" />
        <div className="ws-list">
          <Row icon={<User {...sw} />} label={text({ en: "Settings", fr: "Parametres" })} onSelect={() => { p.onClose(); p.onSettings?.(); }} />
          <Row icon={<FileText {...sw} />} label={text({ en: "Workspace billing", fr: "Facturation" })} onSelect={() => { p.onClose(); p.onBilling?.(); }} />
          <Row icon={<Wallet {...sw} />} label={text({ en: "Credits wallet", fr: "Credits" })} onSelect={() => { p.onClose(); p.onCredits?.(); }} />
        </div>
        <div className="ws-sep" aria-hidden="true" />
        <div className="ws-list ws-list--bottom">
          <Row icon={<Plus {...sw} />} label={text({ en: "Add workspace", fr: "Ajouter un espace" })} onSelect={p.onClose} />
        </div>
      </MenuShell>
    </div>
  );
}

export function UserTrigger(p: { displayName: string; fullName: string; initial: string; open: boolean; onToggle: () => void; onClose: () => void; onAccount?: () => void; onNotifications?: () => void; onRefer?: () => void; onSupport?: () => void; onLogOut: () => void }) {
  const { text } = useAuthLocale();
  return (
    <div className="relative" data-menu-root>
      <button type="button" onClick={p.onToggle} aria-expanded={p.open} aria-haspopup="menu" className={cn("ws-user-trigger", p.open && "ws-user-trigger--open")}>
        <span className="ws-user-trigger__name">{p.displayName}</span>
        <ChevronDown className={cn("ws-trigger__chev", p.open && "ws-trigger__chev--open")} aria-hidden="true" />
      </button>
      <MenuShell open={p.open} onClose={p.onClose} align="right" label={text({ en: "Account menu", fr: "Menu compte" })}>
        <div className="ws-account">
          <span className="ws-account__avatar" aria-hidden="true">{p.initial}</span>
          <span className="ws-account__name">{p.fullName}</span>
        </div>
        <div className="ws-list ws-list--divided">
          <Row icon={<Settings {...sw} />} label={text({ en: "Account", fr: "Compte" })} onSelect={() => { p.onClose(); p.onAccount?.(); }} />
          <Row icon={<Bell {...sw} />} label={text({ en: "Notifications settings", fr: "Notifications" })} onSelect={() => { p.onClose(); p.onNotifications?.(); }} />
          <Row icon={<UserPlus {...sw} />} label={text({ en: "Refer & Earn", fr: "Parrainage" })} onSelect={() => { p.onClose(); p.onRefer?.(); }} />
          <Row icon={<CircleHelp {...sw} />} label={text({ en: "Support", fr: "Assistance" })} onSelect={() => { p.onClose(); p.onSupport?.(); }} />
          <Row icon={<LogOut {...sw} />} label={text({ en: "Log out", fr: "Se deconnecter" })} onSelect={p.onLogOut} />
        </div>
      </MenuShell>
    </div>
  );
}

