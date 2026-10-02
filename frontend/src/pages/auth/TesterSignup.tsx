import { useEffect, useState, type FormEvent, type SVGProps } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft, Eye, EyeOff, LoaderCircle } from "lucide-react";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { useAuthLocale } from "@/components/auth/AuthLocale";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { MediterraLogo } from "@/components/MediterraLogo";
import { authWords as words, isValidEmail, isValidPassword } from "@/lib/auth";
import { apiFetch } from "@/lib/api";
import { authRoute, routes, withQuery } from "@/lib/routes";

function GoogleMark(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 48 48" aria-hidden="true" {...props}>
      <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
      <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
      <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
      <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
    </svg>
  );
}

export { GoogleMark };

function FacebookMark(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 320 512" aria-hidden="true" {...props}>
      <path fill="#1877F2" d="M279.14 288l14.22-92.66h-88.91v-60.13c0-25.35 12.42-50.06 52.24-50.06h40.42V6.26S260.43 0 225.36 0c-73.22 0-121.08 44.38-121.08 124.72v70.62H22.89V288h81.39v224h100.17V288z" />
    </svg>
  );
}

export { FacebookMark };

function AppleMark(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 384 512" aria-hidden="true" {...props}>
      <path fill="currentColor" d="M318.7 268.7c-.2-36.7 16.4-64.4 50-84.8-18.8-26.9-47.2-41.7-84.7-44.6-35.5-2.8-74.3 20.7-88.5 20.7-15 0-49.4-19.7-76.4-19.7C63.3 141.2 4 184.8 4 273.5q0 39.3 14.4 81.2c12.8 36.7 59 126.7 107.2 125.2 25.2-.6 43-17.9 75.8-17.9 31.8 0 48.3 17.9 76.4 17.9 48.6-.7 90.4-82.5 102.6-119.3-65.2-30.7-61.7-90-61.7-91.9zm-56.6-164.2c27.3-32.4 24.8-61.9 24-72.5-24.1 1.4-52 16.4-67.9 34.9-17.5 19.8-27.8 44.3-25.6 71.9 26.1 2 49.9-11.4 69.5-34.3z" />
    </svg>
  );
}

export { AppleMark };

const copy = {
  titleA: words("Create a ", "Créez un compte "),
  titleB: words("tester", "testeur"),
  titleC: words(" account", ""),
  subtitle: words("Create an account and get paid to take tests", "Créez un compte et soyez payé pour réaliser des tests"),
  emailPlaceholder: words("Email address", "Adresse e-mail"),
  required: words("Required field", "Champ requis"),
  emailInvalid: words("Enter a valid email, up to 254 characters.", "Saisissez un e-mail valide de 254 caractères maximum."),
  passwordPlaceholder: words("Create password", "Créez un mot de passe"),
  passwordInvalid: words("Use between 12 and 256 characters.", "Utilisez entre 12 et 256 caractères."),
  showPassword: words("Show password", "Afficher le mot de passe"),
  hidePassword: words("Hide password", "Masquer le mot de passe"),
  termsA: words("I agree to the ", "J’accepte les "),
  terms: words("Terms of Use", "Conditions d’utilisation"),
  termsB: words(" and have read the ", " et j’ai lu la "),
  privacy: words("Privacy Policy", "Politique de confidentialité"),
  age: words("I confirm that I’m over 18 years old", "Je confirme avoir plus de 18 ans"),
  submit: words("Create your account", "Créez votre compte"),
  waiting: words("Please wait…", "Veuillez patienter…"),
  or: words("Or", "Ou"),
  withGoogle: words("Continue with Google", "Continuer avec Google"),
  withFacebook: words("Continue with Facebook", "Continuer avec Facebook"),
  withApple: words("Continue with Apple", "Continuer avec Apple"),
  socialUnavailable: words("Social sign-up isn’t available yet — continue with email.", "La connexion sociale n’est pas encore disponible — continuez avec votre e-mail."),
  serverError: words("Service unavailable. Try again shortly.", "Service indisponible. Réessayez dans un instant."),
  offline: words("You’re offline. Nothing was submitted. Reconnect and try again.", "Vous êtes hors ligne. Rien n’a été envoyé. Reconnectez-vous et réessayez."),
  existing: words("Already have an account?", "Déjà un compte ?"),
  signIn: words("Sign in", "Se connecter"),
  home: words("Home", "Accueil"),
};

