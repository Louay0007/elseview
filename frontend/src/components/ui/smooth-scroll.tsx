"use client";

import "lenis/dist/lenis.css";

import { ReactLenis } from "lenis/react";
import {
  ArrowUpRight,
  FileSearch,
  FlaskConical,
  IterationCw,
  Search,
  type LucideIcon,
} from "lucide-react";
import { forwardRef, type ComponentPropsWithoutRef } from "react";
import { useOptionalAuthLocale } from "@/components/auth/AuthLocale";

import { cn } from "@/lib/utils";

type SmoothScrollProps = ComponentPropsWithoutRef<"section">;
type PanelTone = "navy" | "light" | "blue";

type StoryPanel = {
  eyebrow: string;
  title: string;
  description: string;
  footnote: string;
  icon: LucideIcon;
  tone: PanelTone;
};

const panelsEn: StoryPanel[] = [
  {
    eyebrow: "01 / Understand",
    title: "Curiosity beats certainty.",
    description:
      "The most useful research starts with what you don’t know. Explore how a focused question can turn a strong hunch into a study worth running.",
    footnote: "Start with a question, not a conclusion.",
    icon: Search,
    tone: "light",
  },
  {
    eyebrow: "02 / Test",
    title: "More angles. Fewer blind spots.",
    description:
      "Use AI-powered testing to challenge your first take. Simulated findings can suggest what to investigate; they are not evidence of what real users think.",
    footnote: "AI-generated signals need human validation.",
    icon: FlaskConical,
    tone: "navy",
  },
  {
    eyebrow: "03 / Interpret",
    title: "Find the proof. Not just the pattern.",
    description:
      "A compelling insight should stand up to questions. Compare interpretations, look for missing context, and separate observations from assumptions. These sample insights illustrate a workflow, not measured results.",
    footnote: "Good insights invite scrutiny.",
    icon: FileSearch,
    tone: "blue",
  },
  {
    eyebrow: "04 / Continue",
    title: "Keep learning. Keep building.",
    description:
      "Every unanswered question is a place to begin again. Elseview’s concept connects planning, testing, and reflection so your next research question builds on the last.",
    footnote: "Let real people shape what comes next.",
    icon: IterationCw,
    tone: "light",
  },
];

const panelsFr: StoryPanel[] = [
  { eyebrow: "01 / Comprendre", title: "La curiosité bat la certitude.", description: "La recherche la plus utile commence par ce que vous ignorez. Explorez comment une question ciblée transforme une intuition en étude à mener.", footnote: "Commencez par une question, pas une conclusion.", icon: Search, tone: "light" },
  { eyebrow: "02 / Tester", title: "Plus d’angles. Moins d’angles morts.", description: "Utilisez les tests assistés par IA pour challenger votre première lecture. Les résultats simulés suggèrent quoi explorer ; ils ne prouvent pas ce que pensent les vrais utilisateurs.", footnote: "Les signaux IA exigent une validation humaine.", icon: FlaskConical, tone: "navy" },
  { eyebrow: "03 / Interpréter", title: "Trouvez la preuve. Pas juste le motif.", description: "Un insight convaincant doit résister aux questions. Comparez les interprétations, cherchez le contexte manquant et séparez observations et hypothèses. Ces exemples illustrent un flux, pas des résultats mesurés.", footnote: "Les bons insights invitent à l’examen.", icon: FileSearch, tone: "blue" },
  { eyebrow: "04 / Continuer", title: "Apprenez. Construisez.", description: "Chaque question sans réponse est un nouveau départ. Le concept Elseview relie planification, tests et réflexion pour que chaque question nourrisse la suivante.", footnote: "Laissez de vraies personnes façonner la suite.", icon: IterationCw, tone: "light" },
];

const toneStyles: Record<
  PanelTone,
  {
    section: string;
    grid: string;
    muted: string;
    border: string;
    icon: string;
  }
> = {
  navy: {
    section: "bg-[#07172f] text-white",
    grid:
      "bg-[linear-gradient(to_right,rgba(255,255,255,0.075)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.075)_1px,transparent_1px)]",
    muted: "text-white/65",
    border: "border-white/20",
    icon: "bg-white/10 text-white",
  },
  light: {
    section: "bg-white text-[#07172f]",
    grid:
      "bg-[linear-gradient(to_right,rgba(10,132,255,0.10)_1px,transparent_1px),linear-gradient(to_bottom,rgba(10,132,255,0.10)_1px,transparent_1px)]",
    muted: "text-[#07172f]/65",
    border: "border-[#07172f]/15",
    icon: "bg-[#0a84ff] text-white",
  },
  blue: {
    section: "bg-[#0a84ff] text-white",
    grid:
      "bg-[linear-gradient(to_right,rgba(255,255,255,0.12)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.12)_1px,transparent_1px)]",
    muted: "text-white/75",
    border: "border-white/25",
    icon: "bg-white text-[#0a84ff]",
  },
};

