import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowLeft, ArrowRight, Check, LoaderCircle, Mail } from "lucide-react";
import { AuthShell } from "@/components/auth/AuthShell";
import { useAuthLocale } from "@/components/auth/AuthLocale";
import { PasswordField, fieldClassName, labelClassName } from "@/components/auth/AuthFields";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { authWords as words, validateAuth, type AuthMode, type AuthField, type AuthIssue } from "@/lib/auth";
import { apiFetch, setAccessToken, setCsrfToken } from "@/lib/api";

const screens = {
  login: { title: words("Welcome back.", "Content de vous revoir."), description: words("Sign in to your Elseview account.", "Connectez-vous à votre compte Elseview."), action: words("Sign in", "Se connecter"), fields: ["email", "password"] },
  signup: { title: words("Start with curiosity.", "Tout commence par une question."), description: words("Create your account. Find a clearer perspective.", "Créez votre compte pour voir plus clair."), action: words("Create account", "Créer mon compte"), fields: ["email", "password"] },
  verify: { title: words("Verify your email.", "Vérifiez votre e-mail."), description: words("Enter the verification code from your email.", "Saisissez le code de vérification reçu par e-mail."), action: words("Verify email", "Vérifier mon e-mail"), fields: ["token"] },
  recover: { title: words("Forgot your password?", "Mot de passe oublié ?"), description: words("Enter your email to request a reset code.", "Indiquez votre e-mail pour demander un code de réinitialisation."), action: words("Send reset instructions", "Envoyer les instructions"), fields: ["email"] },
  reset: { title: words("A fresh start.", "Un nouveau départ."), description: words("Use your reset code to choose a new password.", "Utilisez votre code pour choisir un nouveau mot de passe."), action: words("Reset password", "Réinitialiser le mot de passe"), fields: ["token", "password", "confirmation"] },
  invitation: { title: words("Join your team.", "Rejoignez votre équipe."), description: words("Use your invitation code after signing in with the invited email address.", "Utilisez votre code après connexion avec l’adresse invitée."), action: words("Accept invitation", "Accepter l’invitation"), fields: ["token"] },
} satisfies Record<AuthMode, { title: ReturnType<typeof words>; description: ReturnType<typeof words>; action: ReturnType<typeof words>; fields: AuthField[] }>;
const labels = {
  email: words("Email address", "Adresse e-mail"),
  password: words("Password", "Mot de passe"),
  confirmation: words("Confirm password", "Confirmer le mot de passe"),
  token: words("Email code", "Code reçu par e-mail"),
};
const errors: Record<AuthIssue, ReturnType<typeof words>> = {
  email: words("Enter a valid email, up to 254 characters.", "Saisissez un e-mail valide de 254 caractères maximum."),
  password: words("Use between 12 and 256 characters.", "Utilisez entre 12 et 256 caractères."),
  loginPassword: words("Enter your password (up to 256 characters).", "Saisissez votre mot de passe (256 caractères maximum)."),
  confirmation: words("The passwords do not match.", "Les mots de passe ne correspondent pas."),
  token: words("Enter the complete code (20–256 characters).", "Saisissez le code complet (20 à 256 caractères)."),
};
const success = {
  login: words("Signed in.", "Connecté."),
  signup: words("Next, verify your email.", "Vérifiez ensuite votre e-mail."),
  verify: words("Email verified.", "E-mail vérifié."),
  recover: words("Check your email.", "Consultez votre messagerie."),
  reset: words("Password reset. You are signed out everywhere.", "Mot de passe réinitialisé. Déconnecté partout."),
  invitation: words("Invitation accepted.", "Invitation acceptée."),
};
const next = { login: "/auth/login", signup: "/auth/verify-email", verify: "/auth/complete-profile", recover: "/auth/reset-password", reset: "/auth/login", invitation: "/auth/login" };
const nextLabels = {
  login: words("Explore account preview", "Voir l’aperçu du compte"),
  signup: words("Continue to verification", "Continuer vers la vérification"),
  verify: words("Continue to complete your profile", "Continuer pour compléter votre profil"),
  recover: words("I have a reset code", "J’ai un code de réinitialisation"),
  reset: words("Return to sign in", "Retour à la connexion"),
  invitation: words("View workspace preview", "Voir l’aperçu des espaces"),
};

