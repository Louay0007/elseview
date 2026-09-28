import { Card, CardContent } from "@/components/ui/card";
import { Marquee } from "@/components/ui/marquee-01-utils/marquee";
import { useOptionalAuthLocale } from "@/components/auth/AuthLocale";

type Review = { id: string; name: string; username: string; body: string; profile: string };

const reviewsEn: Review[] = [
  { id: "ken-masters-1", name: "First impressions", username: "Illustrative scenario", body: "Explore how a first-time visitor might interpret a product page. Use the scenario to frame questions for real participants, not to predict their answers.", profile: "https://cdn.21st.dev/assets/mirror/b5/b539abc60701ab9cbcd73f9241d13a14a09582a4fd06c65784cb5567d77a2e0e.webp" },
  { id: "kira-athrun-1", name: "Onboarding friction", username: "Illustrative scenario", body: "Outline a study of the first-run experience. Look for unclear instructions and moments worth investigating with people who are new to the product.", profile: "https://cdn.21st.dev/assets/mirror/2b/2bc5f22fa3400c61a2161d14e3dce5a0804badebfc1b3d9cbe844feaa3b72180.webp" },
  { id: "lirael-nassun", name: "Concept exploration", username: "Illustrative scenario", body: "Compare the assumptions behind two product ideas. AI-generated perspectives can suggest questions, but real users are needed to validate demand.", profile: "https://cdn.21st.dev/assets/mirror/e1/e1e172821860559f890ef5ef7c14cc66a6c1ec001f3bbeb6dddd349c0081dd6b.webp" },
  { id: "jessica", name: "Navigation clarity", username: "Illustrative scenario", body: "Plan tasks around finding key information. Review sample observations as an illustration of how to investigate a confusing navigation path.", profile: "https://cdn.21st.dev/assets/mirror/61/61fda783ca2662349458bad61a434038016f05d6a14bd7c5a314f48c8ee8be03.webp" },
  { id: "jenny", name: "Message testing", username: "Illustrative scenario", body: "Explore whether a value proposition is clear. Use this scenario to prepare a study, not as proof that a message will convert.", profile: "https://cdn.21st.dev/assets/mirror/c5/c5ee2e124ea7334450d30a46607f793534f567e97d4b708cda110a06aeed4953.webp" },
  { id: "kira-athrun-2", name: "Prototype feedback", username: "Illustrative scenario", body: "Frame a task-based review of an early prototype. Separate simulated friction from observations gathered in research with real participants.", profile: "https://cdn.21st.dev/assets/mirror/2b/2bc5f22fa3400c61a2161d14e3dce5a0804badebfc1b3d9cbe844feaa3b72180.webp" },
  { id: "ken-masters-2", name: "Research planning", username: "Illustrative scenario", body: "Turn a broad product question into a focused study outline. Identify the audience, tasks, and evidence needed before drawing conclusions.", profile: "https://cdn.21st.dev/assets/mirror/b5/b539abc60701ab9cbcd73f9241d13a14a09582a4fd06c65784cb5567d77a2e0e.webp" },
];

const reviewsFr: Review[] = [
  { id: "ken-masters-1", name: "Premières impressions", username: "Scénario illustratif", body: "Explorez comment un nouveau visiteur pourrait interpréter une page produit. Utilisez ce scénario pour préparer des questions pour de vrais participants, pas pour prédire leurs réponses.", profile: "https://cdn.21st.dev/assets/mirror/b5/b539abc60701ab9cbcd73f9241d13a14a09582a4fd06c65784cb5567d77a2e0e.webp" },
  { id: "kira-athrun-1", name: "Frictions d’onboarding", username: "Scénario illustratif", body: "Préparez une étude de la première utilisation. Repérez les instructions floues et les moments à explorer avec des personnes qui découvrent le produit.", profile: "https://cdn.21st.dev/assets/mirror/2b/2bc5f22fa3400c61a2161d14e3dce5a0804badebfc1b3d9cbe844feaa3b72180.webp" },
  { id: "lirael-nassun", name: "Exploration de concept", username: "Scénario illustratif", body: "Comparez les hypothèses derrière deux idées produit. Les perspectives générées par IA suggèrent des questions, mais seuls de vrais utilisateurs valident la demande.", profile: "https://cdn.21st.dev/assets/mirror/e1/e1e172821860559f890ef5ef7c14cc66a6c1ec001f3bbeb6dddd349c0081dd6b.webp" },
  { id: "jessica", name: "Clarté de navigation", username: "Scénario illustratif", body: "Planifiez des tâches autour de la recherche d’informations clés. Examinez des observations d’exemple pour enquêter sur un parcours confus.", profile: "https://cdn.21st.dev/assets/mirror/61/61fda783ca2662349458bad61a434038016f05d6a14bd7c5a314f48c8ee8be03.webp" },
  { id: "jenny", name: "Test de message", username: "Scénario illustratif", body: "Explorez si une proposition de valeur est claire. Utilisez ce scénario pour préparer une étude, pas comme preuve qu’un message convertira.", profile: "https://cdn.21st.dev/assets/mirror/c5/c5ee2e124ea7334450d30a46607f793534f567e97d4b708cda110a06aeed4953.webp" },
  { id: "kira-athrun-2", name: "Retours prototype", username: "Scénario illustratif", body: "Cadrez une revue d’un prototype précoce basée sur des tâches. Séparez les frictions simulées des observations recueillies avec de vrais participants.", profile: "https://cdn.21st.dev/assets/mirror/2b/2bc5f22fa3400c61a2161d14e3dce5a0804badebfc1b3d9cbe844feaa3b72180.webp" },
  { id: "ken-masters-2", name: "Planification de recherche", username: "Scénario illustratif", body: "Transformez une question produit large en plan d’étude ciblé. Identifiez l’audience, les tâches et les preuves nécessaires avant de conclure.", profile: "https://cdn.21st.dev/assets/mirror/b5/b539abc60701ab9cbcd73f9241d13a14a09582a4fd06c65784cb5567d77a2e0e.webp" },
];