function MediterraPanel({ panel, index, total, returnLabel, scrollLabel }: { panel: StoryPanel; index: number; total: number; returnLabel: string; scrollLabel: string }) {
  const Icon = panel.icon;
  const styles = toneStyles[panel.tone];
  const headingId = `mediterra-story-${index + 1}`;

  return (
    <section
      aria-labelledby={headingId}
      className={cn(
        "sticky top-0 min-h-[100svh] w-full overflow-hidden rounded-t-[1.75rem] sm:rounded-t-[2.5rem]",
        styles.section,
      )}
      style={{ zIndex: index + 10 }}
    >
      <div
        aria-hidden="true"
        className={cn(
          "pointer-events-none absolute inset-0 bg-[size:54px_54px] [mask-image:radial-gradient(ellipse_78%_66%_at_50%_0%,#000_58%,transparent_100%)]",
          styles.grid,
        )}
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute left-1/2 top-0 h-[46rem] w-[46rem] -translate-x-1/2 -translate-y-2/3 rounded-full bg-white/10 blur-3xl"
      />

      <div className="bluecrest-container relative z-10 flex min-h-[100svh] flex-col justify-between py-8 sm:py-12 lg:py-14">
        <div className="flex items-center justify-between gap-6">
          <p className="text-[0.68rem] font-semibold uppercase tracking-[0.24em] sm:text-xs">
            {panel.eyebrow}
          </p>
          <div
            className={cn(
              "grid size-11 shrink-0 place-items-center rounded-full sm:size-12",
              styles.icon,
            )}
          >
            <Icon aria-hidden="true" className="size-5" strokeWidth={1.8} />
          </div>
        </div>

        <div className="grid items-end gap-8 py-12 lg:grid-cols-[minmax(0,1fr)_minmax(18rem,28rem)] lg:gap-16">
          <h2
            id={headingId}
            className="max-w-[12ch] text-[clamp(3rem,7.2vw,7.6rem)] font-semibold leading-[0.91] tracking-[-0.065em]"
          >
            {panel.title}
          </h2>
          <p
            className={cn(
              "max-w-[40rem] text-base leading-relaxed sm:text-lg lg:pb-2 lg:text-xl",
              styles.muted,
            )}
          >
            {panel.description}
          </p>
        </div>

        <div
          className={cn(
            "flex flex-col gap-5 border-t pt-5 text-sm sm:flex-row sm:items-center sm:justify-between",
            styles.border,
          )}
        >
          <p className={cn("max-w-md", styles.muted)}>{panel.footnote}</p>
          {index === total - 1 ? (
            <a
              href="#top"
              className="group inline-flex min-h-11 w-fit items-center gap-2 border-b border-[#07172f]/45 py-2 font-semibold text-[#07172f] transition-colors hover:border-[#07172f] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff] focus-visible:ring-offset-4 focus-visible:ring-offset-white"
            >
              {returnLabel}
              <ArrowUpRight
                aria-hidden="true"
                className="size-4 transition-transform duration-300 group-hover:-translate-y-0.5 group-hover:translate-x-0.5"
              />
            </a>
          ) : (
            <p className="font-mono text-xs uppercase tracking-[0.18em]">
              {scrollLabel}
            </p>
          )}
        </div>
      </div>
    </section>
  );
}

const Component = forwardRef<HTMLElement, SmoothScrollProps>(
  ({ className, id = "future-content", ...props }, ref) => {
    const { text, language } = useOptionalAuthLocale();
    const panels = language === "fr" ? panelsFr : panelsEn;
    const returnLabel = text({ en: "Return to the beginning", fr: "Retour au début" });
    const scrollLabel = text({ en: "Scroll to continue", fr: "Faites défiler pour continuer" });
    return (
      <ReactLenis root options={{ anchors: true, autoRaf: true, lerp: 0.085 }}>
        <section
          ref={ref}
          id={id}
          className={cn("relative isolate bg-white", className)}
          {...props}
        >
          <article aria-label={text({ en: "Elseview research principles", fr: "Principes de recherche Elseview" })}>
            {panels.map((panel, index) => (
              <MediterraPanel key={panel.eyebrow} panel={panel} index={index} total={panels.length} returnLabel={returnLabel} scrollLabel={scrollLabel} />
            ))}
          </article>
        </section>
      </ReactLenis>
    );
  },
);

Component.displayName = "SmoothScroll";

export default Component;