export const authButtonClass = "min-h-12 h-auto w-full whitespace-normal rounded-lg bg-[#07172f] px-4 py-3 text-[15px] font-semibold text-white shadow-none hover:bg-[#153654] focus-visible:ring-2 focus-visible:ring-[#0a84ff] focus-visible:ring-offset-2";
export const authLinkClass = "inline-flex min-h-11 items-center gap-2 text-sm font-medium text-[#075ca8] underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff] rounded-sm";

export default function AuthFlow({ mode }: { mode: AuthMode }) {
  const { text } = useAuthLocale();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [values, setValues] = useState<Partial<Record<AuthField, string>>>({});
  const [issues, setIssues] = useState<ReturnType<typeof validateAuth>>({});
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [notice, setNotice] = useState<ReturnType<typeof words> | null>(null);
  const [resend, setResend] = useState(mode === "verify" && params.get("resend") === "1");
  const [rememberMe, setRememberMe] = useState(true);
  const form = useRef<HTMLFormElement>(null);
  const result = useRef<HTMLDivElement>(null);
  useEffect(() => { if (done) result.current?.focus(); }, [done]);
  const screen = screens[mode];
  const role = params.get("role") === "tester" ? "tester" : "researcher";
  const roleLabel = role === "tester" ? words("tester", "testeur") : words("researcher", "chercheur");
  const roleLink = (path: string) => `${path}${path.includes("?") ? "&" : "?"}role=${role}`;
  const fields: AuthField[] = resend ? ["email"] : screen.fields;
  const change = (field: AuthField, value: string) => {
    const updated = { ...values, [field]: value };
    setValues(updated);
    setNotice(null);
    if (issues[field]) setIssues(validateAuth(resend ? "recover" : mode, updated));
  };
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (busy) return;
    const found = validateAuth(resend ? "recover" : mode, values);
    setIssues(found);
    const first = fields.find(field => found[field]);
    if (first) { form.current?.querySelector<HTMLInputElement>(`[name="${first}"]`)?.focus(); return; }
    if (!navigator.onLine) {
      setNotice(words("You’re offline. Nothing was submitted. Reconnect and try again.", "Vous êtes hors ligne. Rien n’a été envoyé. Reconnectez-vous et réessayez."));
      return;
    }
    setBusy(true);
    setNotice(null);
    const fail = (message: ReturnType<typeof words>) => {
      setBusy(false);
      setNotice(message);
    };
    const invalidCode = words("This code is invalid or expired. Request a new one.", "Ce code est invalide ou expiré. Demandez-en un nouveau.");
    const serverError = words("Service unavailable. Try again shortly.", "Service indisponible. Réessayez dans un instant.");
    const rateLimited = words("Too many attempts. Wait a minute before retrying.", "Trop de tentatives. Patientez une minute.");
    const offlineBackend = words("Can’t reach the server. Start the backend and try again.", "Serveur injoignable. Démarrez le backend et réessayez.");
    void (async () => {
      try {
        if (mode === "signup") {
          await apiFetch("/auth/register", { method: "POST", body: { email: values.email, password: values.password, display_name: "" } });
          navigate(role === "tester" ? `/tester?role=tester` : `/auth/verify-email?email=${encodeURIComponent(values.email ?? "")}&role=${role}`);
          return;
        }
        if (mode === "login") {
          const result = await apiFetch<{ access_token: string; csrf_token: string }>("/auth/login", { method: "POST", body: { email: values.email, password: values.password } });
          setAccessToken(result.access_token);
          setCsrfToken(result.csrf_token);
          navigate(roleLink("/account"));
          return;
        }
        if (mode === "verify") {
          if (resend) {
            await apiFetch("/auth/verification/request", { method: "POST", body: { email: values.email } });
          } else {
            await apiFetch("/auth/verify-email", { method: "POST", body: { token: values.token } });
          }
          setValues({});
          setDone(true);
          return;
        }
        if (mode === "recover") {
          await apiFetch("/auth/password-reset/request", { method: "POST", body: { email: values.email } });
          setValues({});
          setDone(true);
          return;
        }
        if (mode === "reset") {
          await apiFetch("/auth/password-reset/confirm", { method: "POST", body: { token: values.token, password: values.password } });
          setValues({});
          setDone(true);
          return;
        }
        if (mode === "invitation") {
          await apiFetch("/workspace-invitations/accept", { method: "POST", body: { token: values.token } });
          setValues({});
          setDone(true);
          return;
        }
      } catch (cause) {
        const message = cause instanceof Error ? cause.message : "";
        if (/\(401\)|\(404\)|\(422\)/.test(message)) {
          if (mode === "login") fail(words("Unable to sign in. Check your details or request email verification.", "Connexion impossible. Vérifiez vos informations ou demandez une vérification e-mail."));
          else fail(invalidCode);
        } else if (/\(429\)/.test(message)) fail(rateLimited);
        else if (/Failed to fetch|Load failed|NetworkError/i.test(message)) fail(offlineBackend);
        else fail(serverError);
        return;
      } finally {
        setBusy(false);
      }
    })();
  };

  const shellTitle = mode === "login" ? <>{text(words("Sign in to your ", "Connectez-vous à votre compte "))}<span className="text-[#183a68]">{text(roleLabel)}</span>{text(words(" account", ""))}</> : mode === "signup" ? <>{text(words("Create a ", "Créez un compte "))}<span className="text-[#183a68]">{text(roleLabel)}</span>{text(words(" account", ""))}</> : text(resend ? words("Request a new code.", "Demandez un nouveau code.") : screen.title);
  const shellDescription = mode === "login" ? "" : mode === "signup" ? text(words("It’s free to sign up, no credit card needed.", "L’inscription est gratuite, sans carte bancaire.")) : text(resend ? words("Enter the email used to create your account.", "Indiquez l’e-mail utilisé pour créer votre compte.") : screen.description);
  if (mode === "verify" && !resend) {
    const email = params.get("email") || text(words("your email address", "votre adresse e-mail"));
    return <AuthShell title="" description="" wide>
      <div className="rounded-[20px] bg-white px-6 py-9 text-center shadow-[0_12px_40px_rgba(7,23,47,0.10)] sm:px-12 sm:py-11">
        <Mail className="mx-auto size-8 text-[#183a68]" strokeWidth={1.7} aria-hidden="true" />
        <h1 className="mt-8 text-[24px] font-semibold tracking-[-0.04em] text-[#18181b] sm:text-[27px]">{text(words("Please verify your email", "Veuillez vérifier votre e-mail"))}</h1>
        <p className="mx-auto mt-6 max-w-[420px] text-[14px] leading-[1.65] text-[#77797d]">{text(words("You’re almost there! We sent you an email to", "Vous y êtes presque ! Nous vous avons envoyé un e-mail à"))}</p>
        <p className="mt-1 break-all text-[14px] font-semibold text-[#18181b]">{email}</p>
        <p className="mx-auto mt-5 max-w-[440px] text-[14px] leading-[1.65] text-[#77797d]">{text(words("Just click on the link in that email to complete your signup.", "Cliquez sur le lien dans cet e-mail pour terminer votre inscription."))}<br />{text(words("If you don’t see it, you may need to", "Si vous ne le voyez pas, pensez à"))} <strong className="text-[#18181b]">{text(words("check your spam folder.", "vérifier votre dossier spam."))}</strong></p>
        <p className="mt-7 text-[14px] text-[#77797d]">{text(words("Still can’t see it?", "Vous ne le voyez toujours pas ?"))}</p>
        <Button type="button" onClick={() => setResend(true)} className="mt-5 h-12 rounded-full bg-black px-7 text-[14px] hover:bg-[#07172f]">{text(words("Resend email", "Renvoyer l’e-mail"))}</Button>
        <div className="mt-8 flex items-center justify-between gap-4 text-[13px] text-[#77797d]">
          <Link to={roleLink("/auth/login")} className="font-medium hover:text-[#183a68]">{text(words("Back to", "Retour à"))} <strong className="text-[#18181b]">{text(words("Sign in", "Se connecter"))}</strong></Link>
          <span>{text(words("Need help?", "Besoin d’aide ?"))} <a href="mailto:support@elseview.test" className="font-medium text-[#183a68] underline">{text(words("Contact support", "Contacter l’assistance"))}</a></span>
        </div>
      </div>
    </AuthShell>;
  }
  return <AuthShell title={shellTitle} documentTitle={mode === "login" ? text(words(`Sign in to your ${role} account`, role === "tester" ? "Connectez-vous à votre compte testeur" : "Connectez-vous à votre compte chercheur")) : mode === "signup" ? text(words(`Create a ${role} account`, role === "tester" ? "Créez un compte testeur" : "Créez un compte chercheur")) : text(screen.title)} description={shellDescription}>
    {done ? <div ref={result} tabIndex={-1} className="space-y-5 text-center outline-none" role="status">
      <span className="mx-auto grid size-12 place-items-center rounded-full bg-[#edf6f0] text-[#216440]"><Check aria-hidden="true" size={24} /></span>
      <h2 className="text-xl tracking-normal">{text(resend ? words("Request sent.", "Demande envoyée.") : success[mode])}</h2>
      <p className="text-sm leading-relaxed text-[#626870]">{text(mode === "recover" || resend ? words("If the request is eligible, instructions will be delivered.", "Si la demande est éligible, des instructions seront envoyées.") : words("Done. Continue to the next step.", "Terminé. Passez à l’étape suivante."))}</p>
      {mode === "reset" && <p className="text-sm text-[#626870]">{text(words("A real password reset signs you out of all sessions.", "Une réinitialisation réelle déconnecte toutes vos sessions."))}</p>}
      <Button asChild className={authButtonClass}><Link to={resend ? roleLink("/auth/verify-email") : roleLink(next[mode])} onClick={() => { if (resend) { setDone(false); setResend(false); } }}>{text(resend ? nextLabels.signup : nextLabels[mode])}<ArrowRight size={16} aria-hidden="true" className="rtl:rotate-180" /></Link></Button>
    </div> : <form ref={form} onSubmit={submit} noValidate aria-busy={busy} className="space-y-5">
      {notice && <div role="alert" className="rounded-lg bg-[#fff2ef] px-4 py-3 text-sm leading-relaxed text-[#9c2d20]">{text(notice)}</div>}
      {fields.map(field => {
        const issue = issues[field];
        const hint = field === "token" ? text(words("Paste the full code, not a 6-digit authenticator code.", "Collez le code complet, pas un code d’authentification à 6 chiffres.")) : field === "password" && mode !== "login" ? text(errors.password) : undefined;
        return <div key={field}>
          <div className="mb-2 flex items-center justify-between gap-3"><label className={labelClassName} htmlFor={field}>{text(field === "token" && mode === "invitation" ? words("Invitation code", "Code d’invitation") : labels[field])}</label></div>
          {field === "password" || field === "confirmation" ? <PasswordField id={field} name={field} value={values[field] ?? ""} onChange={event=>change(field,event.target.value)} disabled={busy} minLength={mode === "login" ? 1 : 12} autoComplete={mode === "login" ? "current-password" : "new-password"} hint={hint} aria-invalid={Boolean(issue)} aria-describedby={[hint ? `${field}-hint` : "", issue ? `${field}-error` : ""].filter(Boolean).join(" ") || undefined} /> : <Input id={field} name={field} value={values[field] ?? ""} onChange={event=>change(field,event.target.value)} disabled={busy} required type={field === "email" ? "email" : "text"} maxLength={field === "email" ? 254 : 256} autoComplete={field === "email" ? "email" : "off"} spellCheck={false} dir={field === "token" || field === "email" ? "ltr" : undefined} className={fieldClassName} aria-invalid={Boolean(issue)} aria-describedby={issue ? `${field}-error` : hint ? `${field}-hint` : undefined} />}
          {hint && field === "token" && <p id={`${field}-hint`} className="mt-2 text-xs leading-relaxed text-[#626870]">{hint}</p>}
          {issue && <p id={`${field}-error`} className="mt-2 text-xs text-[#b42318]" role="alert">{text(errors[issue])}</p>}
        </div>;
      })}
      {mode === "login" && <div className="flex items-center justify-between gap-4 text-[15px] text-[#6d6d70]">
        <label className="inline-flex min-h-11 items-center gap-3">
          <input type="checkbox" checked={rememberMe} onChange={event => setRememberMe(event.target.checked)} className="size-5 accent-[#ff61ad]" />
          {text(words("Remember me", "Se souvenir de moi"))}
        </label>
        <Link to={roleLink("/auth/recover")} className="min-h-11 inline-flex items-center hover:text-[#183a68]">{text(words("Forgot password?", "Mot de passe oublié ?"))}</Link>
      </div>}
      <Button disabled={busy} className={`${authButtonClass} ${mode === "login" ? "rounded-full bg-[#d9d9da] text-white hover:bg-[#c9c9ca]" : ""}`} type="submit">{busy ? <><LoaderCircle size={16} className="animate-spin motion-reduce:animate-none" aria-hidden="true" />{text(words("Please wait…", "Veuillez patienter…"))}</> : <>{text(resend ? words("Send verification instructions", "Envoyer les instructions") : screen.action)}<ArrowRight size={16} aria-hidden="true" className="rtl:rotate-180" /></>}</Button>

      {mode === "login" && <div className="text-center text-sm text-[#626870]"><span>{text(words("New to Elseview?", "Nouveau sur Elseview ?"))} </span><Link to={roleLink("/auth/signup")} className={authLinkClass}>{text(words("Create an account", "Créer un compte"))}</Link><div><Link to={roleLink("/auth/verify-email?resend=1")} className={authLinkClass}>{text(words("Verify your email", "Vérifier votre e-mail"))}</Link></div></div>}
      {mode === "signup" && <p className="text-center text-sm text-[#626870]">{text(words("Already have an account?", "Déjà un compte ?"))} <Link to={roleLink("/auth/login")} className={authLinkClass}>{text(screens.login.action)}</Link></p>}
      {mode === "verify" && <div className="text-center"><button disabled={busy} type="button" className={authLinkClass} onClick={()=>{setResend(!resend);setIssues({});setNotice(null);}}>{text(resend ? words("I already have a code", "J’ai déjà un code") : words("Request a new code", "Demander un nouveau code"))}</button></div>}
      {mode === "reset" && <div className="text-center"><Link to={roleLink("/auth/recover")} className={authLinkClass}>{text(words("Request a new reset code", "Demander un nouveau code"))}</Link></div>}
      {mode === "invitation" && <p className="text-center text-sm text-[#626870]">{text(words("Wrong account?", "Mauvais compte ?"))} <Link to={roleLink("/auth/login")} className={authLinkClass}>{text(screens.login.action)}</Link></p>}
    </form>}
    {mode !== "login" && <div className="mt-4 text-center"><Link to={roleLink("/auth/login")} className={authLinkClass}><ArrowLeft size={15} aria-hidden="true" className="rtl:rotate-180" />{text(words("Back to sign in", "Retour à la connexion"))}</Link></div>}
  </AuthShell>;
}