function ReviewCard({ profile, name, username, body, scenarioLabel }: Review & { scenarioLabel: string }) {
  return (
    <Card
      role="article"
      aria-label={`${scenarioLabel}: ${name}`}
      className="relative h-full w-[min(21rem,calc(100vw-3rem))] shrink-0 overflow-hidden rounded-2xl border-[#07172f]/10 bg-white p-5 shadow-none transition-[border-color,box-shadow,transform] duration-300 hover:-translate-y-1 hover:border-[#0a84ff]/35 hover:shadow-[0_18px_45px_rgba(7,23,47,0.08)] sm:w-[22rem]"
    >
      <CardContent className="flex h-full flex-col gap-5 p-0">
        <div className="flex items-center gap-3">
          <img className="size-11 rounded-full object-cover ring-1 ring-[#07172f]/10" width="44" height="44" alt="" src={profile} loading="lazy" decoding="async" />
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-[#07172f]">{name}</p>
            <p className="truncate text-xs font-medium text-[#07172f]/55">{username}</p>
          </div>
        </div>
        <p className="text-[0.95rem] leading-relaxed text-[#07172f]/72">{body}</p>
      </CardContent>
    </Card>
  );
}

export default function TestimonialMarquee() {
  const { text, language } = useOptionalAuthLocale();
  const reviews = language === "fr" ? reviewsFr : reviewsEn;
  const firstRow = reviews.slice(0, Math.ceil(reviews.length / 2));
  const secondRow = reviews.slice(Math.ceil(reviews.length / 2));
  const scenarioLabel = text({ en: "Illustrative research scenario", fr: "Scénario de recherche illustratif" });
  return (
    <section aria-labelledby="testimonial-heading" className="relative z-20 overflow-hidden bg-white py-24 sm:py-28 lg:py-36">
      <div className="bluecrest-container mb-12 grid items-end gap-6 lg:grid-cols-[minmax(0,1fr)_24rem]">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#0a84ff]">{text({ en: "Research possibilities", fr: "Possibilités de recherche" })}</p>
          <h2 id="testimonial-heading" className="mt-5 max-w-[12ch] text-[clamp(2.8rem,6vw,6.5rem)] font-semibold leading-[0.94] tracking-[-0.06em] text-[#07172f]">
            {text({ en: "What’s between your idea and their experience?", fr: "Qu’y a-t-il entre votre idée et leur expérience ?" })}
          </h2>
        </div>
        <p className="max-w-md text-base leading-relaxed text-[#07172f]/62 sm:text-lg">
          {text({ en: "Illustrative use cases, not customer testimonials. Portraits are decorative; these examples do not describe real people or measured results.", fr: "Cas d’usage illustratifs, pas des témoignages clients. Les portraits sont décoratifs ; ces exemples ne décrivent ni de vraies personnes ni des résultats mesurés." })}
        </p>
      </div>
      <div className="relative flex w-full flex-col justify-center gap-2 overflow-hidden">
        <Marquee aria-label={text({ en: "Illustrative scenarios moving left", fr: "Scénarios illustratifs défilant vers la gauche" })} pauseOnHover className="[--duration:20s] [--gap:1rem]">
          {firstRow.map((review) => (<ReviewCard key={review.id} {...review} scenarioLabel={scenarioLabel} />))}
        </Marquee>
        <Marquee aria-label={text({ en: "Illustrative scenarios moving right", fr: "Scénarios illustratifs défilant vers la droite" })} reverse pauseOnHover className="[--duration:20s] [--gap:1rem]">
          {secondRow.map((review) => (<ReviewCard key={review.id} {...review} scenarioLabel={scenarioLabel} />))}
        </Marquee>
        <div className="pointer-events-none absolute inset-y-0 left-0 z-10 w-[clamp(2rem,12vw,12rem)] bg-gradient-to-r from-white via-white/80 to-transparent" />
        <div className="pointer-events-none absolute inset-y-0 right-0 z-10 w-[clamp(2rem,12vw,12rem)] bg-gradient-to-l from-white via-white/80 to-transparent" />
      </div>
    </section>
  );
}