export default function TesterSignup() {
  const { text } = useAuthLocale();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [visible, setVisible] = useState(false);
  const [terms, setTerms] = useState(false);
  const [age, setAge] = useState(false);
  const [touchedEmail, setTouchedEmail] = useState(false);
  const [touchedPassword, setTouchedPassword] = useState(false);
  const [attempted, setAttempted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => { document.title = `${text(words("Create a tester account", "Créez un compte testeur"))} | Elseview`; }, [text]);

  const emailOk = isValidEmail(email);
  const passwordOk = isValidPassword(password);
  const canSubmit = emailOk && passwordOk && terms && age && !busy;

  const showEmailError = (touchedEmail || attempted) && !emailOk;
  const showPasswordError = (touchedPassword || attempted) && !passwordOk;

  const submit = (event: FormEvent) => {
    event.preventDefault();
    setAttempted(true);
    setNotice(null);
    if (!emailOk || !passwordOk) return;
    if (!navigator.onLine) {
      setNotice(text(copy.offline));
      return;
    }
    setBusy(true);
    void (async () => {
      try {
        await apiFetch("/auth/register", { method: "POST", body: { email, password, display_name: "" } });
        navigate(withQuery(routes.testerOnboarding, { role: "tester" }));
      } catch {
        setNotice(text(copy.serverError));
      } finally {
        setBusy(false);
      }
    })();
  };

  const inputClass = (invalid: boolean) =>
    `h-14 w-full rounded-xl border bg-white px-5 text-[16px] md:text-[16px] text-[#18181b] shadow-none outline-none transition placeholder:text-[#a7abb2] focus:border-[#18181b] ${invalid ? "border-[#f04438]" : "border-[#b9bec7] hover:border-[#8f96a1]"}`;

  return (
    <main className="min-h-dvh bg-white text-[#18181b]">
      <header className="mx-auto flex w-full max-w-[1200px] items-center justify-between gap-4 px-5 py-5 sm:px-8">
        <Link to="/" className="inline-flex min-h-11 items-center gap-2 rounded-md text-sm font-medium text-[#626870] hover:text-[#07172f] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff]">
          <ArrowLeft className="size-4 rtl:rotate-180" aria-hidden="true" /> {text(copy.home)}
        </Link>
        <LanguageSwitcher />
      </header>
      <section className="mx-auto w-full max-w-[540px] px-6 pb-14 pt-4 sm:pt-8">
        <Link to="/" aria-label="Elseview home" className="mx-auto mb-8 flex w-fit rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff] focus-visible:ring-offset-4">
          <MediterraLogo />
        </Link>
        <h1 className="text-[32px] font-bold leading-tight tracking-tight sm:text-[36px]">
          {text(copy.titleA)}<span className="text-[#1d4ed8]">{text(copy.titleB)}</span>{text(copy.titleC)}
        </h1>
        <p className="mt-3 text-[17px] leading-relaxed text-[#6d6d70]">{text(copy.subtitle)}</p>

        <form onSubmit={submit} noValidate className="mt-8 space-y-6">
          {notice && <div role="alert" className="rounded-xl bg-[#fff2ef] px-4 py-3 text-sm leading-relaxed text-[#9c2d20]">{notice}</div>}
          <div>
            <label htmlFor="tester-email" className="sr-only">{text(copy.emailPlaceholder)}</label>
            <Input
              id="tester-email"
              name="email"
              type="email"
              autoComplete="email"
              spellCheck={false}
              dir="ltr"
              maxLength={254}
              placeholder={text(copy.emailPlaceholder)}
              value={email}
              disabled={busy}
              onChange={(event) => { setEmail(event.target.value); setNotice(null); }}
              onBlur={() => setTouchedEmail(true)}
              aria-invalid={showEmailError}
              className={inputClass(showEmailError)}
            />
            {showEmailError && <p role="alert" className="mt-2 text-[14px] text-[#f04438]">{email.trim() === "" ? text(copy.required) : text(copy.emailInvalid)}</p>}
          </div>

          <div>
            <label htmlFor="tester-password" className="sr-only">{text(copy.passwordPlaceholder)}</label>
            <div className="relative">
              <Input
                id="tester-password"
                name="password"
                type={visible ? "text" : "password"}
                autoComplete="new-password"
                maxLength={256}
                placeholder={text(copy.passwordPlaceholder)}
                value={password}
                disabled={busy}
                onChange={(event) => { setPassword(event.target.value); setNotice(null); }}
                onBlur={() => setTouchedPassword(true)}
                aria-invalid={showPasswordError}
                className={`${inputClass(showPasswordError)} pe-14`}
              />
              <button
                type="button"
                onClick={() => setVisible((value) => !value)}
                aria-label={text(visible ? copy.hidePassword : copy.showPassword)}
                aria-pressed={visible}
                className="absolute end-2 top-1/2 flex size-10 -translate-y-1/2 items-center justify-center rounded-lg text-[#7b7f86] hover:text-[#18181b] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff]"
              >
                {visible ? <EyeOff className="size-5" aria-hidden="true" /> : <Eye className="size-5" aria-hidden="true" />}
              </button>
            </div>
            {showPasswordError && <p role="alert" className="mt-2 text-[14px] text-[#f04438]">{password === "" ? text(copy.required) : text(copy.passwordInvalid)}</p>}
          </div>

          <div className="space-y-4 pt-1">
            <label className="flex cursor-pointer items-start gap-4">
              <Checkbox
                checked={terms}
                onCheckedChange={(value) => setTerms(value === true)}
                aria-label={text(words("Agree to terms and privacy policy", "Accepter les conditions et la politique de confidentialité"))}
                className="mt-0.5 size-7 shrink-0 rounded-[8px] border-2 border-[#c4c9d1] bg-white data-[state=checked]:border-[#18181b] data-[state=checked]:bg-[#18181b] data-[state=checked]:text-white [&_svg]:size-5"
              />
              <span className="text-[16px] leading-relaxed text-[#18181b]">
                {text(copy.termsA)}
                <Link to={routes.terms} className="text-[#7c3aed] underline underline-offset-2 hover:text-[#6d28d9]">{text(copy.terms)}</Link>
                {text(copy.termsB)}
                <Link to={routes.privacy} className="text-[#7c3aed] underline underline-offset-2 hover:text-[#6d28d9]">{text(copy.privacy)}</Link>
              </span>
            </label>
            <label className="flex cursor-pointer items-start gap-4">
              <Checkbox
                checked={age}
                onCheckedChange={(value) => setAge(value === true)}
                aria-label={text(copy.age)}
                className="mt-0.5 size-7 shrink-0 rounded-[8px] border-2 border-[#c4c9d1] bg-white data-[state=checked]:border-[#18181b] data-[state=checked]:bg-[#18181b] data-[state=checked]:text-white [&_svg]:size-5"
              />
              <span className="text-[16px] leading-relaxed text-[#18181b]">{text(copy.age)}</span>
            </label>
          </div>

          <button
            type="submit"
            disabled={!canSubmit}
            className={`flex h-14 w-full items-center justify-center gap-2 rounded-full text-[17px] font-semibold text-white transition ${canSubmit ? "bg-black hover:bg-[#2a2a2e]" : "bg-[#d7d7db]"}`}
          >
            {busy && <LoaderCircle className="size-5 animate-spin motion-reduce:animate-none" aria-hidden="true" />}
            {text(busy ? copy.waiting : copy.submit)}
          </button>
        </form>

        <div className="mt-8 flex items-center gap-4" aria-hidden="true">
          <span className="h-px flex-1 bg-[#e2e3e8]" />
          <span className="text-[16px] text-[#18181b]">{text(copy.or)}</span>
          <span className="h-px flex-1 bg-[#e2e3e8]" />
        </div>

        <div className="mt-6 grid grid-cols-3 gap-4">
          <button type="button" onClick={() => setNotice(text(copy.socialUnavailable))} aria-label={text(copy.withGoogle)} className="flex h-14 items-center justify-center rounded-full border-[1.5px] border-[#18181b] bg-white transition hover:bg-[#f6f6f7] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff] focus-visible:ring-offset-2">
            <GoogleMark className="size-7" />
          </button>
          <button type="button" onClick={() => setNotice(text(copy.socialUnavailable))} aria-label={text(copy.withFacebook)} className="flex h-14 items-center justify-center rounded-full border-[1.5px] border-[#18181b] bg-white transition hover:bg-[#f6f6f7] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff] focus-visible:ring-offset-2">
            <FacebookMark className="size-7" />
          </button>
          <button type="button" onClick={() => setNotice(text(copy.socialUnavailable))} aria-label={text(copy.withApple)} className="flex h-14 items-center justify-center rounded-full border-[1.5px] border-[#18181b] bg-white text-black transition hover:bg-[#f6f6f7] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff] focus-visible:ring-offset-2">
            <AppleMark className="size-7" />
          </button>
        </div>

        <p className="mt-10 text-center text-[16px] text-[#6d6d70]">
          {text(copy.existing)} <Link to={authRoute("login", "tester")} className="font-semibold text-[#18181b] hover:underline">{text(copy.signIn)}</Link>
        </p>
      </section>
    </main>
  );
}
