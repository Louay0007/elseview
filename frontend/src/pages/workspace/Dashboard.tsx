import { useEffect, useState } from "react";
import { ArrowRight, BarChart3, Folder, History as HistoryIcon, Sparkles, UserRoundPlus } from "lucide-react";
import { apiFetch, backendAvailable } from "@/lib/api";
import { useWorkspace } from "@/components/workspace/WorkspaceContext";
import { useAuthLocale } from "@/components/auth/AuthLocale";
import { WelcomeDialog } from "@/components/workspace/WelcomeDialog";
import { PrototypeArt, CardSortingArt, PreferenceArt, TreeTestArt, SurveyArt, SurveyMultiArt, SurveyRatingArt, SurveyTextArt, RankingArt, ConstantSumArt, A11yArt, LanguageArt, FiveSecondArt, FirstClickArt, CustomRecruitmentArt } from "@/components/workspace/TestTypeArt";
import "@/components/workspace/WelcomeDialog.css";
import { WorkspaceShell, useWorkspaceNav } from "@/components/workspace/WorkspaceShell";
import { TestSettingsDialog } from "@/components/workspace/TestSettingsDialog";
import { routes, withQuery } from "@/lib/routes";

const testTypes = [
  { key: "prototype", method: "prototype.task", Art: PrototypeArt, title: { en: "Prototype", fr: "Prototype" }, body: { en: "People try your design.", fr: "Les gens essaient votre design et racontent." } },
  { key: "card", method: "card_sort", Art: CardSortingArt, title: { en: "Card sorting", fr: "Tri de cartes" }, body: { en: "People group cards.", fr: "Les gens rangent les cartes par idées." } },
  { key: "preference", method: "preference", Art: PreferenceArt, title: { en: "Pick your favorite", fr: "Préférence" }, body: { en: "People pick their favorite.", fr: "Les gens choisissent ce qu’ils préfèrent." } },
  { key: "tree", method: "tree_test", Art: TreeTestArt, title: { en: "Menu test", fr: "Test menu" }, body: { en: "People find things in your menu.", fr: "Les gens cherchent dans le menu." } },
  { key: "survey", method: "survey.single", Art: SurveyArt, title: { en: "Survey", fr: "Enquête" }, star: true, body: { en: "One question. Clear totals.", fr: "Une question, totaux clairs. Plus de formats dedans." } },
  { key: "five", method: "five_second", Art: FiveSecondArt, title: { en: "5 Seconds", fr: "5 secondes" }, body: { en: "Show a design for five seconds, then learn what people remember.", fr: "Montrez un design pendant cinq secondes, puis découvrez ce dont les participants se souviennent." } },
  { key: "click", method: "first_click", Art: FirstClickArt, title: { en: "First click", fr: "Premier clic" }, body: { en: "See the first click.", fr: "Voyez où les gens cliquent en premier." } },
  { key: "survey-multi", method: "survey.multi", Art: SurveyMultiArt, title: { en: "Survey: many", fr: "Enquête : multiple" }, body: { en: "Tick all that fit.", fr: "Cochez tout ce qui va." } },
  { key: "survey-rating", method: "survey.rating", Art: SurveyRatingArt, title: { en: "Survey: rating", fr: "Enquête : note" }, body: { en: "Rate from low to high.", fr: "Notez de bas en haut." } },
  { key: "survey-text", method: "survey.text", Art: SurveyTextArt, title: { en: "Survey: free text", fr: "Enquête : texte" }, body: { en: "People write freely.", fr: "Les gens écrivent librement." } },
  { key: "ranking", method: "survey.ranking", Art: RankingArt, title: { en: "Rank in order", fr: "Classer" }, body: { en: "Best to the top.", fr: "Le meilleur en haut." } },
  { key: "constant-sum", method: "survey.constant_sum", Art: ConstantSumArt, title: { en: "Split points", fr: "Répartir" }, body: { en: "Share 100 points.", fr: "Partagez 100 points." } },
  { key: "a11y", method: "accessibility.issue", Art: A11yArt, title: { en: "Report a problem", fr: "Signaler" }, body: { en: "People flag what blocks them.", fr: "Les gens signalent ce qui bloque." } },
  { key: "language", method: "language.review", Art: LanguageArt, title: { en: "Check wording", fr: "Vérifier texte" }, body: { en: "Review FR, AR, or EN text.", fr: "Relisez le texte FR, AR ou EN." } },
  { key: "recruit", method: "recruit", Art: CustomRecruitmentArt, title: { en: "Find people", fr: "Trouver des gens" }, hideFree: true, body: { en: "Invite people. They say yes first.", fr: "Invitez vos gens. Ils disent oui d’abord." } },
] as const;

