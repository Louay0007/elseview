"use client";

import { useRef } from "react";
import { Building2, CheckCircle2, ClipboardList, HeartPulse, Stethoscope, UsersRound } from "lucide-react";
import { AnimatedBeam, Circle } from "@/components/ui/animated-beam";
import { cn } from "@/lib/utils";

export function MediterraAnimatedNetwork({ className }: { className?: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const patientRef = useRef<HTMLDivElement>(null);
  const mediterraRef = useRef<HTMLDivElement>(null);
  const specialistRef = useRef<HTMLDivElement>(null);
  const contextRef = useRef<HTMLDivElement>(null);
  const careTeamRef = useRef<HTMLDivElement>(null);
  const hospitalRef = useRef<HTMLDivElement>(null);
  const outcomeRef = useRef<HTMLDivElement>(null);

  const outputs = [
    { ref: specialistRef, label: "Research question", icon: Stethoscope },
    { ref: contextRef, label: "Study context", icon: ClipboardList },
    { ref: careTeamRef, label: "User feedback", icon: UsersRound },
    { ref: hospitalRef, label: "Product team", icon: Building2 },
    { ref: outcomeRef, label: "Next experiment", icon: CheckCircle2 },
  ];

  return (
    <section id="connected-care" aria-labelledby="connected-care-heading" className="bg-white py-24 sm:py-28">
      <div className="bluecrest-container">
        <div className="mx-auto mb-10 max-w-[620px] text-center">
          <p className="text-[12px] font-semibold uppercase tracking-[0.2em] text-[#0a84ff]">The Elseview concept</p>
          <h2 id="connected-care-heading" className="mt-4 text-[34px] font-semibold leading-[1.06] tracking-[-0.045em] text-[#18181b] sm:text-[44px]">
            Connect the dots. See what’s missing.
          </h2>
          <p className="mx-auto mt-4 max-w-[540px] text-[16px] leading-[1.6] text-[#666a70]">
            A question is only the beginning. This concept shows how user feedback, study context, and AI-assisted analysis could come together to guide your next experiment.
          </p>
        </div>

        <div
          ref={containerRef}
          className={cn(
            "relative mx-auto flex min-h-[400px] w-full max-w-[920px] items-center justify-center overflow-hidden bg-white px-2 py-8 sm:min-h-[480px] sm:px-8 lg:px-12",
            className,
          )}
        >
          <div className="flex h-full w-full flex-row items-stretch justify-between gap-12 sm:gap-20 lg:gap-28">
            <div className="flex flex-col justify-center">
              <Circle ref={patientRef} label="Product question" className="size-14 sm:size-16">
                <HeartPulse aria-hidden="true" className="size-6 sm:size-7" strokeWidth={1.8} />
              </Circle>
            </div>

            <div className="flex flex-col justify-center">
              <Circle ref={mediterraRef} label="Elseview" className="size-24 rounded-none border-0 p-0 shadow-none sm:size-28">
                <img src="/images/brand/elseview-logo.png" width={512} height={512} alt="" className="size-full object-contain" />
              </Circle>
            </div>

            <div className="flex flex-col justify-center gap-3 sm:gap-4">
              {outputs.map(({ ref, label, icon: Icon }) => (
                <Circle key={label} ref={ref} label={label} className="size-12 p-2 sm:size-14">
                  <Icon aria-hidden="true" className="size-5 sm:size-6" strokeWidth={1.8} />
                </Circle>
              ))}
            </div>
          </div>

          <AnimatedBeam containerRef={containerRef} fromRef={patientRef} toRef={mediterraRef} duration={3.2} />
          {outputs.map(({ ref, label }, index) => (
            <AnimatedBeam key={label} containerRef={containerRef} fromRef={mediterraRef} toRef={ref} duration={3.2} delay={0.65 + index * 0.18} />
          ))}
        </div>
      </div>
    </section>
  );
}
