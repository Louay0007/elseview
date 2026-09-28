import { useRef, useState, type KeyboardEvent } from "react";
import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { BellRing, Check, ClipboardCheck, FileText, Stethoscope, type LucideIcon } from "lucide-react";

gsap.registerPlugin(ScrollTrigger, useGSAP);

interface WorkflowStep {
  title: string;
  description: string;
  result: string;
  icon: LucideIcon;
}

const steps: WorkflowStep[] = [
  { title: "Frame a question", description: "Choose a product assumption or user need to investigate.", result: "Question framed", icon: BellRing },
  { title: "Outline a study", description: "Define the audience, tasks, and evidence you need.", result: "Study outlined", icon: FileText },
  { title: "Explore a test", description: "Preview AI-assisted tasks and simulated observations.", result: "Test explored", icon: Stethoscope },
  { title: "Review findings", description: "Question sample insights and identify gaps in the evidence.", result: "Findings reviewed", icon: Check },
  { title: "Plan what’s next", description: "Choose what to validate next with real participants.", result: "Next step chosen", icon: ClipboardCheck },
];

export function WorkflowSection() {
  const sectionRef = useRef<HTMLElement>(null);
  const buttonRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const [activeStep, setActiveStep] = useState(0);

  useGSAP(() => {
    const section = sectionRef.current;
    if (!section) return;

    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const heading = section.querySelector<HTMLElement>("[data-workflow-heading]");
    const intro = section.querySelector<HTMLElement>("[data-workflow-intro]");
    const cards = gsap.utils.toArray<HTMLElement>("[data-workflow-step]", section);
    const rail = section.querySelector<HTMLElement>("[data-workflow-rail]");
    const targets = [heading, intro, ...cards].filter(Boolean);

    gsap.set(targets, { autoAlpha: 0 });
    gsap.set(heading, { y: reducedMotion ? 0 : 14 });
    gsap.set(cards, { y: reducedMotion ? 0 : 18 });
    gsap.set(rail, { scaleX: 0, transformOrigin: "left center" });

    const timeline = gsap.timeline({
      scrollTrigger: { trigger: section, start: "top 74%", once: true },
    });

    timeline
      .to(heading, { autoAlpha: 1, y: 0, duration: reducedMotion ? 0.22 : 0.55, ease: "power2.out" })
      .to(intro, { autoAlpha: 1, duration: 0.35, ease: "power1.out" }, "-=0.25")
      .to(rail, { scaleX: 1, duration: reducedMotion ? 0.3 : 0.9, ease: "power3.inOut" }, "-=0.12")
      .to(cards, { autoAlpha: 1, y: 0, duration: reducedMotion ? 0.22 : 0.48, stagger: reducedMotion ? 0.025 : 0.09, ease: "power3.out" }, "-=0.56");
  }, { scope: sectionRef });

  const selectStep = (index: number, moveFocus = false) => {
    setActiveStep(index);
    if (moveFocus) buttonRefs.current[index]?.focus();
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    let nextIndex: number | null = null;
    if (event.key === "ArrowRight" || event.key === "ArrowDown") nextIndex = (index + 1) % steps.length;
    if (event.key === "ArrowLeft" || event.key === "ArrowUp") nextIndex = (index - 1 + steps.length) % steps.length;
    if (event.key === "Home") nextIndex = 0;
    if (event.key === "End") nextIndex = steps.length - 1;
    if (nextIndex !== null) {
      event.preventDefault();
      selectStep(nextIndex, true);
    }
  };

  const progress = `${(activeStep / (steps.length - 1)) * 100}%`;

  return (
    <section ref={sectionRef} id="how-it-works" aria-labelledby="workflow-heading" className="relative overflow-hidden bg-white py-24 font-sans sm:py-28 lg:py-32">
      <div className="bluecrest-container relative">
        <div className="mx-auto max-w-[850px] text-center">
          <div data-workflow-heading>
            <p className="text-[12px] font-semibold uppercase tracking-[0.2em] text-[#0a84ff]">How Elseview works</p>
            <h2 id="workflow-heading" className="mt-5 text-[38px] font-semibold leading-[1.04] tracking-[-0.05em] text-[#18181b] sm:text-[45px] lg:text-[52px]">
              Less wondering. A clearer next step.
            </h2>
          </div>
          <p data-workflow-intro className="mx-auto mt-5 max-w-[650px] text-[16px] leading-[1.65] tracking-[-0.015em] text-[#62646a] sm:text-[17px]">
            From the question on your mind to the next test on your roadmap. Explore five stages of the concept below; selecting a step won’t launch a live study.
          </p>
        </div>

        <div className="relative mx-auto mt-14 max-w-[1180px] lg:mt-20">
          <div data-workflow-rail className="absolute left-[10%] right-[10%] top-6 hidden h-px bg-[#dce9f8] md:block" aria-hidden="true">
            <div className="h-full bg-[#0a84ff] transition-[width] duration-700 [transition-timing-function:cubic-bezier(.22,1,.36,1)]" style={{ width: progress }} />
          </div>

          <ol className="relative grid gap-3 md:grid-cols-5 md:gap-3 lg:gap-4" aria-label="Elseview illustrative research workflow">
            {steps.map((step, index) => {
              const Icon = step.icon;
              const isActive = index === activeStep;
              const isComplete = index < activeStep;

              return (
                <li key={step.title} data-workflow-step className="relative md:pt-12">
                  <button
                    ref={(element) => { buttonRefs.current[index] = element; }}
                    type="button"
                    onClick={() => selectStep(index)}
                    onKeyDown={(event) => handleKeyDown(event, index)}
                    aria-current={isActive ? "step" : undefined}
                    aria-label={`Step ${index + 1} of ${steps.length}: ${step.title}`}
                    className={`group relative min-h-[154px] w-full overflow-hidden rounded-[18px] border px-5 py-5 text-left transition-[transform,border-color,background-color,box-shadow] duration-500 [transition-timing-function:cubic-bezier(.22,1,.36,1)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff] focus-visible:ring-offset-4 md:min-h-[234px] md:px-4 md:py-6 lg:min-h-[220px] lg:p-6 ${isActive ? "-translate-y-1 border-[#0a84ff] bg-[#f2f8ff] shadow-[0_18px_48px_-30px_rgba(10,132,255,.6)]" : "border-[#e4e4e7] bg-white hover:-translate-y-1 hover:border-[#b9d9fb] hover:shadow-[0_16px_40px_-34px_rgba(24,24,27,.5)]"}`}
                  >
                    <span className={`absolute inset-x-0 top-0 h-[3px] origin-left bg-[#0a84ff] transition-transform duration-500 ${isActive ? "scale-x-100" : "scale-x-0"}`} aria-hidden="true" />
                    <span className="flex items-start justify-between gap-4">
                      <span className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-full border transition-[transform,color,background-color,border-color] duration-500 ${isActive ? "scale-105 border-[#0a84ff] bg-[#0a84ff] text-white" : isComplete ? "border-[#a9d3ff] bg-[#eaf4ff] text-[#0a84ff]" : "border-[#dfe4ea] bg-white text-[#5f6268] group-hover:border-[#a9d3ff] group-hover:text-[#0a84ff]"}`}>
                        {isComplete ? <Check aria-hidden="true" className="h-5 w-5" strokeWidth={2} /> : <Icon aria-hidden="true" className="h-5 w-5" strokeWidth={1.8} />}
                      </span>
                      <span className={`pt-1 text-[11px] font-semibold tracking-[0.14em] ${isActive || isComplete ? "text-[#0a84ff]" : "text-[#a0a2a7]"}`}>0{index + 1}</span>
                    </span>
                    <span className="mt-5 block text-[18px] font-semibold leading-[1.2] tracking-[-0.025em] text-[#202124]">{step.title}</span>
                    <span className="mt-2.5 block text-[14px] leading-[1.55] tracking-[-0.01em] text-[#686b70]">{step.description}</span>
                    <span className={`mt-4 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.1em] transition-[opacity,transform,color] duration-500 ${isActive ? "translate-y-0 text-[#0a84ff] opacity-100" : isComplete ? "translate-y-0 text-[#6f7680] opacity-100" : "translate-y-1 text-[#a0a2a7] opacity-0 group-hover:translate-y-0 group-hover:opacity-100"}`}>
                      <span className={`h-1.5 w-1.5 rounded-full ${isActive ? "animate-pulse bg-[#0a84ff]" : "bg-[#83bfff]"}`} aria-hidden="true" />
                      {isActive ? "Current focus" : isComplete ? step.result : "Explore step"}
                    </span>
                  </button>

                  <div className="absolute bottom-[-14px] left-[22px] top-[50px] w-px bg-[#dce9f8] md:hidden" aria-hidden="true">
                    {index < steps.length - 1 && <div className={`w-full origin-top bg-[#0a84ff] transition-transform duration-500 ${isComplete ? "scale-y-100" : "scale-y-0"}`} style={{ height: "calc(100% + 14px)" }} />}
                  </div>
                </li>
              );
            })}
          </ol>

          <p className="mt-6 text-center text-[12px] tracking-[0.02em] text-[#85878c]">Select a step · Use arrow keys to move through the workflow</p>
        </div>
      </div>
    </section>
  );
}
