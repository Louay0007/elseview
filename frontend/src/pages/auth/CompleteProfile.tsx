import { useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowLeft, ArrowRight, Check, ChevronDown, FlaskConical, LogOut, Users, FileBarChart2 } from "lucide-react";
import { useAuthLocale } from "@/components/auth/AuthLocale";
import { authWords as words, isValidDisplayName } from "@/lib/auth";
import { countryCallingCodes, defaultCountryIso, getCountryFlag, getCountryName, isValidPhoneNumber, normalizePhoneNumber } from "@/lib/phoneCountries";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { MediterraLogo } from "@/components/MediterraLogo";
import { Button } from "@/components/ui/button";
import { apiFetch, backendAvailable } from "@/lib/api";
import { useWorkspace } from "@/components/workspace/WorkspaceContext";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

const jobRoles = [
  { en: "Product Manager", fr: "Chef de produit" },
  { en: "UX Researcher", fr: "UX Researcher" },
  { en: "Designer", fr: "Designer" },
  { en: "Developer", fr: "Développeur" },
  { en: "Marketer", fr: "Marketeur" },
  { en: "Founder", fr: "Fondateur" },
  { en: "Other", fr: "Autre" },
];

const teamSizes = [
  { en: "Just me", fr: "Moi uniquement" },
  { en: "2 – 5 people", fr: "2 à 5 personnes" },
  { en: "6 – 20 people", fr: "6 à 20 personnes" },
  { en: "21+ people", fr: "21 personnes et plus" },
];

