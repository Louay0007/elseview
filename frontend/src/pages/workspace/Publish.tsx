import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { ArrowLeft, BadgePercent, ChevronDown, Plus } from "lucide-react";
import { useAuthLocale } from "@/components/auth/AuthLocale";
import { WorkspaceShell, useWorkspaceNav } from "@/components/workspace/WorkspaceShell";
import { OrderSidebar } from "@/components/workspace/OrderSidebar";
import { StudyHeader } from "@/components/workspace/StudyHeader";
import { StudyRail, type RailStep } from "@/components/workspace/StudyRail";
import { studyQuery, type StudyParams } from "@/components/workspace/studyNav";
import { CardForm, type CardFormValue } from "@/components/workspace/CardForm";
import { panelCredits } from "@/lib/pricing";
import { methodByKey } from "@/lib/methods";
import { routes, withQuery } from "@/lib/routes";

const DEMO_PROMO = "ELSEVIEW10";

function Accordion({ id, title, open, onToggle, children }: {
  id: string; title: string; open: boolean; onToggle: () => void; children: React.ReactNode;
}) {
  return (
      <div className={`overflow-hidden rounded-2xl border bg-white transition-colors ${open ? "border-[#18181b]" : "border-[#e4e4e7]"}`}>
      <button type="button" onClick={onToggle} aria-expanded={open} aria-controls={id}
        className="flex w-full items-center gap-3 px-5 py-4 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[#0a84ff]">
      <span className="flex-1 text-[16px] font-semibold text-black">{title}</span>
      <span aria-hidden="true" className="grid size-6 place-items-center text-black">{open ? <ChevronDown className="size-5 rotate-180" strokeWidth={1.6} /> : <Plus className="size-5" strokeWidth={1.6} />}</span>
      </button>
      {open && <div id={id} className="border-t border-[#ececf0] px-5 py-5">{children}</div>}
      </div>
  );
}

