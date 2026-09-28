import { useEffect, useRef, type ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { MediterraLogo } from "@/components/MediterraLogo";
import { useAuthLocale } from "@/components/auth/AuthLocale";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";

type AuthShellProps = {
  eyebrow?: string;
  title: ReactNode;
  description: string;
  documentTitle?: string;
  children?: ReactNode;
  wide?: boolean;
};

export function AuthShell({ title, description, documentTitle, children, wide = false }: AuthShellProps) {
  const { text } = useAuthLocale();
  const { pathname } = useLocation();
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    heading.current?.focus({ preventScroll: true });
    window.scrollTo({ top: 0, behavior: "instant" });
  }, [pathname]);
  useEffect(() => { document.title = `${documentTitle ?? "Elseview"} | Elseview`; }, [documentTitle]);
  return (
    <main className="min-h-dvh bg-white text-[#18181b] tracking-normal">
      <header className="mx-auto flex w-full max-w-[1200px] items-center justify-between gap-4 px-5 py-5 sm:px-8">
        <Link to="/" className="inline-flex min-h-11 items-center gap-2 rounded-md text-sm font-medium text-[#626870] hover:text-[#07172f] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff]">
          <ArrowLeft className="size-4 rtl:rotate-180" aria-hidden="true" /> {text({ en: "Home", fr: "Accueil" })}
        </Link>
        <LanguageSwitcher />
      </header>
      <section className="mx-auto flex w-full justify-center px-6 pb-10 pt-7 sm:pb-14 sm:pt-12">
        <div className={wide ? "w-full max-w-[540px]" : "w-full max-w-[400px]"}>
          <Link to="/" aria-label="Elseview home" className="mx-auto mb-8 flex w-fit rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff] focus-visible:ring-offset-4">
            <MediterraLogo />
          </Link>
          <div className="mb-8 text-center">
            <h1 ref={heading} tabIndex={-1} className="text-[30px] leading-[1.15] tracking-normal outline-none sm:text-[34px]">{title}</h1>
            {description && <p className="mx-auto mt-3 text-[15px] leading-relaxed text-[#626870]">{description}</p>}
          </div>
          {children}
        </div>
      </section>
    </main>
  );
}