export default function CompleteProfile() {
  const { language, text } = useAuthLocale();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const role = params.get("role") === "tester" ? "tester" : "researcher";
  const roleLink = (path: string) => `${path}${path.includes("?") ? "&" : "?"}role=${role}`;

  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [countryIso, setCountryIso] = useState(defaultCountryIso);
  const [phone, setPhone] = useState("");
  const [phoneTouched, setPhoneTouched] = useState(false);
  const [whatsapp, setWhatsapp] = useState(true);
  const [company, setCompany] = useState("");
  const [jobRole, setJobRole] = useState("");
  const [teamSize, setTeamSize] = useState("");
  const [updates, setUpdates] = useState(true);
  const [submitted, setSubmitted] = useState(false);
  const [tipIndex, setTipIndex] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { refresh: refreshWorkspaces } = useWorkspace();

  const countryOptions = useMemo(
    () =>
      countryCallingCodes
        .map((country) => ({ ...country, localizedName: getCountryName(country, language) }))
        .sort((first, second) => first.localizedName.localeCompare(second.localizedName, language)),
    [language],
  );
  const selectedCountry = countryOptions.find((country) => country.iso === countryIso) ?? countryOptions.find((country) => country.iso === defaultCountryIso) ?? countryOptions[0];
  const normalizedPhone = useMemo(() => normalizePhoneNumber(phone, selectedCountry.callingCode, selectedCountry.iso), [phone, selectedCountry.callingCode, selectedCountry.iso]);
  const phoneValid = useMemo(() => isValidPhoneNumber(normalizedPhone, selectedCountry.callingCode, selectedCountry.iso), [normalizedPhone, selectedCountry.callingCode, selectedCountry.iso]);
  const showPhoneError = (phoneTouched || submitted) && !phoneValid;
  const displayNameValid = isValidDisplayName(displayName);
  const showDisplayNameError = submitted && !displayNameValid;
  const canContinue =
    firstName.trim().length > 0 &&
    lastName.trim().length > 0 &&
    displayNameValid &&
    phoneValid &&
    company.trim().length > 0 &&
    jobRole.length > 0 &&
    teamSize.length > 0;

  const tips = useMemo(
    () =>
      role === "tester"
        ? [
            { icon: Users, title: words("Take tests that fit you", "Participez à des tests faits pour vous"), body: words("Choose from studies that match your profile and availability.", "Choisissez des études adaptées à votre profil et vos disponibilités.") },
            { icon: FileBarChart2, title: words("Share honest feedback", "Partagez un avis honnête"), body: words("Clear answers help researchers improve real products.", "Des réponses claires aident les chercheurs à améliorer de vrais produits.") },
            { icon: FlaskConical, title: words("Get rewarded", "Soyez récompensé"), body: words("Completed sessions are recorded so rewards can follow.", "Les sessions terminées sont enregistrées pour permettre les récompenses.") },
          ]
        : [
            { icon: Users, title: words("Easily recruit participants", "Recrutez facilement des participants"), body: words("Choose from a variety of demographics to find the ideal participants for your study.", "Choisissez parmi divers profils démographiques pour trouver les participants idéaux.") },
            { icon: FlaskConical, title: words("Launch tests in minutes", "Lancez des tests en quelques minutes"), body: words("Pick a template, add your questions, and preview before you publish.", "Choisissez un modèle, ajoutez vos questions et prévisualisez avant de publier.") },
            { icon: FileBarChart2, title: words("Read clear results", "Lisez des résultats clairs"), body: words("Follow sample charts and quotes to decide what to validate next.", "Suivez graphiques et citations d’exemple pour décider quoi valider ensuite.") },
          ],
    [role],
  );

  const submit = (event: FormEvent) => {
    event.preventDefault();
    setSubmitted(true);
    setPhoneTouched(true);
    setError(null);
    if (!canContinue) {
      let firstInvalidField = "teamSize";
      if (!firstName.trim()) firstInvalidField = "firstName";
      else if (!lastName.trim()) firstInvalidField = "lastName";
      else if (!displayNameValid) firstInvalidField = "displayName";
      else if (!phoneValid) firstInvalidField = "phone";
      else if (!company.trim()) firstInvalidField = "company";
      else if (!jobRole) firstInvalidField = "jobRole";
      document.getElementById(firstInvalidField)?.focus();
      return;
    }
    const goNext = () => {
      const target = role === "researcher" ? "/dashboard" : roleLink("/auth/login");
      const query = new URLSearchParams({ role, welcome: "1", firstName: firstName.trim() });
      navigate(role === "researcher" ? `${target}?${query.toString()}` : target);
    };
    if (!backendAvailable()) {
      goNext();
      return;
    }
    setBusy(true);
    void (async () => {
      try {
        await apiFetch("/me");
        await apiFetch("/workspaces", {
          method: "POST",
          body: { name: `${firstName.trim()}'s workspace` },
        });
        refreshWorkspaces();
      } catch {
        setError(text({ en: "Could not save your workspace. You can continue — we’ll retry later.", fr: "Espace non enregistré. Continuez — on réessaiera." }));
      } finally {
        setBusy(false);
        goNext();
      }
    })();
  };

  const logout = () => {
    navigate(roleLink("/auth/login"));
  };

  const inputClass = (invalid = false) =>
    cn(
      "h-[52px] rounded-[12px] border bg-white px-4 text-[15px] text-[#18181b] shadow-none outline-none transition-colors placeholder:text-[#626870] focus:border-[#183a68] focus:ring-2 focus:ring-[#183a68]/15",
      invalid ? "border-[#e5484d] focus:border-[#e5484d] focus:ring-[#e5484d]/15" : "border-[#c9ccd1]",
    );

  return (
    <main className="min-h-dvh bg-white text-[#18181b]">
      <header className="mx-auto flex w-full max-w-[1200px] items-center justify-between gap-4 px-5 py-5 sm:px-8">
        <Link to="/" className="inline-flex min-h-11 items-center gap-2 rounded-md text-sm font-medium text-[#626870] hover:text-[#07172f] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff]">
          <ArrowLeft className="size-4 rtl:rotate-180" aria-hidden="true" /> {text({ en: "Home", fr: "Accueil" })}
        </Link>
        <div className="flex items-center gap-3">
          <LanguageSwitcher />
          <Button type="button" variant="outline" onClick={logout} className="inline-flex min-h-11 items-center gap-2 rounded-lg border-[#c9ccd1] px-4 text-sm font-semibold text-[#07172f] hover:border-[#183a68] hover:text-[#183a68]">
            <LogOut className="size-4" aria-hidden="true" /> {text({ en: "Log out", fr: "Se déconnecter" })}
          </Button>
        </div>
      </header>

      <section className="mx-auto grid w-full max-w-[1120px] gap-14 px-6 pb-16 pt-6 sm:pt-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] lg:gap-20">
        <div>
          <h1 className="text-[28px] font-bold tracking-[-0.02em] sm:text-[32px]">{text({ en: "Tell us about yourself", fr: "Parlez-nous de vous" })}</h1>
          <p className="mt-2 text-[15px] text-[#6d6d70]">{text({ en: "We need to know some information about yourself", fr: "Nous avons besoin de quelques informations vous concernant" })}</p>

            <form onSubmit={submit} noValidate className="mt-8 space-y-5">
              <div>
                <label htmlFor="firstName" className="sr-only">{text({ en: "First name", fr: "Prénom" })}</label>
                <Input id="firstName" name="firstName" value={firstName} onChange={(e) => setFirstName(e.target.value)} placeholder={text({ en: "First name", fr: "Prénom" })} autoComplete="given-name" required className={inputClass()} />
              </div>
              <div>
                <label htmlFor="lastName" className="sr-only">{text({ en: "Last name", fr: "Nom" })}</label>
                <Input id="lastName" name="lastName" value={lastName} onChange={(e) => setLastName(e.target.value)} placeholder={text({ en: "Last name", fr: "Nom" })} autoComplete="family-name" required className={inputClass()} />
              </div>
              <div>
                <label htmlFor="displayName" className="sr-only">{text({ en: "Display name (optional)", fr: "Nom affiché (facultatif)" })}</label>
                <Input id="displayName" name="displayName" value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder={text({ en: "Display name (optional)", fr: "Nom affiché (facultatif)" })} autoComplete="nickname" autoCapitalize="words" spellCheck maxLength={100} aria-invalid={showDisplayNameError} aria-describedby={showDisplayNameError ? "displayName-error" : undefined} className={inputClass(showDisplayNameError)} />
                {showDisplayNameError && <p id="displayName-error" role="alert" className="mt-1.5 text-[13px] text-[#b42318]">{text({ en: "Use no more than 100 characters.", fr: "Utilisez 100 caractères maximum." })}</p>}
              </div>

              <div>
                <div className={cn("relative rounded-[12px] border bg-white transition-colors focus-within:border-[#183a68] focus-within:ring-2 focus-within:ring-[#183a68]/15", showPhoneError ? "border-[#e5484d] focus-within:border-[#e5484d] focus-within:ring-[#e5484d]/15" : "border-[#c9ccd1]")}>
                  <span aria-hidden="true" className="pointer-events-none absolute -top-2.5 left-3 bg-white px-1 text-xs text-[#6d6d70]">{text({ en: "Phone number", fr: "Numéro de téléphone" })}</span>
                  <div className="flex min-w-0 items-stretch">
                    <div className="relative max-w-[52%] shrink-0 border-r border-[#e4e4e7]">
                      <label htmlFor="countryCode" className="sr-only">{text({ en: "Country and calling code", fr: "Pays et indicatif téléphonique" })}</label>
                      <select
                        id="countryCode"
                        name="countryCode"
                        value={selectedCountry.iso}
                        onChange={(e) => {
                          setCountryIso(e.target.value);
                          setPhoneTouched(false);
                        }}
                        className="h-[52px] w-full appearance-none bg-transparent py-0 pl-3 pr-8 text-[15px] font-medium text-[#18181b] outline-none"
                      >
                        {countryOptions.map((country) => (
                          <option key={country.iso} value={country.iso}>
                            (+{country.callingCode}) {getCountryFlag(country.iso)} {country.localizedName}
                          </option>
                        ))}
                      </select>
                      <ChevronDown className="pointer-events-none absolute right-2 top-1/2 size-3.5 -translate-y-1/2 text-[#6d6d70]" aria-hidden="true" />
                    </div>
                    <div className="flex min-w-0 flex-1 items-center px-3">
                      <label htmlFor="phone" className="sr-only">{text({ en: "Mobile number", fr: "Numéro mobile" })}</label>
                      <input
                        id="phone"
                        name="phone"
                        type="tel"
                        value={phone}
                        onChange={(e) => setPhone(sanitizePhoneInput(e.target.value))}
                        onBlur={() => setPhoneTouched(true)}
                        inputMode="tel"
                        autoComplete="tel-national"
                        required
                        dir="ltr"
                        placeholder={text({ en: "Mobile number", fr: "Numéro mobile" })}
                        aria-invalid={showPhoneError}
                        aria-describedby={showPhoneError ? "phone-error phone-hint" : "phone-hint"}
                        className="h-full min-w-0 w-full bg-transparent text-[15px] text-[#18181b] outline-none placeholder:text-[#626870]"
                      />
                    </div>
                  </div>
                </div>
                <p id="phone-hint" className="mt-1.5 text-[13px] text-[#6d6d70]">{text({ en: "Choose your country and enter a mobile number.", fr: "Choisissez votre pays et saisissez un numéro mobile." })}</p>
                {showPhoneError && <p id="phone-error" role="alert" className="mt-1.5 text-[13px] text-[#b42318]">{text({ en: "Enter a valid mobile number for the selected country.", fr: "Saisissez un numéro mobile valide pour le pays sélectionné." })}</p>}
              </div>

              <label className="flex min-h-11 cursor-pointer items-center gap-3 rounded-md text-[15px] font-medium focus-within:ring-2 focus-within:ring-[#0a84ff] focus-within:ring-offset-2">
                <input type="checkbox" checked={whatsapp} onChange={(e) => setWhatsapp(e.target.checked)} className="sr-only" />
                <span className={cn("grid size-6 shrink-0 place-items-center rounded-[6px] transition-colors", whatsapp ? "bg-[#183a68] text-white" : "border border-[#c9ccd1] bg-white text-transparent")}><Check className="size-4" strokeWidth={3} aria-hidden="true" /></span>
                {text({ en: "I use WhatsApp on this number", fr: "J’utilise WhatsApp sur ce numéro" })}
              </label>

              <div>
                <label htmlFor="company" className="sr-only">{text({ en: "Company name", fr: "Nom de l’entreprise" })}</label>
                <Input id="company" name="company" value={company} onChange={(e) => setCompany(e.target.value)} placeholder={text({ en: "Company name", fr: "Nom de l’entreprise" })} autoComplete="organization" required className={inputClass()} />
              </div>

              <div className="relative">
                <label htmlFor="jobRole" className="sr-only">{text({ en: "Job role", fr: "Poste occupé" })}</label>
                <select id="jobRole" value={jobRole} onChange={(e) => setJobRole(e.target.value)} required className={cn(inputClass(), "w-full appearance-none pr-10", !jobRole && "text-[#626870]")}>
                  <option value="" disabled>{text({ en: "Job role", fr: "Poste occupé" })}</option>
                  {jobRoles.map((r) => (<option key={r.en} value={r.en} className="text-[#18181b]">{text(r)}</option>))}
                </select>
                <ChevronDown className="pointer-events-none absolute right-4 top-1/2 size-4 -translate-y-1/2 text-[#626870]" aria-hidden="true" />
              </div>

              <div className="relative">
                <label htmlFor="teamSize" className="sr-only">{text({ en: "Research & design team size", fr: "Taille de l’équipe recherche & design" })}</label>
                <select id="teamSize" value={teamSize} onChange={(e) => setTeamSize(e.target.value)} required className={cn(inputClass(), "w-full appearance-none pr-10", !teamSize && "text-[#626870]")}>
                  <option value="" disabled>{text({ en: "Research & design team size", fr: "Taille de l’équipe recherche & design" })}</option>
                  {teamSizes.map((s) => (<option key={s.en} value={s.en} className="text-[#18181b]">{text(s)}</option>))}
                </select>
                <ChevronDown className="pointer-events-none absolute right-4 top-1/2 size-4 -translate-y-1/2 text-[#626870]" aria-hidden="true" />
              </div>

              <label className="flex min-h-11 cursor-pointer items-center gap-3 rounded-md text-[15px] font-medium focus-within:ring-2 focus-within:ring-[#0a84ff] focus-within:ring-offset-2">
                <span className={cn("grid size-6 shrink-0 place-items-center rounded-[6px] transition-colors", updates ? "bg-[#183a68] text-white" : "border border-[#c9ccd1] bg-white text-transparent")}><Check className="size-4" strokeWidth={3} aria-hidden="true" /></span>
                <input type="checkbox" checked={updates} onChange={(e) => setUpdates(e.target.checked)} className="sr-only" />
                {text({ en: "I’d like to receive updates about Elseview", fr: "Je souhaite recevoir les nouveautés d’Elseview" })}
              </label>

              {submitted && !canContinue && <p role="alert" className="text-center text-[13px] text-[#b42318]">{text({ en: "Complete the required fields to continue.", fr: "Complétez les champs obligatoires pour continuer." })}</p>}
              {error && <p role="alert" className="text-center text-[13px] text-[#b42318]">{error}</p>}
              <Button type="submit" disabled={busy} className="h-[52px] w-full rounded-full bg-[#07172f] text-[16px] font-semibold text-white hover:bg-[#153654]">
                {text({ en: "Next", fr: "Suivant" })} <ArrowRight size={18} aria-hidden="true" className="rtl:rotate-180" />
              </Button>
            </form>
        </div>

        <div>
          <h2 className="text-[28px] font-bold tracking-[-0.02em] sm:text-[32px]">{text({ en: "Some useful tips", fr: "Quelques conseils utiles" })}</h2>
          <p className="mt-2 text-[15px] text-[#6d6d70]">
            {role === "tester"
              ? text({ en: "To help you get started with your tester account", fr: "Pour vous aider à démarrer avec votre compte testeur" })
              : text({ en: "To help you get started with your researcher account", fr: "Pour vous aider à démarrer avec votre compte chercheur" })}
          </p>

          <div className="mt-8 rounded-[20px] border border-[#ececee] bg-[#fafafa] p-8">
            <TipIcon icon={tips[tipIndex].icon} />
            <h3 className="mt-6 text-[17px] font-bold">{text(tips[tipIndex].title)}</h3>
            <p className="mt-3 min-h-[66px] text-[15px] leading-relaxed text-[#6d6d70]">{text(tips[tipIndex].body)}</p>
            <div className="mt-8 flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={() => setTipIndex((i) => Math.max(0, i - 1))}
                disabled={tipIndex === 0}
                aria-label={text({ en: "Previous tip", fr: "Conseil précédent" })}
                className={cn("grid size-11 place-items-center rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff]", tipIndex === 0 ? "bg-[#c9c9ca] text-white" : "bg-black text-white hover:bg-[#07172f]")}
              >
                <ArrowLeft size={18} aria-hidden="true" className="rtl:rotate-180" />
              </button>
              <button
                type="button"
                onClick={() => setTipIndex((i) => Math.min(tips.length - 1, i + 1))}
                disabled={tipIndex === tips.length - 1}
                aria-label={text({ en: "Next tip", fr: "Conseil suivant" })}
                className={cn("grid size-11 place-items-center rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff]", tipIndex === tips.length - 1 ? "bg-[#c9c9ca] text-white" : "bg-black text-white hover:bg-[#07172f]")}
              >
                <ArrowRight size={18} aria-hidden="true" className="rtl:rotate-180" />
              </button>
            </div>
          </div>

          <div className="mt-8 flex justify-center">
            <MediterraLogo />
          </div>
        </div>
      </section>
    </main>
  );
}

function sanitizePhoneInput(value: string) {
  const trimmedValue = value.trimStart();
  const prefix = trimmedValue.startsWith("+") ? "+" : "";
  return `${prefix}${trimmedValue.slice(prefix.length).replace(/[^\d\s().-]/g, "")}`;
}

function TipIcon({ icon: Icon }: { icon: typeof Users }) {
  return (
    <span className="grid size-12 place-items-center rounded-2xl bg-[#183a68]/10 text-[#183a68]">
      <Icon size={26} strokeWidth={1.8} aria-hidden="true" />
    </span>
  );
}
