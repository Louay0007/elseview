import { useEffect, useState } from "react";
import { ArrowUpRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { MediterraLogo } from "@/components/MediterraLogo";
import { authRoute, routes } from "@/lib/routes";

const navigation = [
  { label: "How it works", href: "#how-it-works" },
  { label: "Questions", href: "#faq" },
  { label: "Pricing", href: routes.buyCredits },
];

export function MediterraHeader() {
  const [isScrolled, setIsScrolled] = useState(false);

  useEffect(() => {
    const updateHeader = () => {
      const nextIsScrolled = window.scrollY > 32;
      setIsScrolled((current) => current === nextIsScrolled ? current : nextIsScrolled);
    };

    updateHeader();
    window.addEventListener("scroll", updateHeader, { passive: true });
    return () => window.removeEventListener("scroll", updateHeader);
  }, []);

  return (
    <header
      className={cn(
        "fixed inset-x-0 top-0 z-50 border-b transition-[background-color,border-color,box-shadow,backdrop-filter] duration-500 motion-reduce:duration-0",
        isScrolled
          ? "border-black/[0.07] bg-white/[0.68] shadow-[0_8px_30px_rgba(35,70,105,0.08)] backdrop-blur-2xl backdrop-saturate-150"
          : "border-transparent bg-transparent shadow-none backdrop-blur-none",
      )}
    >
      <div className="bluecrest-container grid min-h-[88px] grid-cols-[1fr_auto_1fr] items-center gap-4 py-2">
        <a
          href="#top"
          aria-label="Elseview home"
          className={cn(
            "bluecrest-focus inline-flex w-fit items-center rounded-lg bg-white text-carbon transition-colors duration-500 motion-reduce:duration-0",
          )}
        >
          <MediterraLogo />
        </a>

        <nav className="hidden items-center gap-1 md:flex" aria-label="Primary navigation">
          {navigation.map((item) => (
            <a
              key={item.label}
              href={item.href}
              className={cn(
                "bluecrest-focus rounded-full px-3.5 py-2 text-[13px] font-medium tracking-[-0.015em] transition-colors duration-300",
                isScrolled
                  ? "text-carbon/75 hover:bg-black/[0.055] hover:text-carbon"
                  : "text-white/90 [text-shadow:0_1px_8px_rgba(0,31,73,0.35)] hover:bg-white/[0.12] hover:text-white",
              )}
            >
              {item.label}
            </a>
          ))}
        </nav>

        <div className="hidden justify-self-end md:block">
          <a
            href={authRoute("signup", "researcher")}
            className={cn(
              "bluecrest-focus inline-flex h-9 items-center gap-1.5 rounded-full px-4 text-[13px] font-semibold tracking-[-0.015em] transition-all duration-300",
              isScrolled
                ? "bg-carbon text-white shadow-[0_5px_15px_rgba(0,0,0,0.12)] hover:bg-black"
                : "border border-white/35 bg-white/[0.14] text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.24)] backdrop-blur-md hover:bg-white/[0.22]",
            )}
          >
            Start free
            <ArrowUpRight className="h-3.5 w-3.5" strokeWidth={2.2} aria-hidden="true" />
          </a>
        </div>
      </div>
    </header>
  );
}
