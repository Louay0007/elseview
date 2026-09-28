import { useEffect, useState } from "react";
import { LogoCarousel } from "@/components/LogoCarousel";
import { RoleSelectionDialog } from "@/components/RoleSelectionDialog";
import { Seo } from "@/components/Seo";
import { MediterraFaq } from "@/components/MediterraFaq";
import { MediterraFooter } from "@/components/MediterraFooter";
import { MediterraMinimalistHero } from "@/components/MediterraMinimalistHero";
import { useOptionalAuthLocale } from "@/components/auth/AuthLocale";
import TestimonialMarquee from "@/components/ui/marquee-01";
import SmoothScroll from "@/components/ui/smooth-scroll";

const Index = () => {
  const [roleDialogOpen, setRoleDialogOpen] = useState(false);
  const { text } = useOptionalAuthLocale();

  useEffect(() => {
    const openRoleSelection = () => setRoleDialogOpen(true);
    window.addEventListener("elseview:open-role-selection", openRoleSelection);
    return () => window.removeEventListener("elseview:open-role-selection", openRoleSelection);
  }, []);

  return (
    <main id="top" className="min-h-screen bg-white">
      <Seo
        title={text({ en: "Elseview — User Research & AI-Powered Testing", fr: "Elseview — Recherche utilisateur & tests assistés par IA" })}
        description={text({
          en: "See beyond assumptions with Elseview. Explore user research, usability testing, and AI-assisted analysis to turn better questions into clearer product decisions.",
          fr: "Voyez au-delà des hypothèses avec Elseview. Explorez la recherche utilisateur, les tests d’utilisabilité et l’analyse assistée par IA pour transformer vos questions en décisions produit plus claires.",
        })}
      />
      <MediterraMinimalistHero />
      <RoleSelectionDialog open={roleDialogOpen} onOpenChange={setRoleDialogOpen} />
      <LogoCarousel />
      <SmoothScroll />
      <TestimonialMarquee />
      <MediterraFaq />
      <MediterraFooter />
    </main>
  );
};

export default Index;
