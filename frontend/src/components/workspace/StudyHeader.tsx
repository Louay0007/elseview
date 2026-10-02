import { useState } from "react";
import { ArrowLeft, Check, ChevronDown, Clock, Eye, Globe, Layers, LayoutGrid, Pencil, Share2 } from "lucide-react";
import { useAuthLocale } from "@/components/auth/AuthLocale";
import { useWorkspaceNav } from "@/components/workspace/WorkspaceShell";
import { methodByKey } from "@/lib/methods";
import { routes } from "@/lib/routes";

const MEDIUM_METHODS = new Set(["card_sort", "tree_test"]);

type StudyHeaderProps = {
  studyName: string;
  project: string;
  lang: string;
  method: string;
  saved?: boolean;
  onPreview?: () => void;
  onPublish?: () => void;
};

export function StudyHeader({ studyName, project, lang, method, saved = true, onPreview, onPublish }: StudyHeaderProps) {
  const { text } = useAuthLocale();
  const nav = useWorkspaceNav();
  const [menuOpen, setMenuOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const methodTitle = methodByKey(method)?.title ?? { en: "Prototype", fr: "Prototype" };
  const langLabel = lang === "ar" ? "Arabic (عربي)" : "English";
  const duration = MEDIUM_METHODS.has(method)
    ? text({ en: "Medium 3–7 mins", fr: "Moyen 3–7 min" })
    : text({ en: "Short 1–3 mins", fr: "Court 1–3 min" });

  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch { /* clipboard unavailable */ }
  };
  const publish = () => {
    setMenuOpen(false);
    if (onPublish) onPublish();
    else nav.goWithParams(routes.dashboard);
  };

  return (
    <div className="flex flex-wrap items-center gap-3">
      <button type="button" onClick={() => nav.goWithParams(routes.dashboard)} aria-label={text({ en: "Back", fr: "Retour" })} className="grid size-10 place-items-center rounded-xl border border-[#e4e4e7] bg-white text-[#52525b] hover:bg-[#f4f4f5]"><ArrowLeft className="size-5" strokeWidth={1.8} aria-hidden="true" /></button>
      <p className="flex items-center gap-2 text-[19px] font-bold text-black">{studyName} <span className="grid size-7 place-items-center rounded-lg bg-[#eef4ff] text-[#1d4ed8]" aria-hidden="true"><Pencil className="size-3.5" strokeWidth={1.8} /></span></p>
      <span className="ml-2 inline-flex items-center gap-1.5 rounded-lg border border-[#bfd0f5] bg-[#eef4ff] px-2.5 py-1 text-[13px] font-medium text-[#0b1e4b]"><LayoutGrid className="size-4 text-[#1d4ed8]" strokeWidth={1.8} aria-hidden="true" /> {project}</span>
      <span className="inline-flex items-center gap-1.5 rounded-lg border border-[#bfd0f5] bg-[#eef4ff] px-2.5 py-1 text-[13px] font-medium text-[#0b1e4b]"><Globe className="size-4 text-[#1d4ed8]" strokeWidth={1.8} aria-hidden="true" /> {langLabel}</span>
      <span className="inline-flex items-center gap-1.5 rounded-lg bg-[#0b1e4b] px-2.5 py-1 text-[13px] font-medium text-white"><Layers className="size-4" strokeWidth={1.8} aria-hidden="true" /> {text(methodTitle)}</span>
      <span className="flex-1" />
      <span className="hidden items-center gap-1.5 text-[14px] font-medium text-black md:flex"><Clock className="size-4 text-[#1d4ed8]" strokeWidth={1.8} aria-hidden="true" /> {duration}</span>
      {saved && <span className="grid size-7 place-items-center rounded-full border border-[#22c55e] text-[#22c55e]" aria-label={text({ en: "Saved", fr: "Enregistré" })}><Check className="size-4" strokeWidth={2.2} aria-hidden="true" /></span>}
      <button type="button" onClick={() => void copyLink()} aria-label={text({ en: "Copy study link", fr: "Copier le lien" })} title={copied ? text({ en: "Link copied", fr: "Lien copié" }) : text({ en: "Copy study link", fr: "Copier le lien" })} className="grid size-10 place-items-center rounded-xl border border-[#e4e4e7] bg-white text-[#52525b] hover:bg-[#f4f4f5] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1d4ed8]"><Share2 className="size-5" strokeWidth={1.8} aria-hidden="true" /></button>
      <button type="button" onClick={onPreview} className="inline-flex min-h-[44px] items-center gap-2 rounded-full border border-[#0b1e4b] px-5 text-[14px] font-semibold text-[#0b1e4b] hover:bg-[#eef4ff] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1d4ed8]"><Eye className="size-4 text-[#1d4ed8]" strokeWidth={1.8} aria-hidden="true" /> {text({ en: "Preview test", fr: "Aperçu" })}</button>
      <div className="relative">
        <div className="flex min-h-[44px] items-stretch overflow-hidden rounded-full bg-[#0b1e4b] text-white">
          <button type="button" onClick={publish} className="px-5 text-[14px] font-semibold hover:bg-[#1d4ed8] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-white">{text({ en: "Publish", fr: "Publier" })}</button>
          <button type="button" onClick={() => setMenuOpen((v) => !v)} aria-expanded={menuOpen} aria-label={text({ en: "More publish options", fr: "Plus d’options" })} className="grid w-10 place-items-center border-l border-white/25 hover:bg-[#1d4ed8] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-white"><ChevronDown className={`size-4 transition-transform ${menuOpen ? "rotate-180" : ""}`} strokeWidth={2} aria-hidden="true" /></button>
        </div>
        {menuOpen && (
          <div role="menu" className="absolute right-0 top-[calc(100%+8px)] z-20 w-52 overflow-hidden rounded-xl border border-[#e4e4e7] bg-white py-1 shadow-[0_18px_50px_-20px_rgba(0,0,0,.35)]">
            <button type="button" role="menuitem" onClick={publish} className="block w-full px-4 py-2.5 text-left text-[14px] font-medium text-black hover:bg-[#f4f4f5]">{text({ en: "Publish now", fr: "Publier" })}</button>
            <button type="button" role="menuitem" onClick={() => void copyLink()} className="block w-full px-4 py-2.5 text-left text-[14px] text-[#52525b] hover:bg-[#f4f4f5]">{copied ? text({ en: "Link copied!", fr: "Lien copié !" }) : text({ en: "Copy study link", fr: "Copier le lien" })}</button>
          </div>
        )}
      </div>
    </div>
  );
}
