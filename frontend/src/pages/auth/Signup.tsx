import { useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowRight, Clock3, Languages, Mail } from "lucide-react";
import { AuthShell } from "@/components/auth/AuthShell";
import { useAuthLocale, type AuthLanguage } from "@/components/auth/AuthLocale";
import { PasswordField, fieldClassName, labelClassName } from "@/components/auth/AuthFields";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const copy = {
  en: { eyebrow: "Invitation accepted", title: "Create your Elseview account.", description: "We detected your language and timezone. You can change either before continuing.", first: "Legal first name", last: "Legal last name", display: "Display name", displayHint: "This is the name your care team will see.", email: "Email address", password: "Password", passwordPlaceholder: "Create a password", timezone: "Timezone", language: "Language", role: "Your role and organization were set by your invitation and cannot be changed here.", submit: "Create secure account", loading: "Creating account…", existing: "Already have access?", signIn: "Sign in" },
  fr: { eyebrow: "Invitation acceptée", title: "Créez votre compte Elseview.", description: "Votre langue et votre fuseau horaire ont été détectés. Vous pouvez les modifier.", first: "Prénom légal", last: "Nom légal", display: "Nom affiché", displayHint: "C’est le nom que votre équipe de soins verra.", email: "Adresse e-mail", password: "Mot de passe", passwordPlaceholder: "Créez un mot de passe", timezone: "Fuseau horaire", language: "Langue", role: "Votre rôle et votre établissement sont définis par l’invitation et ne peuvent pas être modifiés ici.", submit: "Créer le compte sécurisé", loading: "Création du compte…", existing: "Vous avez déjà un accès ?", signIn: "Se connecter" },
} satisfies Record<AuthLanguage, Record<string, string>>;

const invitationCopy = {
  en: { missing: ["This invitation link is incomplete", "Ask the person who invited you to send a new link."], expired: ["This invitation has expired", "Ask your Elseview administrator for a new invitation."], invalid: ["This invitation is not valid", "Check that you opened the complete link, or request a new invitation."], used: ["This invitation has already been used", "If you already created your account, sign in instead."], action: "Go to sign in", note: "Ask your organization’s administrator if you need a new invitation." },
  fr: { missing: ["Ce lien d’invitation est incomplet", "Demandez un nouveau lien à la personne qui vous a invité."], expired: ["Cette invitation a expiré", "Demandez une nouvelle invitation à votre administrateur Elseview."], invalid: ["Cette invitation n’est pas valide", "Vérifiez le lien complet ou demandez une nouvelle invitation."], used: ["Cette invitation a déjà été utilisée", "Si votre compte existe déjà, connectez-vous."], action: "Accéder à la connexion", note: "Demandez une nouvelle invitation à l’administrateur de votre établissement." },
} as const;

