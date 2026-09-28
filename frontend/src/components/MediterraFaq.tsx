import { useRef } from "react";
import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { useOptionalAuthLocale } from "@/components/auth/AuthLocale";

gsap.registerPlugin(ScrollTrigger, useGSAP);

const faqsEn = [
  { question: "What is Elseview?", answer: "Elseview is a product concept for user research and AI-powered testing. The available app is an interactive preview with sample data, not a live research service." },
  { question: "Who is Elseview designed for?", answer: "The concept is for researchers, designers, product managers, and founders who want to understand user needs, explore product questions, and plan useful tests." },
  { question: "What can I explore in the preview?", answer: "Explore sign-in, account creation, email verification, password recovery, invitations and account settings. Workspace and session screens use demonstration data only. This frontend does not run live studies or collect participant responses." },
  { question: "Does AI testing replace research with people?", answer: "No. Simulated observations can help frame hypotheses, but they are not evidence of real user behavior. Validate important findings with real participants and human judgment." },
  { question: "Should I enter sensitive information?", answer: "No. Use fictional, non-sensitive information while exploring. Do not enter personal participant data, confidential research, credentials, or health information into this preview." },
  { question: "Are the findings and scenarios real?", answer: "No. Preview findings and landing-page scenarios are illustrative examples, not customer testimonials, measured outcomes, or results from completed research." },
  { question: "Do the displayed logos indicate available integrations?", answer: "No. The logos represent brands that trust Elseview, not a catalogue of available integrations." },
  { question: "How can I get started?", answer: "Create a researcher account to publish tests, or join as a tester to take tests. Then verify your email and complete your profile." },
];

const faqsFr = [
  { question: "Qu’est-ce qu’Elseview ?", answer: "Elseview est un concept produit pour la recherche utilisateur et les tests assistés par IA. L’application disponible est un aperçu interactif avec des données d’exemple, pas un service de recherche en production." },
  { question: "Pour qui Elseview est-il conçu ?", answer: "Le concept s’adresse aux chercheurs, designers, chefs de produit et fondateurs qui veulent comprendre les besoins utilisateurs, explorer des questions produit et planifier des tests utiles." },
  { question: "Que puis-je explorer dans l’aperçu ?", answer: "Explorez la connexion, la création de compte, la vérification e-mail, la récupération de mot de passe, les invitations et les paramètres. Les écrans d’espaces et de sessions utilisent des données de démonstration. Ce frontend ne lance pas d’études réelles ni ne collecte de réponses." },
  { question: "Les tests IA remplacent-ils la recherche avec des humains ?", answer: "Non. Les observations simulées aident à formuler des hypothèses, mais ne prouvent pas le comportement réel. Validez les résultats importants avec de vrais participants et un jugement humain." },
  { question: "Dois-je saisir des informations sensibles ?", answer: "Non. Utilisez des informations fictives et non sensibles. Ne saisissez ni données personnelles, ni recherches confidentielles, ni identifiants, ni informations de santé dans cet aperçu." },
  { question: "Les résultats et scénarios sont-ils réels ?", answer: "Non. Les résultats et scénarios de l’aperçu sont des exemples illustratifs, pas des témoignages clients, des résultats mesurés ou des recherches terminées." },
  { question: "Les logos affichés indiquent-ils des intégrations disponibles ?", answer: "Non. Les logos représentent des marques qui font confiance à Elseview, pas un catalogue d’intégrations disponibles." },
  { question: "Comment commencer ?", answer: "Créez un compte chercheur pour publier des tests, ou rejoignez comme testeur pour participer. Vérifiez ensuite votre e-mail et complétez votre profil." },
];

