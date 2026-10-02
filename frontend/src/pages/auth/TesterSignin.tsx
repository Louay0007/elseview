import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft, Eye, EyeOff, LoaderCircle } from "lucide-react";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { useAuthLocale } from "@/components/auth/AuthLocale";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { MediterraLogo } from "@/components/MediterraLogo";
import { authWords as words, validateAuth } from "@/lib/auth";
import { apiFetch, setAccessToken, setCsrfToken } from "@/lib/api";
import { AppleMark, FacebookMark, GoogleMark } from "@/pages/auth/TesterSignup";
import { authRoute, routes } from "@/lib/routes";

const copy = {
  titleA: words("Sign in to your ", "Connectez-vous à votre compte "),
  titleB: words("tester", "testeur"),
  titleC: words(" account", ""),
  emailPlaceholder: words("Email address", "Adresse e-mail"),
  passwordPlaceholder: words("Password", "Mot de passe"),
  required: words("Required field", "Champ requis"),
  emailInvalid: words("Enter a valid email, up to 254 characters.", "Saisissez un e-mail valide de 254 caractères maximum."),
  showPassword: words("Show password", "Afficher le mot de passe"),
  hidePassword: words("Hide password", "Masquer le mot de passe"),
  remember: words("Remember me", "Se souvenir de moi"),
  forgot: words("Forgot password?", "Mot de passe oublié ?"),
  submit: words("Sign in", "Se connecter"),
  waiting: words("Please wait…", "Veuillez patienter…"),
  or: words("Or", "Ou"),
  withGoogle: words("Continue with Google", "Continuer avec Google"),
  withFacebook: words("Continue with Facebook", "Continuer avec Facebook"),
  withApple: words("Continue with Apple", "Continuer avec Apple"),
  socialUnavailable: words("Social sign-in isn’t available yet — continue with email.", "La connexion sociale n’est pas encore disponible — continuez avec votre e-mail."),
  signInFailed: words("Unable to sign in. Check your details or request email verification.", "Connexion impossible. Vérifiez vos informations ou demandez une vérification e-mail."),
  serverError: words("Service unavailable. Try again shortly.", "Service indisponible. Réessayez dans un instant."),
  offlineBackend: words("Can’t reach the server. Start the backend and try again.", "Serveur injoignable. Démarrez le backend et réessayez."),
  offline: words("You’re offline. Nothing was submitted. Reconnect and try again.", "Vous êtes hors ligne. Rien n’a été envoyé. Reconnectez-vous et réessayez."),
  existing: words("You don't have an account?", "Vous n’avez pas de compte ?"),
  signUp: words("Sign up", "Créer un compte"),
  home: words("Home", "Accueil"),
};

export default function TesterSignin() {
  const { text } = useAuthLocale();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [visible, setVisible] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [touchedEmail, setTouchedEmail] = useState(false);
  const [touchedPassword, setTouchedPassword] = useState(false);
  const [attempted, setAttempted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => { document.title = `${text(words("Sign in to your tester account", "Connectez-vous à votre compte testeur"))} | Elseview`; }, [text]);

  const issues = validateAuth("login", { email, password });
  const canSubmit = !issues.email && !issues.password && !busy;

  const showEmailError = (touchedEmail || attempted) && Boolean(issues.email);
  const showPasswordError = (touchedPassword || attempted) && Boolean(issues.password);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    setAttempted(true);
    setNotice(null);
    if (issues.email || issues.password) return;
    if (!navigator.onLine) {
      setNotice(text(copy.offline));
      return;
    }
    setBusy(true);
    void (async () => {
      try {
        const result = await apiFetch<{ access_token: string; csrf_token: string }>("/auth/login", { method: "POST", body: { email, password } });
        setAccessToken(result.access_token);
        setCsrfToken(result.csrf_token);
        // Testers land in the tester space. `/account` is the researcher
        // workspace page and exposes controls a tester must never see.
        navigate(routes.tester);
      } catch (cause) {
        const message = cause instanceof Error ? cause.message : "";
        if (/\(401\)|\(404\)|\(422\)/.test(message)) setNotice(text(copy.signInFailed));
        else if (/Failed to fetch|Load failed|NetworkError/i.test(message)) setNotice(text(copy.offlineBackend));
        else setNotice(text(copy.serverError));
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

        <form onSubmit={submit} noValidate className="mt-8 space-y-6">
          {notice && <div role="alert" className="rounded-xl bg-[#fff2ef] px-4 py-3 text-sm leading-relaxed text-[#9c2d20]">{notice}</div>}
          <div>
            <label htmlFor="tester-login-email" className="sr-only">{text(copy.emailPlaceholder)}</label>
            <Input
              id="tester-login-email"
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
            <label htmlFor="tester-login-password" className="sr-only">{text(copy.passwordPlaceholder)}</label>
            <div className="relative">
              <Input
                id="tester-login-password"
                name="password"
                type={visible ? "text" : "password"}
                autoComplete="current-password"
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
            {showPasswordError && <p role="alert" className="mt-2 text-[14px] text-[#f04438]">{text(copy.required)}</p>}
          </div>

          <div className="flex min-h-11 items-center justify-between gap-4">
            <label className="inline-flex cursor-pointer items-center gap-3 text-[16px] text-[#6d6d70]">
              <Checkbox
                checked={rememberMe}
                onCheckedChange={(value) => setRememberMe(value === true)}
                aria-label={text(copy.remember)}
                className="size-6 shrink-0 rounded-[7px] border-2 border-[#c4c9d1] bg-white data-[state=checked]:border-[#1d4ed8] data-[state=checked]:bg-[#1d4ed8] data-[state=checked]:text-white [&_svg]:size-4"
              />
              {text(copy.remember)}
            </label>
            <Link to={authRoute("recover", "tester")} className="inline-flex min-h-11 items-center text-[16px] text-[#6d6d70] hover:text-[#18181b]">{text(copy.forgot)}</Link>
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
          {text(copy.existing)} <Link to={authRoute("signup", "tester")} className="font-semibold text-[#18181b] hover:underline">{text(copy.signUp)}</Link>
        </p>
      </section>
    </main>
  );
}