export default function Publish() {
  const { text } = useAuthLocale();
  const nav = useWorkspaceNav();
  const [params] = useSearchParams();
  const studyName = params.get("name")?.trim() || "Card Sorting 1";
  const studyProject = params.get("project")?.trim() || "hey";
  const studyLang = params.get("lang") === "ar" ? "ar" : "en";
  const studyMethod = params.get("method") ?? "card_sort";
  const participants = Math.max(1, Math.min(1000, Number(params.get("participants")) || 61));

  const [summaryOpen, setSummaryOpen] = useState(false);
  const [promoOpen, setPromoOpen] = useState(true);
  const [payOpen, setPayOpen] = useState(true);
  const [code, setCode] = useState("");
  const [promoState, setPromoState] = useState<"idle" | "applied" | "invalid">("idle");
  const [card, setCard] = useState<CardFormValue | null>(null);
  const [publishAttempted, setPublishAttempted] = useState(false);
  const [published, setPublished] = useState(false);

  const credits = panelCredits(participants);
  const discount = promoState === "applied" ? Math.round(credits * 0.1) : 0;
  const payable = credits - discount;

  const applyPromo = () => {
    setPromoState(code.trim().toUpperCase() === DEMO_PROMO ? "applied" : "invalid");
  };

  const publish = () => {
    setPublishAttempted(true);
    if (!card?.valid) return;
    setPublished(true);
  };

  const methodTitle = methodByKey(studyMethod)?.title ?? { en: "Card sorting", fr: "Tri de cartes" };
  const study: StudyParams = { method: studyMethod, name: studyName, lang: studyLang, project: studyProject, participants };

  const handleRailSelect = (next: RailStep) => {
    if (next === "publish") return;
    if (next === "recruit") nav.goWithParams(withQuery(routes.recruit, studyQuery(study)));
    else nav.goWithParams(withQuery(routes.newStudy, studyQuery(study)));
  };

  return (
      <WorkspaceShell>
      <div className="-mx-6 -mt-8 border-b border-[#e8e8ec] bg-[#fafafa] px-6 py-3">
      <StudyHeader studyName={studyName} project={studyProject} lang={studyLang} method={studyMethod} onPublish={publish} />
      </div>

      <div className="mt-8 grid gap-10 lg:grid-cols-[200px_minmax(0,1fr)_340px]">
      <aside><StudyRail active="publish" onSelect={handleRailSelect} /></aside>
      <main className="min-w-0">
      <h1 className="text-[24px] font-bold tracking-tight text-black">{text({ en: "You're nearly ready to publish!", fr: "Presque prêt à publier !" })}</h1>
      <p className="mt-2 max-w-[70ch] text-[14.5px] leading-relaxed text-[#3a3a3c]">
            {text({ en: "A test will only go live when you publish it - start collecting real time data now.", fr: "Un test ne sera en ligne qu’une fois publié - collectez des données en temps réel." })}{" "}
      <button type="button" onClick={() => setSummaryOpen((v) => !v)} aria-expanded={summaryOpen} aria-controls="publish-test-summary"
              className="font-semibold text-[#1d4ed8] underline underline-offset-2 hover:no-underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff]">
              {text({ en: "View test summary", fr: "Voir le résumé du test" })}
      </button>
      </p>
          {summaryOpen && (
      <dl id="publish-test-summary" className="mt-4 grid gap-2 rounded-2xl border border-[#e4e4e7] bg-white p-5 text-[14px] sm:grid-cols-2">
      <div><dt className="text-[#6d6d70]">{text({ en: "Study", fr: "Étude" })}</dt><dd className="mt-0.5 font-semibold text-black">{studyName}</dd></div>
      <div><dt className="text-[#6d6d70]">{text({ en: "Method", fr: "Méthode" })}</dt><dd className="mt-0.5 font-semibold text-black">{text(methodTitle)}</dd></div>
      <div><dt className="text-[#6d6d70]">{text({ en: "Language", fr: "Langue" })}</dt><dd className="mt-0.5 font-semibold text-black">{studyLang === "ar" ? "Arabic (عربي)" : "English"}</dd></div>
      <div><dt className="text-[#6d6d70]">{text({ en: "Participants", fr: "Participants" })}</dt><dd className="mt-0.5 font-semibold text-black">{participants}</dd></div>
      </dl>
          )}

      <div className="mt-5 grid gap-3">
      <Accordion id="publish-promo" title="Promo Code" open={promoOpen} onToggle={() => setPromoOpen((v) => !v)}>
      <p className="text-[14px] text-[#3a3a3c]">Enter your promotional code here. Click “Apply” to update your order</p>
      <div className="mt-3 flex flex-wrap items-center gap-2">
      <input value={code} onChange={(e) => { setCode(e.target.value); setPromoState("idle"); }} placeholder="Code" aria-label="Promo code"
                  className="min-h-[46px] w-40 rounded-xl border border-[#d9d9df] bg-white px-4 text-[14px] uppercase outline-none focus:border-[#18181b]" />
      <button type="button" onClick={applyPromo} disabled={!code.trim()}
                  className="min-h-[46px] rounded-full bg-[#18181b] px-6 text-[14px] font-semibold text-white disabled:cursor-not-allowed disabled:opacity-40">Apply</button>
      </div>
              {promoState === "applied" && (
      <p role="status" className="mt-3 flex items-center gap-2 text-[13.5px] font-medium text-[#1d5c1d]">
      <BadgePercent className="size-4" strokeWidth={1.8} aria-hidden="true" />Code {DEMO_PROMO} applied — 10% off your payment.
      </p>
              )}
              {promoState === "invalid" && (
      <p role="alert" className="mt-3 text-[13.5px] font-medium text-[#9c2d20]">This code isn’t valid. Try {DEMO_PROMO}.</p>
              )}
      </Accordion>

      <Accordion id="publish-payment" title="Payment method" open={payOpen} onToggle={() => setPayOpen((v) => !v)}>
      <div className="flex items-center justify-end">
      <button type="button" className="flex items-center gap-1.5 text-[13px] font-bold uppercase tracking-wide text-[#1d4ed8] hover:underline">
      <Plus className="size-4" strokeWidth={2} aria-hidden="true" />Add new card
      </button>
      </div>
      <div className="mt-3">
      <CardForm onChange={setCard} forceTouched={publishAttempted} />
      </div>
      </Accordion>
      </div>

          {published && (
      <p role="status" className="mt-4 rounded-lg bg-[#eef6ee] px-4 py-3 text-sm text-[#1d5c1d]">
              {text({ en: "Payment confirmed. Your test is published.", fr: "Paiement confirmé. Votre test est publié." })}
      </p>
          )}

      <div className="mt-6 flex items-center justify-between gap-3">
      <button type="button" onClick={() => nav.goWithParams(withQuery(routes.recruit, studyQuery(study)))}
              className="inline-flex min-h-[48px] items-center gap-2 rounded-full border border-[#18181b] px-6 text-[14.5px] font-medium text-black hover:bg-[#f7f7f8]">
      <ArrowLeft className="size-4" strokeWidth={1.8} aria-hidden="true" />Previous
      </button>
      <button type="button" onClick={publish}
              className="inline-flex min-h-[48px] items-center gap-2 rounded-full bg-[#0b1e4b] px-8 text-[14.5px] font-semibold text-white hover:bg-[#1d4ed8] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff]">
              Publish for ${payable}{discount > 0 && <s className="text-[13px] font-normal text-white/70">${credits}</s>}
      </button>
      </div>
      </main>

      <OrderSidebar participants={participants} panelLabel="~29.7K" speed={82} feesOpen />
      </div>
      </WorkspaceShell>
  );
}