export function MediterraFaq() {
  const sectionRef = useRef<HTMLElement>(null);
  const { text, language } = useOptionalAuthLocale();
  const faqs = language === "fr" ? faqsFr : faqsEn;

  useGSAP(
    () => {
      const section = sectionRef.current;
      if (!section) return;

      const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      const heading = section.querySelector<HTMLElement>("[data-faq-heading]");
      const intro = section.querySelector<HTMLElement>("[data-faq-intro]");
      const items = gsap.utils.toArray<HTMLElement>("[data-faq-item]", section);
      const targets = [heading, intro, ...items].filter(Boolean);

      gsap.set(targets, { autoAlpha: 0, y: reducedMotion ? 0 : 12 });

      gsap
        .timeline({
          scrollTrigger: {
            trigger: section,
            start: "top 82%",
            once: true,
          },
        })
        .to(heading, {
          autoAlpha: 1,
          y: 0,
          duration: reducedMotion ? 0.2 : 0.4,
          ease: "power1.out",
        })
        .to(
          intro,
          {
            autoAlpha: 1,
            y: 0,
            duration: reducedMotion ? 0.2 : 0.35,
            ease: "power1.out",
          },
          "-=0.18",
        )
        .to(
          items,
          {
            autoAlpha: 1,
            y: 0,
            duration: reducedMotion ? 0.18 : 0.36,
            stagger: reducedMotion ? 0.02 : 0.055,
            ease: "power1.out",
          },
          "-=0.12",
        );
    },
    { scope: sectionRef },
  );

  return (
    <section
      ref={sectionRef}
      id="faq"
      aria-labelledby="faq-heading"
      className="relative overflow-hidden bg-white py-24 font-sans sm:py-28 lg:py-36"
    >
      <div className="bluecrest-container relative grid gap-14 lg:grid-cols-[minmax(17rem,0.72fr)_minmax(0,1.28fr)] lg:gap-24">
        <div className="lg:sticky lg:top-24 lg:self-start">
          <div data-faq-heading>
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#0a84ff]">
              {text({ en: "Frequently asked questions", fr: "Questions fréquentes" })}
            </p>
            <h2
              id="faq-heading"
              className="mt-5 max-w-[10ch] text-[clamp(3rem,5.4vw,6rem)] font-semibold leading-[0.94] tracking-[-0.06em] text-[#07172f]"
            >
              {text({ en: "Good questions. Straight answers.", fr: "Bonnes questions. Réponses claires." })}
            </h2>
          </div>
          <p
            data-faq-intro
            className="mt-7 max-w-md text-base leading-relaxed text-[#07172f]/65 sm:text-lg"
          >
            {text({ en: "Get to know Elseview: who it’s for, where AI fits, and exactly what you can explore in this preview.", fr: "Découvrez Elseview : pour qui, quelle place pour l’IA, et ce que vous pouvez explorer dans cet aperçu." })}
          </p>
        </div>

        <Accordion
          type="single"
          collapsible
          className="border-t border-[#07172f]/15"
        >
          {faqs.map((faq, index) => (
            <AccordionItem
              key={faq.question}
              value={`item-${index + 1}`}
              data-faq-item
              className="border-[#07172f]/15"
            >
              <AccordionTrigger className="min-h-20 gap-5 py-5 text-left text-[1.05rem] font-semibold leading-snug tracking-[-0.02em] text-[#07172f] hover:text-[#0a84ff] hover:no-underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff] focus-visible:ring-offset-4 focus-visible:ring-offset-white sm:min-h-24 sm:py-6 sm:text-xl [&>svg]:size-5 [&>svg]:text-[#0a84ff]">
                <span className="flex items-start gap-4 sm:gap-6">
                  <span className="mt-0.5 shrink-0 font-mono text-[0.68rem] font-semibold tracking-[0.14em] text-[#0a84ff] sm:mt-1">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  <span>{faq.question}</span>
                </span>
              </AccordionTrigger>
              <AccordionContent className="pb-7 pl-[2.7rem] pr-10 text-[0.98rem] leading-relaxed text-[#07172f]/68 sm:pb-8 sm:pl-[3.8rem] sm:pr-14 sm:text-base">
                {faq.answer}
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </div>
    </section>
  );
}