export default function Dashboard() {
  const { text } = useAuthLocale();
  const { navigate, role, welcome, workspaceName, goWithParams } = useWorkspaceNav();
  const { workspaceId } = useWorkspace();
  const [overview, setOverview] = useState<{ live: number; draft: number; replies: number; toCheck: number } | null>(null);
  const [overviewState, setOverviewState] = useState<"idle" | "loading" | "error">("idle");
  const [selectedTest, setSelectedTest] = useState<(typeof testTypes)[number] | null>(null);

  useEffect(() => {
    if (!backendAvailable() || !workspaceId) return;
    setOverviewState("loading");
    apiFetch<{ live: number; draft: number; replies: number; toCheck: number }>(`/workspaces/${workspaceId}/analytics/overview`)
      .then((result) => { setOverview(result); setOverviewState("idle"); })
      .catch(() => setOverviewState("error"));
  }, [workspaceId]);
  const dismissWelcome = () => navigate(withQuery(routes.dashboard, { role }), { replace: true });
  return (
      <WorkspaceShell >
      <div className="flex flex-wrap items-center justify-between gap-4">
      <div>
      <p className="text-[13px] font-medium uppercase tracking-[0.08em] text-[#6d6d70]">{text({ en: "Your work", fr: "Votre travail" })}</p>
      <h1 className="mt-1 text-[30px] font-bold tracking-[-0.02em] text-black">{text({ en: "Home", fr: "Accueil" })}</h1>
      </div>
      <div className="flex flex-wrap gap-3">
      <button type="button" onClick={() => document.getElementById("choose-test")?.scrollIntoView({ behavior: "smooth" })} className="inline-flex min-h-[46px] items-center gap-2 rounded-full bg-[#18181b] px-6 text-[15px] font-medium text-white hover:bg-black focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff] focus-visible:ring-offset-2"><Folder className="size-[18px]" strokeWidth={1.6} aria-hidden="true" />{text({ en: "New study", fr: "Nouvelle étude" })}</button>
      <button type="button" onClick={() => goWithParams(routes.recruit)} className="inline-flex min-h-[46px] items-center gap-2 rounded-full border border-[#18181b] px-6 text-[15px] font-medium text-black hover:bg-[#f7f8fa] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff] focus-visible:ring-offset-2"><UserRoundPlus className="size-[18px]" strokeWidth={1.6} aria-hidden="true" />{text({ en: "Find people", fr: "Trouver des gens" })}</button>
      <button type="button" onClick={() => goWithParams(routes.analytics)} className="inline-flex min-h-[46px] items-center gap-2 rounded-full bg-[#1d4ed8] px-6 text-[15px] font-medium text-white hover:bg-[#1e40af] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff] focus-visible:ring-offset-2"><BarChart3 className="size-[18px]" strokeWidth={1.6} aria-hidden="true" />{text({ en: "Analytics", fr: "Stats" })}</button>
      <button type="button" onClick={() => goWithParams(routes.history)} className="inline-flex min-h-[46px] items-center gap-2 rounded-full border border-[#18181b] px-6 text-[15px] font-medium text-black hover:bg-[#f7f8fa] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff] focus-visible:ring-offset-2"><HistoryIcon className="size-[18px]" strokeWidth={1.6} aria-hidden="true" />{text({ en: "History", fr: "Historique" })}</button>
      </div>
      </div>

      <button
        type="button"
        onClick={() => goWithParams(routes.analytics)}
        className="mt-6 flex w-full flex-wrap items-center gap-4 rounded-[22px] p-6 text-left text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff] focus-visible:ring-offset-2"
        style={{ background: "linear-gradient(120deg,#0b1e4b,#1d4ed8 60%,#0ea5e9)" }}
      >
      <span className="grid size-12 shrink-0 place-items-center rounded-full bg-white/15"><BarChart3 className="size-6" strokeWidth={1.6} aria-hidden="true" /></span>
      <span className="min-w-0 flex-1">
      <span className="block text-[20px] font-bold tracking-tight">{text({ en: "Results at a glance", fr: "Vos résultats en bref" })}</span>
      <span className="mt-1 block text-[14px] text-white/85">{
            overview
              ? `${overview.replies} ${text({ en: "replies", fr: "réponses" })} · ${overview.toCheck} ${text({ en: "to review", fr: "à vérifier" })}. ${text({ en: "See details.", fr: "Voir les détails." })}`
              : overviewState === "loading"
                ? text({ en: "Loading your results…", fr: "Chargement de vos résultats…" })
                : text({ en: "424 replies · 3 to review. See charts and details.", fr: "424 réponses · 3 à vérifier. Voir les détails." })
          }</span>
      </span>
      <span className="inline-flex min-h-[46px] items-center gap-2 rounded-full bg-white px-6 text-[15px] font-semibold text-black">
          {text({ en: "Open analytics", fr: "Voir les stats" })}<ArrowRight className="size-[18px]" strokeWidth={1.8} aria-hidden="true" />
      </span>
      </button>

      <h2 id="choose-test" className="mt-12 scroll-mt-6 text-[28px] font-bold tracking-[-0.02em] text-black">{text({ en: "Choose a test", fr: "Choisir un test" })}</h2>
      <p className="mt-3 max-w-[72ch] text-[16px] leading-relaxed text-[#6d6d70]">{text({ en: "Pick a template to start. We check consent and images before you share.", fr: "Choisissez un modèle. On vérifie tout avant de partager." })}</p>
      <div className="mt-8 grid gap-6 sm:grid-cols-2 xl:grid-cols-4">
        {testTypes.map((test) => (
      <button key={test.key} type="button" onClick={() => test.method === "recruit" ? goWithParams(routes.recruit) : setSelectedTest(test)} aria-label={text(test.title)} className="group rounded-[14px] border border-[#e4e4e7] bg-[#fafafa] p-4 text-left transition-shadow hover:shadow-[0_18px_45px_-28px_rgba(24,24,27,0.45)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff]">
      <span className="block overflow-hidden rounded-[10px] border border-[#e9e9ec] bg-white"><span className="block aspect-[16/10] w-full p-3"><test.Art /></span></span>
      <span className="mt-5 flex items-baseline justify-between gap-3 px-1">
      <span className="flex items-center gap-1.5 text-[19px] font-bold text-black">{text(test.title)}{"star" in test && test.star && <Sparkles className="size-4 text-[#1d4ed8]" aria-hidden="true" />}</span>
      <span className="text-[12px] font-medium uppercase tracking-wide text-[#6d6d70]">{test.method === "five_second" ? "5 second test" : "Easy start"}</span>
      </span>
      <span className="mt-2 block px-1 pb-1 text-[14.5px] leading-[1.6] text-[#6d6d70]">{text(test.body)}</span>
      </button>
        ))}
      </div>
      {welcome && <WelcomeDialog open workspaceName={workspaceName} onGoToDashboard={dismissWelcome} />}
      <TestSettingsDialog open={selectedTest !== null} test={selectedTest} onClose={() => setSelectedTest(null)} onCreate={({ name, language, project, device, custom }) => { const method = selectedTest?.method ?? "survey.single"; setSelectedTest(null); goWithParams(withQuery(routes.newStudy, { method, name, lang: language, project, device, custom: JSON.stringify(custom) })); }} />
      </WorkspaceShell>
  );
}
