import { useEffect } from "react";
import { BookOpen, Bookmark, ChevronRight, ExternalLink, Mail, MessageCircleMore, X, CircleHelp } from "lucide-react";
import { useAuthLocale } from "@/components/auth/AuthLocale";
import { cn } from "@/lib/utils";
import "./SupportCenter.css";

function Faces() {
  return (
    <span className="sc-faces" aria-hidden="true">
      <svg viewBox="0 0 32 32" className="sc-face"><circle cx="16" cy="16" r="15" fill="#dc2626" /><circle cx="11" cy="13" r="2" fill="#fff" /><circle cx="21" cy="13" r="2" fill="#fff" /><path d="M9 23c2-3.5 12-3.5 14 0" stroke="#fff" strokeWidth="2" fill="none" strokeLinecap="round" /><path d="M7 12l3 2M25 12l-3 2" stroke="#7f1d1d" strokeWidth="1.6" strokeLinecap="round" /></svg>
      <svg viewBox="0 0 32 32" className="sc-face sc-face--overlap"><circle cx="16" cy="16" r="15" fill="#f9a8d4" /><circle cx="11" cy="13" r="2" fill="#7c2d12" /><circle cx="21" cy="13" r="2" fill="#7c2d12" /><path d="M10 22c2-2 8-2 12 0" stroke="#7c2d12" strokeWidth="2" fill="none" strokeLinecap="round" /></svg>
      <svg viewBox="0 0 32 32" className="sc-face sc-face--overlap"><circle cx="16" cy="16" r="15" fill="#facc15" /><circle cx="11" cy="13" r="2" fill="#713f12" /><circle cx="21" cy="13" r="2" fill="#713f12" /><path d="M10 21h12" stroke="#713f12" strokeWidth="2" strokeLinecap="round" /></svg>
      <svg viewBox="0 0 32 32" className="sc-face sc-face--overlap"><circle cx="16" cy="16" r="15" fill="#a3e635" /><circle cx="11" cy="13" r="2" fill="#1a2e05" /><circle cx="21" cy="13" r="2" fill="#1a2e05" /><path d="M10 19c2 3 8 3 12 0" stroke="#1a2e05" strokeWidth="2" fill="none" strokeLinecap="round" /></svg>
      <svg viewBox="0 0 32 32" className="sc-face sc-face--overlap"><circle cx="16" cy="16" r="15" fill="#166534" /><circle cx="11" cy="12" r="2.2" fill="#fff" /><circle cx="21" cy="12" r="2.2" fill="#fff" /><path d="M8 17c1.5 5 6.5 7 8 7s6.5-2 8-7c-3 1.5-13 1.5-16 0z" fill="#fff" /></svg>
    </span>
  );
}

export function SupportCenter({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { text } = useAuthLocale();
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => { document.removeEventListener("keydown", onKey); document.body.style.overflow = ""; };
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="sc-root" role="dialog" aria-modal="true" aria-label={text({ en: "Support center", fr: "Centre d'assistance" })}>
      <button type="button" aria-label={text({ en: "Close support center", fr: "Fermer l'assistance" })} className="sc-scrim" onClick={onClose} />
      <aside className="sc-panel">
        <div className="sc-header">
          <h2 className="sc-title">{text({ en: "Support center", fr: "Centre d'assistance" })}</h2>
          <button type="button" onClick={onClose} className="sc-close" aria-label={text({ en: "Close", fr: "Fermer" })}><X className="size-5" strokeWidth={1.6} /></button>
        </div>
        <nav className="sc-links">
          <a className="sc-link" href="/#how-it-works"><span className="sc-link__left"><BookOpen className="sc-link__icon" strokeWidth={1.6} />{text({ en: "Guides", fr: "Guides" })}</span><ChevronRight className="sc-link__trail" /></a>
          <a className="sc-link" href="/#faq"><span className="sc-link__left"><CircleHelp className="sc-link__icon" strokeWidth={1.6} />FAQs</span><ExternalLink className="sc-link__trail" /></a>
          <a className="sc-link" href="mailto:support@elseview.test"><span className="sc-link__left"><Bookmark className="sc-link__icon" strokeWidth={1.6} />{text({ en: "Feature request", fr: "Demande de fonctionnalite" })}</span><ExternalLink className="sc-link__trail" /></a>
        </nav>
        <div className="sc-cards">
          <button type="button" className={cn("sc-card", "sc-card--primary")}>
            <Mail className="sc-card__icon" strokeWidth={1.5} />
            <span className="sc-card__label">{text({ en: "Contact us", fr: "Nous contacter" })}</span>
          </button>
          <button type="button" className={cn("sc-card", "sc-card--ghost")}>
            <MessageCircleMore className="sc-card__icon sc-card__icon--blue" strokeWidth={1.5} />
            <span className="sc-card__label sc-card__label--dark">{text({ en: "Live chat", fr: "Chat en direct" })}</span>
          </button>
        </div>
        <button type="button" className="sc-feedback">
          <span className="sc-feedback__label">{text({ en: "Share your feedback", fr: "Donnez votre avis" })}</span>
          <Faces />
        </button>
      </aside>
    </div>
  );
}
