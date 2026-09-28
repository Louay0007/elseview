import { useRef, type ReactNode } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";

gsap.registerPlugin(useGSAP);

export interface MinimalistHeroProps {
  logo: ReactNode;
  mainText: string;
  readMoreLabel: string;
  readMoreLink: string;
  onCtaClick?: () => void;
  imageSrc: string;
  imageAlt: string;
  overlayText: {
    part1: string;
    part2: string;
  };
  footerLinks: { label: string; icon: LucideIcon; href: string }[];
  locationText: string;
  className?: string;
}

const easing = [0.22, 1, 0.36, 1] as const;

export function MinimalistHero({
  logo,
  mainText,
  readMoreLabel,
  readMoreLink,
  onCtaClick,
  imageSrc,
  imageAlt,
  overlayText,
  footerLinks,
  locationText,
  className,
}: MinimalistHeroProps) {
  const hero = useRef<HTMLElement>(null);
  const heroCircle = useRef<HTMLDivElement>(null);
  const heroImage = useRef<HTMLImageElement>(null);
  const heroImageFade = useRef<HTMLDivElement>(null);
  const heroCopy = useRef<HTMLDivElement>(null);
  const reduceMotion = useReducedMotion();
  const initial = reduceMotion ? false : undefined;

  useGSAP(() => {
    const circle = heroCircle.current;
    const image = heroImage.current;
    const imageFade = heroImageFade.current;
    const copy = heroCopy.current;
    const headlineLines = gsap.utils.toArray<HTMLElement>("[data-hero-line]", hero.current);
    if (!circle || !image || !imageFade || !copy || headlineLines.length === 0) return;

    const travelDistance = Math.max(360, Math.min(window.innerHeight * 0.72, 680));
    const animatedElements = [circle, image, imageFade, copy, ...headlineLines];
    const timeline = gsap.timeline({ delay: 0.24 });

    timeline
      .set(animatedElements, { willChange: "transform, opacity" })
      .fromTo(
        circle,
        { autoAlpha: 0, scale: 0.14, y: 46 },
        {
          autoAlpha: 1,
          scale: 1,
          y: 0,
          duration: 1.35,
          ease: "expo.out",
          transformOrigin: "50% 50%",
        },
      )
      .fromTo(
        image,
        {
          autoAlpha: 0,
          y: travelDistance,
          scale: 0.88,
          rotate: 1.2,
          transformOrigin: "50% 100%",
        },
        {
          autoAlpha: 1,
          y: -18,
          scale: 1.012,
          rotate: -0.2,
          duration: 1.35,
          ease: "power3.out",
        },
        ">+=0.1",
      )
      .to(image, {
        y: 0,
        scale: 1,
        rotate: 0,
        duration: 0.35,
        ease: "power2.out",
      })
      .fromTo(
        imageFade,
        { autoAlpha: 0, y: 20 },
        { autoAlpha: 1, y: 0, duration: 0.55, ease: "power2.out" },
        "-=0.18",
      )
      .fromTo(
        headlineLines,
        { autoAlpha: 0, yPercent: 125, rotate: 5 },
        {
          autoAlpha: 1,
          yPercent: 0,
          rotate: 0,
          duration: 1,
          stagger: 0.18,
          ease: "power4.out",
          transformOrigin: "0% 100%",
        },
        ">+=0.08",
      )
      .fromTo(
        copy,
        { autoAlpha: 0, y: 28 },
        { autoAlpha: 1, y: 0, duration: 0.82, ease: "power3.out" },
        "-=0.4",
      )
      .set(animatedElements, { clearProps: "transform,willChange" });

    return () => timeline.kill();
  }, { scope: hero });

  return (
    <section
      ref={hero}
      className={cn(
        "relative flex min-h-[100svh] w-full flex-col overflow-hidden bg-white px-5 pb-6 pt-5 text-carbon sm:min-h-[760px] sm:px-8 sm:pb-8 sm:pt-7 md:h-[100svh] md:min-h-[720px] md:px-12 md:pb-9 md:pt-9",
        className,
      )}
      aria-labelledby="mediterra-hero-heading"
    >
      <header className="relative z-40 mx-auto flex w-full max-w-[1440px] items-center justify-between gap-3">
        <motion.a
          href="#top"
          initial={initial ?? { opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5, ease: easing }}
          className="bluecrest-focus rounded-md text-[20px] font-bold tracking-[-0.045em] text-carbon sm:text-[22px]"
          aria-label="Elseview home"
        >
          {logo}
        </motion.a>

        <div className="flex items-center gap-3">
          <LanguageSwitcher />
          {onCtaClick ? (
            <motion.button
              type="button"
              onClick={onCtaClick}
              initial={initial ?? { opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5, ease: easing }}
              className="bluecrest-focus inline-flex min-h-11 items-center justify-center rounded-full bg-[#07172f] px-5 text-[13px] font-semibold text-white transition-colors duration-200 hover:bg-[#0a2d5c]"
            >
              {readMoreLabel}
            </motion.button>
          ) : (
            <motion.a
              href={readMoreLink}
              initial={initial ?? { opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5, ease: easing }}
              className="bluecrest-focus inline-flex min-h-11 items-center justify-center rounded-full bg-[#07172f] px-5 text-[13px] font-semibold text-white transition-colors duration-200 hover:bg-[#0a2d5c]"
            >
              {readMoreLabel}
            </motion.a>
          )}
        </div>
      </header>

      <div className="relative z-10 mx-auto grid w-full max-w-[1440px] flex-1 grid-cols-1 items-center py-5 sm:py-7 md:grid-cols-[0.8fr_1.18fr_1fr] md:gap-3 md:py-0 lg:grid-cols-[0.78fr_1.15fr_1.07fr]">
        <div
          ref={heroCopy}
          data-hero-copy
          className="invisible order-3 z-20 mx-auto max-w-[350px] text-center opacity-0 md:order-1 md:mx-0 md:max-w-[300px] md:text-left"
        >
          <p className="text-[16px] leading-[1.65] tracking-[-0.012em] text-carbon/68 md:text-[14px] lg:text-[15px]">
            {mainText}
          </p>
          {onCtaClick ? (
            <button
              type="button"
              onClick={onCtaClick}
              className="bluecrest-focus mt-4 inline-block rounded-sm border-b border-carbon pb-0.5 text-[13px] font-semibold tracking-[-0.01em] text-carbon transition-colors hover:border-signal-blue hover:text-signal-blue"
            >
              {readMoreLabel}
            </button>
          ) : (
            <a
              href={readMoreLink}
              className="bluecrest-focus mt-4 inline-block rounded-sm border-b border-carbon pb-0.5 text-[13px] font-semibold tracking-[-0.01em] text-carbon transition-colors hover:border-signal-blue hover:text-signal-blue"
            >
              {readMoreLabel}
            </a>
          )}
        </div>

        <div className="relative order-1 flex h-[340px] items-center justify-center sm:h-[420px] md:order-2 md:h-full">
          <div
            ref={heroCircle}
            data-hero-circle
            className="invisible absolute z-0 h-[285px] w-[285px] rounded-full bg-signal-blue opacity-0 sm:h-[370px] sm:w-[370px] md:h-[min(37vw,530px)] md:w-[min(37vw,530px)]"
            aria-hidden="true"
          />
          <img
            ref={heroImage}
            src={imageSrc}
            alt={imageAlt}
            width={1536}
            height={2304}
            fetchPriority="high"
            className="invisible relative z-10 h-[390px] w-auto max-w-none object-contain opacity-0 max-md:[mask-image:linear-gradient(to_bottom,#000_65%,transparent_90%)] sm:h-[490px] md:h-[min(78vh,830px)]"
          />
          <div
            ref={heroImageFade}
            data-hero-image-fade
            className="pointer-events-none invisible absolute inset-x-[-12%] bottom-0 z-20 h-[34%] bg-[linear-gradient(to_bottom,rgba(255,255,255,0)_0%,rgba(255,255,255,0.72)_35%,rgba(255,255,255,0.96)_62%,#fff_84%,#fff_100%)] opacity-0 sm:h-[32%] md:h-[29%]"
            aria-hidden="true"
          />
        </div>

        <div className="order-2 z-20 -mt-7 mb-6 text-center sm:-mt-10 md:order-3 md:m-0 md:text-left">
          <h1
            id="mediterra-hero-heading"
            className="text-balance text-[54px] font-extrabold leading-[0.84] tracking-[-0.075em] text-carbon sm:text-[70px] md:text-[clamp(68px,7.1vw,116px)]"
          >
            <span className="-my-[0.08em] block overflow-hidden py-[0.08em]">
              <span data-hero-line className="invisible block opacity-0">{overlayText.part1}</span>
            </span>
            <span className="-my-[0.08em] block overflow-hidden py-[0.08em]">
              <span data-hero-line className="invisible block opacity-0">{overlayText.part2}</span>
            </span>
          </h1>
        </div>
      </div>

      <footer className="relative z-30 mx-auto flex w-full max-w-[1440px] items-end justify-between gap-5">
        <nav className="flex items-center gap-1" aria-label="Footer links">
          {footerLinks.map(({ label, icon: Icon, href }) => (
            <motion.a
              key={label}
              href={href}
              initial={initial ?? { opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 1.1, ease: easing }}
              className="bluecrest-focus inline-flex h-11 w-11 items-center justify-center rounded-full text-carbon/60 transition-colors hover:bg-frost hover:text-signal-blue"
              aria-label={label}
              title={label}
            >
              <Icon aria-hidden="true" className="h-4 w-4" />
            </motion.a>
          ))}
        </nav>
        <motion.p
          initial={initial ?? { opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 1.3, ease: easing }}
          className="pb-2 text-right text-[12px] font-semibold tracking-[0.04em] text-carbon/60 sm:text-[13px]"
        >
          {locationText}
        </motion.p>
      </footer>
    </section>
  );
}