export default function SignupPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { language, setLanguage } = useAuthLocale();
  const c = copy[language];
  const tokenPresent = Boolean(searchParams.get("token"));
  const requestedState = searchParams.get("state");
  const state = requestedState === "expired" || requestedState === "invalid" || requestedState === "used" ? requestedState : !tokenPresent ? "missing" : null;
  const detectedTimezone = useMemo(() => Intl.DateTimeFormat().resolvedOptions().timeZone || "Africa/Tunis", []);
  const [timezone, setTimezone] = useState(detectedTimezone);
  const [loading, setLoading] = useState(false);

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const email = new FormData(event.currentTarget).get("email");
    setLoading(true);
    window.setTimeout(() => navigate("/auth/enroll-mfa", { state: { email } }), 650);
  };

  if (state) {
    const message = invitationCopy[language][state];
    return <AuthShell eyebrow={language === "fr" ? "Accès sur invitation" : "Invitation-only access"} title={message[0]} description={message[1]}><Button asChild className="h-12 w-full rounded-xl bg-[#07172f] text-base text-white"><Link to="/auth/login">{invitationCopy[language].action}</Link></Button><p className="mt-4 text-center text-[13px] text-[#747981]">{invitationCopy[language].note}</p></AuthShell>;
  }

  return (
    <AuthShell wide eyebrow={c.eyebrow} title={c.title} description={c.description}>
      <form onSubmit={submit} className="space-y-5" aria-busy={loading}>
        <div className="grid gap-4 sm:grid-cols-2"><div><Label className={labelClassName} htmlFor="legal-first-name">{c.first}</Label><Input id="legal-first-name" name="legalFirstName" required autoComplete="given-name" className={`${fieldClassName} mt-2 text-base`} /></div><div><Label className={labelClassName} htmlFor="legal-last-name">{c.last}</Label><Input id="legal-last-name" name="legalLastName" required autoComplete="family-name" className={`${fieldClassName} mt-2 text-base`} /></div></div>
        <div><Label className={labelClassName} htmlFor="display-name">{c.display}</Label><Input id="display-name" name="displayName" required autoComplete="nickname" className={`${fieldClassName} mt-2 text-base`} /><p className="mt-1.5 text-[12px] text-[#747981]">{c.displayHint}</p></div>
        <div><Label className={labelClassName} htmlFor="signup-email">{c.email}</Label><div className="relative mt-2"><Input id="signup-email" name="email" type="email" required autoComplete="email" placeholder="you@example.com" className={`${fieldClassName} ps-10 text-base`} /><Mail className="pointer-events-none absolute start-3.5 top-1/2 size-4 -translate-y-1/2 text-[#92969d]" aria-hidden="true" /></div></div>
        <div><Label className={labelClassName} htmlFor="signup-password">{c.password}</Label><div className="mt-2"><PasswordField id="signup-password" autoComplete="new-password" placeholder={c.passwordPlaceholder} /></div></div>
        <div className="grid gap-4 sm:grid-cols-2"><div><Label className={labelClassName} htmlFor="timezone">{c.timezone}</Label><div className="relative mt-2"><Clock3 className="pointer-events-none absolute start-3.5 top-1/2 z-10 size-4 -translate-y-1/2 text-[#92969d]" aria-hidden="true" /><Select value={timezone} onValueChange={setTimezone} name="timezone"><SelectTrigger id="timezone" className={`${fieldClassName} ps-10 text-base`}><SelectValue /></SelectTrigger><SelectContent><SelectItem value={detectedTimezone}>{detectedTimezone.split("_").join(" ")}</SelectItem>{detectedTimezone !== "Africa/Tunis" && <SelectItem value="Africa/Tunis">Tunis (UTC+1)</SelectItem>}<SelectItem value="Europe/Paris">Paris</SelectItem><SelectItem value="Europe/London">London</SelectItem></SelectContent></Select></div></div><div><Label className={labelClassName} htmlFor="language">{c.language}</Label><div className="relative mt-2"><Languages className="pointer-events-none absolute start-3.5 top-1/2 z-10 size-4 -translate-y-1/2 text-[#92969d]" aria-hidden="true" /><Select value={language} onValueChange={(value) => setLanguage(value as AuthLanguage)} name="language"><SelectTrigger id="language" className={`${fieldClassName} ps-10 text-base`}><SelectValue /></SelectTrigger><SelectContent><SelectItem value="en">English</SelectItem><SelectItem value="fr">Français (Tunisie)</SelectItem></SelectContent></Select></div></div></div>
        <p className="rounded-xl bg-[#f7f9fb] px-4 py-3 text-[13px] leading-relaxed text-[#60656d]">{c.role}</p>
        <Button type="submit" disabled={loading} className="h-12 w-full rounded-xl bg-[#07172f] text-base text-white hover:bg-[#0a2d5c]">{loading ? c.loading : c.submit}<ArrowRight className="size-4 rtl:rotate-180" aria-hidden="true" /></Button>
        <p className="text-center text-[14px] text-[#686b70]">{c.existing} <Link to="/auth/login" className="font-semibold text-[#0a67c7] hover:underline">{c.signIn}</Link></p>
      </form>
    </AuthShell>
  );
}
