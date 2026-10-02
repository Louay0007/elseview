import { useState, type FormEvent } from "react";

import { RuixenGradientFooter } from "@/components/ui/ruixen-gradient-footer";
import { MediterraLogo } from "@/components/MediterraLogo";
import { useOptionalAuthLocale } from "@/components/auth/AuthLocale";
import { authRoute, routes } from "@/lib/routes";

export function MediterraFooter() {
  const [submitted, setSubmitted] = useState(false);
  const { text } = useOptionalAuthLocale();

  const columns = [
    { title: text({ en: "Research", fr: "Recherche" }), links: [{ label: text({ en: "Research principles", fr: "Principes de recherche" }), href: "#future-content" }] },
    { title: text({ en: "Explore", fr: "Explorer" }), links: [{ label: text({ en: "Use cases", fr: "Cas d’usage" }), href: "#testimonial-heading" }, { label: text({ en: "Questions", fr: "Questions" }), href: "#faq" }, { label: text({ en: "Back to top", fr: "Haut de page" }), href: "#top" }] },
    { title: text({ en: "Company", fr: "Société" }), links: [{ label: text({ en: "Start as researcher", fr: "Commencer chercheur" }), href: authRoute("signup", "researcher") }, { label: text({ en: "Join as tester", fr: "Rejoindre testeur" }), href: authRoute("signup", "tester") }, { label: text({ en: "Sign in", fr: "Se connecter" }), href: routes.login }] },
    { title: text({ en: "Pricing", fr: "Tarifs" }), links: [{ label: text({ en: "Buy credits", fr: "Acheter des crédits" }), href: routes.buyCredits }, { label: text({ en: "How credits work", fr: "Comprendre les crédits" }), href: routes.buyCredits }] },
    { title: text({ en: "Information", fr: "Informations" }), links: [{ label: text({ en: "Data guidance", fr: "Guide des données" }), href: "#faq" }, { label: text({ en: "Preview limits", fr: "Limites de l’aperçu" }), href: "#faq" }, { label: text({ en: "AI guidance", fr: "Guide IA" }), href: "#faq" }] },
  ];

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitted(true);
  };

  return (
    <RuixenGradientFooter
      gradientHeight="40vh"
      className="relative z-30 bg-white font-sans text-[#07172f]"
    >
      <div className="bluecrest-container pt-20 sm:pt-24 lg:pt-28">
        <p className="pb-20 text-center text-xs font-semibold uppercase tracking-[0.18em] text-[#07172f]/48 sm:pb-28">
          {text({ en: "Scroll to reveal the horizon", fr: "Faites défiler pour révéler l’horizon" })}
          <span aria-hidden="true" className="ml-2">↓</span>
        </p>

        <div className="grid gap-12 pb-12 sm:grid-cols-2 lg:grid-cols-6 lg:gap-10">
          <div className="sm:col-span-2 lg:col-span-2">
            <a
              href="#top"
              aria-label="Elseview home"
              className="bluecrest-focus inline-flex min-h-11 items-center gap-2 text-[#07172f]"
            >
              <MediterraLogo />
            </a>
            <p className="mt-4 max-w-xs text-sm leading-relaxed text-[#07172f]/58">
              {text({ en: "A fresh perspective on your next big idea. Explore Elseview’s vision for user research and AI-powered testing in this product preview.", fr: "Un regard neuf sur votre prochaine grande idée. Explorez la vision d’Elseview pour la recherche utilisateur et les tests assistés par IA dans cet aperçu produit." })}
            </p>

            <form onSubmit={handleSubmit} className="mt-6 max-w-sm" aria-label={text({ en: "Elseview email form demo", fr: "Démo du formulaire e-mail Elseview" })}>
              <div className="flex gap-2">
                <label htmlFor="footer-email" className="sr-only">{text({ en: "Email address (demo only)", fr: "Adresse e-mail (démo uniquement)" })}</label>
                <input
                  id="footer-email"
                  type="email"
                  required
                  onChange={() => setSubmitted(false)}
                  aria-describedby="footer-email-status"
                  placeholder={text({ en: "Email address (demo)", fr: "Adresse e-mail (démo)" })}
                  className="h-11 min-w-0 flex-1 rounded-md border border-[#07172f]/15 bg-transparent px-3 text-sm text-[#07172f] outline-none transition-colors placeholder:text-[#07172f]/38 focus:border-[#0a84ff] focus:ring-2 focus:ring-[#0a84ff]/20"
                />
                <button
                  type="submit"
                  className="h-11 shrink-0 rounded-md bg-[#07172f] px-4 text-xs font-semibold uppercase tracking-[0.12em] text-white transition-colors hover:bg-[#0a84ff] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff] focus-visible:ring-offset-2"
                >
                  {text({ en: "Try demo", fr: "Essayer la démo" })}
                </button>
              </div>
              <p
                id="footer-email-status"
                aria-live="polite"
                className="mt-2 min-h-5 text-xs text-[#07172f]/58"
              >
                {submitted ? text({ en: "Demo only. Your email was not saved or subscribed.", fr: "Démo uniquement. Votre e-mail n’a pas été enregistré ni abonné." }) : text({ en: "Demo form only. No subscription or email delivery.", fr: "Formulaire de démo uniquement. Ni abonnement ni envoi d’e-mail." })}
              </p>
            </form>
          </div>

          <nav
            aria-label={text({ en: "Footer navigation", fr: "Navigation de pied de page" })}
            className="grid grid-cols-2 gap-x-8 gap-y-10 text-xs uppercase tracking-[0.12em] sm:col-span-2 sm:grid-cols-4 lg:col-span-4"
          >
            {columns.map((column) => (
              <div key={column.title}>
                <h2 className="font-semibold text-[#07172f]">{column.title}</h2>
                <ul className="mt-4 flex flex-col gap-3">
                  {column.links.map((link) => (
                    <li key={link.label}>
                      <a
                        href={link.href}
                        className="bluecrest-focus inline-flex min-h-7 items-center text-[#07172f]/52 transition-colors hover:text-[#0a84ff]"
                      >
                        {link.label}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </nav>
        </div>

        <div className="flex flex-col items-center justify-between gap-4 border-t border-[#07172f]/10 pb-3 pt-6 text-xs uppercase tracking-[0.1em] text-[#07172f]/52 sm:flex-row">
          <span>© 2026 Elseview</span>
          <span className="flex items-center gap-2 text-[#07172f]/62">
            <span aria-hidden="true" className="size-1.5 rounded-full bg-[#30d158]" />
            {text({ en: "Preview · Not a live service", fr: "Aperçu · Pas un service en production" })}
          </span>
          <span>{text({ en: "Stay curious. Build with purpose.", fr: "Restez curieux. Construisez avec intention." })}</span>
        </div>
      </div>
    </RuixenGradientFooter>
  );
}
