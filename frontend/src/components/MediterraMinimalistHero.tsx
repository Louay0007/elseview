import { ClipboardList, Compass, MessageCircleQuestion } from "lucide-react";
import { MinimalistHero } from "@/components/ui/minimalist-hero";
import { MediterraLogo } from "@/components/MediterraLogo";
import { useOptionalAuthLocale } from "@/components/auth/AuthLocale";
import { authRoute } from "@/lib/routes";

export function MediterraMinimalistHero() {
  const { text } = useOptionalAuthLocale();
  const footerLinks = [
    { label: text({ en: "Explore research use cases", fr: "Explorer les cas d’usage" }), icon: ClipboardList, href: "#testimonial-heading" },
    { label: text({ en: "Questions about Elseview", fr: "Questions sur Elseview" }), icon: MessageCircleQuestion, href: "#faq" },
    { label: text({ en: "Research principles", fr: "Principes de recherche" }), icon: Compass, href: "#future-content" },
  ];
  return (
    <MinimalistHero
      logo={<MediterraLogo className="text-carbon" />}
      mainText={text({
        en: "Your next big idea deserves more than a hunch. Explore user research and AI-powered testing with Elseview: a product preview for challenging assumptions, spotting friction, and finding your next move.",
        fr: "Votre prochaine grande idée mérite mieux qu’une intuition. Explorez la recherche utilisateur et les tests assistés par IA avec Elseview : un aperçu produit pour challenger vos hypothèses, repérer les frictions et trouver votre prochaine étape.",
      })}
      readMoreLabel={text({ en: "Get started for free", fr: "Commencer gratuitement" })}
      readMoreLink={authRoute("signup", "researcher")}
      onCtaClick={() => window.dispatchEvent(new CustomEvent("elseview:open-role-selection"))}
      imageSrc="/images/hero/elseview-research-session.png"
      imageAlt={text({
        en: "Illustrative user research session: a participant explores a tablet while a researcher listens with a notebook.",
        fr: "Session de recherche utilisateur illustrative : un participant explore une tablette pendant qu’un chercheur écoute avec un carnet.",
      })}
      overlayText={{
        part1: text({ en: "see deeper.", fr: "voir plus loin." }),
        part2: text({ en: "build better.", fr: "construire mieux." }),
      }}
      footerLinks={footerLinks}
      locationText={text({ en: "Landing & authentication preview", fr: "Aperçu landing & authentification" })}
    />
  );
}
