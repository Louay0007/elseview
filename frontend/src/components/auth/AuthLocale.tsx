/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

export type AuthLanguage = "en" | "fr";
type LocalizedText = Record<AuthLanguage, string>;
type AuthLocaleValue = { language: AuthLanguage; setLanguage: (language: AuthLanguage) => void; text: (copy: LocalizedText) => string };

const AuthLocaleContext = createContext<AuthLocaleValue | null>(null);

export function resolveLanguage(saved: string | null, browser = "en"): "en" | "fr" {
  if (saved === "en" || saved === "fr") return saved;
  if (saved === "ar") return "en";
  return browser.toLowerCase().startsWith("fr") ? "fr" : "en";
}

function detectLanguage(): "en" | "fr" {
  if (typeof window === "undefined") return "en";
  try {
    return resolveLanguage(window.localStorage.getItem("elseview-language") ?? window.localStorage.getItem("mediterra-language"), navigator.language);
  } catch {
    return resolveLanguage(null, navigator.language);
  }
}

export function AuthLocaleProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<"en" | "fr">(detectLanguage);
  useEffect(() => {
    document.documentElement.lang = language;
    document.documentElement.dir = "ltr";
    try {
      window.localStorage.setItem("elseview-language", language);
      window.localStorage.removeItem("mediterra-language");
    } catch {
      // Storage can be unavailable in private browsing contexts.
    }
  }, [language]);
  const value = useMemo(() => ({ language, setLanguage: (next: AuthLanguage) => setLanguageState(resolveLanguage(next)), text: (copy: LocalizedText) => copy[language] }), [language]);
  return <AuthLocaleContext.Provider value={value}>{children}</AuthLocaleContext.Provider>;
}

export function useAuthLocale() {
  const context = useContext(AuthLocaleContext);
  if (!context) throw new Error("useAuthLocale must be used inside AuthLocaleProvider");
  return context;
}

export function useOptionalAuthLocale(): AuthLocaleValue {
  const context = useContext(AuthLocaleContext);
  if (!context) return { language: "en", setLanguage: () => {}, text: (copy: LocalizedText) => copy.en };
  return context;
}
