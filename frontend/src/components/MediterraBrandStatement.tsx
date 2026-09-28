import { useRef } from "react";
import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger, useGSAP);

const statement =
  "Behind every better product is a moment of understanding. Elseview is built around that belief: ask sharper questions, challenge the obvious, and never lose sight of the people you’re building for.";
const statementWords = statement.split(" ");

export function MediterraBrandStatement() {
  const sectionRef = useRef<HTMLElement>(null);

  useGSAP(
    () => {
      const section = sectionRef.current;
      if (!section) return;

      const words = gsap.utils.toArray<HTMLElement>("[data-statement-word]", section);
      const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

      gsap.set(words, {
        autoAlpha: 0,
        y: reducedMotion ? 0 : 18,
        filter: reducedMotion ? "none" : "blur(5px)",
      });

      gsap.to(words, {
        autoAlpha: 1,
        y: 0,
        filter: "blur(0px)",
        duration: reducedMotion ? 0.18 : 0.5,
        stagger: reducedMotion ? 0.008 : 0.035,
        ease: "power2.out",
        scrollTrigger: {
          trigger: section,
          start: "top 72%",
          toggleActions: "play none none reverse",
        },
      });
    },
    { scope: sectionRef },
  );

  return (
    <section
      ref={sectionRef}
      id="about-mediterra"
      aria-labelledby="brand-statement-heading"
      className="relative z-30 overflow-hidden bg-white py-24 font-sans sm:py-32 lg:py-40"
    >
      <div className="bluecrest-container grid items-center gap-14 lg:grid-cols-[0.8fr_1.2fr] lg:gap-20">
        <div className="flex items-center justify-center lg:justify-start">
          <div className="flex flex-col items-center gap-5">
            <img
              src="/images/brand/elseview-logo.png"
              width="512"
              height="512"
              alt="Elseview logo"
              className="size-56 object-contain sm:size-72 lg:size-80"
              loading="lazy"
              decoding="async"
            />
            <h2
              id="brand-statement-heading"
              className="text-center text-3xl font-semibold tracking-[-0.05em] text-[#07172f] sm:text-4xl"
            >
              Elseview.
            </h2>
          </div>
        </div>

        <div className="flex justify-center">
          <p
            className="max-w-[26ch] text-center text-[clamp(2rem,4.2vw,4.5rem)] font-medium leading-[1.04] tracking-[-0.05em] text-[#07172f]"
          >
            <span className="sr-only">{statement}</span>
            {statementWords.map((word, index) => (
              <span
                key={`${word}-${index}`}
                data-statement-word
                aria-hidden="true"
                className="inline-block will-change-transform"
              >
                {word}{index < statementWords.length - 1 ? "\u00a0" : ""}
              </span>
            ))}
          </p>
        </div>
      </div>
    </section>
  );
}
