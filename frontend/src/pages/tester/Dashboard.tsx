import { Link } from "react-router-dom";
import { ArrowUpRight, IdCard, Star } from "lucide-react";
import { useAuthLocale } from "@/components/auth/AuthLocale";
import { TesterShell, useTesterNav } from "@/components/tester/TesterShell";
import { PrototypeArt, CardSortingArt, PreferenceArt, TreeTestArt, SurveyArt, FiveSecondArt, FirstClickArt, SurveyMultiArt, SurveyRatingArt, SurveyTextArt, RankingArt, ConstantSumArt, A11yArt, LanguageArt } from "@/components/workspace/TestTypeArt";
import { mockTesterRating, mockTesterVerified } from "./testerMocks";
import { routes, withQuery } from "@/lib/routes";

/**
 * Practice exercises, one per researcher test type so a tester can meet every
 * method before real work arrives. They are simulated: they never affect rating
 * or earnings, which is why the section says so. `recruit` is deliberately
 * absent — it is a recruitment flow, not something a tester answers.
 */
const demos = [
  { key: "prototype", method: "prototype.task", Art: PrototypeArt, title: { en: "Prototype", fr: "Prototype" } },
  { key: "card", method: "card_sort", Art: CardSortingArt, title: { en: "Card sorting", fr: "Tri de cartes" } },
  { key: "preference", method: "preference", Art: PreferenceArt, title: { en: "Preference test", fr: "Test de préférence" } },
  { key: "tree", method: "tree_test", Art: TreeTestArt, title: { en: "Tree test", fr: "Test d’arborescence" } },
  { key: "survey", method: "survey.single", Art: SurveyArt, title: { en: "Survey", fr: "Enquête" } },
  { key: "five", method: "five_second", Art: FiveSecondArt, title: { en: "5 second test", fr: "Test 5 secondes" } },
  { key: "click", method: "first_click", Art: FirstClickArt, title: { en: "First click", fr: "Premier clic" } },
  { key: "survey-multi", method: "survey.multi", Art: SurveyMultiArt, title: { en: "Multi-choice survey", fr: "Enquête à choix multiple" } },
  { key: "survey-rating", method: "survey.rating", Art: SurveyRatingArt, title: { en: "Rating survey", fr: "Enquête par notation" } },
  { key: "survey-text", method: "survey.text", Art: SurveyTextArt, title: { en: "Free text survey", fr: "Enquête en texte libre" } },
  { key: "ranking", method: "survey.ranking", Art: RankingArt, title: { en: "Ranking", fr: "Classement" } },
  { key: "constant-sum", method: "survey.constant_sum", Art: ConstantSumArt, title: { en: "Constant sum", fr: "Répartition de points" } },
  { key: "a11y", method: "accessibility.issue", Art: A11yArt, title: { en: "Report a problem", fr: "Signaler un problème" } },
  { key: "language", method: "language.review", Art: LanguageArt, title: { en: "Check wording", fr: "Vérifier le texte" } },
] as const;

