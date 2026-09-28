import { useOptionalAuthLocale } from "@/components/auth/AuthLocale";

export function LanguageSwitcher() {
  const { language, setLanguage, text } = useOptionalAuthLocale();
  return (
    <div className="relative isolate grid h-11 w-[104px] shrink-0 grid-cols-2 rounded-lg bg-[#f1f3f5] p-1" role="group" aria-label={text({ en: "Language", fr: "Langue" })}>
      <span aria-hidden="true" className="pointer-events-none absolute start-1 top-1 -z-10 h-9 w-12 rounded-md bg-white shadow-[0_1px_3px_rgba(0,0,0,0.1)] transition-transform duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] motion-reduce:transition-none" style={{ transform: `translateX(${language === "fr" ? 48 : 0}px)` }} />
      {(["en", "fr"] as const).map(locale => (
        <button key={locale} type="button" lang={locale} aria-label={locale === "en" ? "English" : "Français"} aria-pressed={language === locale} onClick={() => setLanguage(locale)} className={`relative rounded-md text-xs font-semibold tracking-normal transition-colors duration-200 motion-reduce:transition-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#0a84ff] ${language === locale ? "text-[#075ca8]" : "text-[#626870] hover:text-[#18181b]"}`}>{locale.toUpperCase()}</button>
      ))}
      <span className="sr-only" role="status">{text({ en: "Language: English", fr: "Langue : français" })}</span>
    </div>
  );
}