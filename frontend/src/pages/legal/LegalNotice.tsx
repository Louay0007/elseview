import { Link } from "react-router-dom";
import { useAuthLocale } from "@/components/auth/AuthLocale";
import { Seo } from "@/components/Seo";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { routes } from "@/lib/routes";

/**
 * A legal page whose text has not been written yet.
 *
 * Both the researcher and the tester footer link to terms and privacy, so
 * both need a destination. Inventing plausible-looking policy copy would be
 * worse than saying plainly that none exists, so this states the gap instead
 * and links back to a working screen.
 */
export default function LegalNotice({
  slug,
  title,
  body,
}: {
  slug: "terms" | "privacy";
  title: { en: string; fr: string };
  body: { en: string; fr: string };
}) {
  const { text } = useAuthLocale();

  return (
    <main className="flex min-h-dvh flex-col bg-white text-[#18181b]">
      <Seo title={text(title)} description={text(body)} />

      <header className="bg-black text-white">
        <div className="mx-auto flex w-full max-w-[1440px] items-center gap-3 px-6 py-3.5 sm:gap-5">
          <Link
            to={routes.landing}
            aria-label="Elseview home"
            className="flex shrink-0 items-center gap-2.5 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
          >
            <img
              src="/images/brand/elseview-logo-white.png"
              alt=""
              aria-hidden="true"
              className="h-9 w-9 object-contain"
            />
            <span className="text-[24px] font-bold tracking-tight text-white">Elseview</span>
          </Link>
          <span className="flex-1" />
          <LanguageSwitcher />
        </div>
      </header>

      <section className="mx-auto w-full max-w-[720px] flex-1 px-6 py-16">
        <h1 className="text-[32px] font-bold tracking-tight text-black">{text(title)}</h1>
        <p className="mt-4 rounded-[18px] border border-[#e4e4e7] bg-[#fafafa] p-5 text-[16px] leading-7 text-[#3a3a3c]">
          {text(body)}
        </p>
        <Link
          to={routes.landing}
          className="mt-8 inline-flex min-h-[44px] items-center rounded-full border border-[#e4e4e7] px-5 text-[14px] font-medium text-black hover:bg-[#f7f8fa] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff]"
        >
          {text({ en: "Back to Elseview", fr: "Retour à Elseview" })}
        </Link>
      </section>

      <footer className="bg-[#f5f5f6] px-6 py-[18px] text-[14px] text-[#3a3a3c]">
        <p className="mx-auto max-w-[1440px]">
          {text({ en: "© 2026 Elseview. All rights reserved.", fr: "© 2026 Elseview. Tous droits réservés." })}
        </p>
      </footer>
    </main>
  );
}

/** The two live legal destinations, defined once and routed by slug. */
export const legalPages = {
  terms: {
    title: { en: "Terms of use", fr: "Conditions d'utilisation" },
    body: {
      en: "These terms have not been published yet. Ask your workspace owner for the current terms before you use the product.",
      fr: "Ces conditions ne sont pas encore publiées. Demandez les conditions actuelles à votre propriétaire d'espace avant d'utiliser le produit.",
    },
  },
  privacy: {
    title: { en: "Privacy policy", fr: "Politique de confidentialité" },
    body: {
      en: "This policy has not been published yet. Ask your workspace owner for the current policy before you use the product.",
      fr: "Cette politique n'est pas encore publiée. Demandez la politique actuelle à votre propriétaire d'espace avant d'utiliser le produit.",
    },
  },
} satisfies Record<string, { title: { en: string; fr: string }; body: { en: string; fr: string } }>;