export default function TesterDashboard() {
  const { text } = useAuthLocale();
  const { go, displayName } = useTesterNav();

  return (
    <TesterShell>
      {!mockTesterVerified && (
        <p className="flex flex-wrap items-center gap-2 rounded-[14px] bg-[#efe9fb] px-4 py-3 text-[14px] text-[#3b2a63]">
          <IdCard className="size-[18px] shrink-0" strokeWidth={1.7} aria-hidden="true" />
          <span>{text({ en: "To access more tests and enable payouts, please ", fr: "Pour accéder à plus de tests et activer les paiements, " })}<Link to={routes.testerOnboarding} className="font-semibold underline underline-offset-2 hover:text-[#1E3A8A] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1E3A8A]">{text({ en: "verify now", fr: "vérifiez maintenant" })}</Link>{text({ en: ". Verification may take 3–5 mins. Please have your ID document ready.", fr: ". La vérification peut prendre 3 à 5 min. Préparez votre pièce d’identité." })}</span>
        </p>
      )}

      <h1 className="mt-6 text-[30px] font-bold tracking-[-0.02em] text-black">
        {text({ en: `Hey, ${displayName}!`, fr: `Salut, ${displayName} !` })}
      </h1>
      <p className="mt-2 max-w-[68ch] text-[16px] text-[#6d6d70]">
        {text({ en: "We don’t have any tests for you right now :( We’ll let you know when one becomes available.", fr: "Nous n’avons pas de test pour vous pour le moment :( Nous vous préviendrons dès qu’il y en aura un." })}
      </p>

      <hr className="mt-10 border-t border-[#e4e4e7]" />

      <div className="mt-10 text-center">
        <h2 className="text-[22px] font-bold tracking-tight text-black">{text({ en: "Practice using test demos", fr: "Entraînez-vous avec des démos" })}</h2>
        <p className="mx-auto mt-3 max-w-[68ch] text-[15px] leading-relaxed text-[#6d6d70]">
          {text({
            en: "To become familiar with how Elseview works while awaiting new tests, you can always practice with the demos below. These exercises are simulated and do not result in any compensation.",
            fr: "Pour vous familiariser avec Elseview en attendant de nouveaux tests, vous pouvez vous entraîner avec les démos ci-dessous. Ces exercices sont simulés et ne donnent lieu à aucune rémunération.",
          })}
        </p>
      </div>

      {/* Capping the row keeps exactly four cards per line and centres the trailing three. */}
      <ul className="mt-8 grid grid-cols-2 gap-4 sm:grid-cols-3 sm:gap-5 xl:grid-cols-4">
        {demos.map((demo) => (
          <li key={demo.key}>
            <article className="flex h-full flex-col rounded-[14px] border border-[#e4e4e7] bg-white p-3">
              <span className="block overflow-hidden rounded-[10px] border border-[#e9e9ec] bg-white">
                <span className="block aspect-[16/11] w-full p-2.5"><demo.Art /></span>
              </span>
              <div className="mt-3 flex flex-1 flex-col items-start justify-end gap-2">
                <h3 className="text-[15px] font-bold leading-tight text-black">{text(demo.title)}</h3>
                <button
                  type="button"
                  onClick={() => go(withQuery(routes.testerRunner, { demo: demo.method }))}
                  className="inline-flex min-h-[36px] w-full items-center justify-center gap-1 rounded-full bg-black px-3 text-[13px] font-semibold text-white transition hover:bg-[#1E3A8A] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff] focus-visible:ring-offset-2"
                >
                  {text({ en: "Start demo", fr: "Lancer la démo" })}
                  <ArrowUpRight className="size-4" strokeWidth={1.9} aria-hidden="true" />
                  <span className="sr-only">— {text(demo.title)}</span>
                </button>
              </div>
            </article>
          </li>
        ))}
      </ul>

      <div className="mt-12 flex flex-wrap items-center justify-center gap-x-10 gap-y-3 border-t border-[#e4e4e7] pt-8 text-center">
        <p className="flex items-center gap-2 text-[18px]">
          <Star className="size-[22px] shrink-0 text-[#3fbf6f]" strokeWidth={1.7} aria-hidden="true" />
          <span className="font-semibold text-[#3fbf6f]">{mockTesterRating}%</span>
          <span className="font-semibold text-black">{text({ en: "is your tester rating", fr: "est votre note de testeur" })}</span>
        </p>
        <p className="max-w-[46ch] text-[15px] leading-relaxed text-[#6d6d70]">
          {text({
            en: "Remember, your responses affect your rating, so ensure you answer accurately. The better your rating the more tests you will see.",
            fr: "Rappelez-vous que vos réponses influencent votre note : répondez avec précision. Meilleure est votre note, plus vous verrez de tests.",
          })}
        </p>
      </div>
    </TesterShell>
  );
}
