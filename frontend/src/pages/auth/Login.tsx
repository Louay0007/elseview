import { useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowRight, LoaderCircle, Mail, ShieldCheck } from "lucide-react";
import { REGEXP_ONLY_DIGITS } from "input-otp";
import { AuthShell } from "@/components/auth/AuthShell";
import { AuthNotice, type AuthNoticeKind } from "@/components/auth/AuthNotice";
import { PasswordField, fieldClassName, labelClassName } from "@/components/auth/AuthFields";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { InputOTP, InputOTPGroup, InputOTPSlot } from "@/components/ui/input-otp";
import { Label } from "@/components/ui/label";
import { isValidEmail, isValidPassword } from "@/lib/auth";
import { useAuthSession } from "@/components/auth/AuthSession";
import { useAuthLocale } from "@/components/auth/AuthLocale";

const knownNotices = new Set<AuthNoticeKind>(["invalid", "locked", "offline", "server", "expired", "permission"]);

export default function LoginPage() {
  const navigate = useNavigate();
  const { completeSession } = useAuthSession();
  const { text } = useAuthLocale();
  const [searchParams] = useSearchParams();
  const requestedNotice = searchParams.get("state") as AuthNoticeKind | null;
  const [notice, setNotice] = useState<AuthNoticeKind | null>(requestedNotice && knownNotices.has(requestedNotice) ? requestedNotice : null);
  const [mfaRequired, setMfaRequired] = useState(false);
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<{ email?: string; password?: string; code?: string }>({});

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const email = String(form.get("email") ?? "");
    const password = String(form.get("password") ?? "");
    const nextErrors = {
      email: isValidEmail(email) ? undefined : "Enter a valid email address.",
      password: isValidPassword(password) ? undefined : "Password must contain at least 12 characters.",
      code: mfaRequired && code.length !== 6 ? "Enter all 6 digits from your authenticator app." : undefined,
    };
    setErrors(nextErrors);
    if (Object.values(nextErrors).some(Boolean)) return;
    if (!navigator.onLine) { setNotice("offline"); return; }

    setNotice(null);
    setLoading(true);
    window.setTimeout(() => {
      setLoading(false);
      if (!mfaRequired) {
        setMfaRequired(true);
        requestAnimationFrame(() => document.getElementById("login-code")?.focus());
      } else {
        completeSession();
        navigate("/", { replace: true });
      }
    }, 650);
  };

  return (
    <AuthShell
      eyebrow={text({ en: "Secure sign in", fr: "Connexion sécurisée" })}
      title={text({ en: "Welcome back.", fr: "Bienvenue." })}
      description={text({ en: "Enter your email and password to continue to Elseview.", fr: "Saisissez votre e-mail et votre mot de passe pour accéder à Elseview." })}
    >
      <form onSubmit={submit} className="space-y-5" noValidate aria-busy={loading}>
        {notice && <AuthNotice kind={notice} />}
        <div>
          <Label className={labelClassName} htmlFor="email">{text({ en: "Email address", fr: "Adresse e-mail" })}</Label>
          <div className="relative mt-2"><Input id="email" name="email" type="email" required autoComplete="email" placeholder="you@example.com" aria-invalid={Boolean(errors.email)} aria-describedby={errors.email ? "email-error" : undefined} className={`${fieldClassName} ps-10 text-base`} /><Mail className="pointer-events-none absolute start-3.5 top-1/2 size-4 -translate-y-1/2 text-[#92969d]" aria-hidden="true" /></div>
          {errors.email && <p id="email-error" className="mt-1.5 text-[13px] text-[#b42318]">{errors.email}</p>}
        </div>

        <div>
          <div className="flex items-center justify-between gap-4"><Label className={labelClassName} htmlFor="password">{text({ en: "Password", fr: "Mot de passe" })}</Label><Link to="/auth/recover" className="text-[13px] font-medium text-[#0a67c7] hover:underline">{text({ en: "Forgot password?", fr: "Mot de passe oublié ?" })}</Link></div>
          <div className="mt-2"><PasswordField /></div>
          {errors.password && <p className="mt-1.5 text-[13px] text-[#b42318]" role="alert">{errors.password}</p>}
        </div>

        {mfaRequired && (
          <div className="rounded-2xl border border-[#cfe2f7] bg-[#f7fbff] p-5" aria-live="polite">
            <div className="flex gap-3"><ShieldCheck className="mt-0.5 size-5 shrink-0 text-[#0a67c7]" aria-hidden="true" /><div><p className="text-[14px] font-semibold text-[#202124]">{text({ en: "One more step", fr: "Une dernière étape" })}</p><p className="mt-1 text-[13px] leading-relaxed text-[#60656d]">{text({ en: "Open your authenticator app and enter the current 6-digit code.", fr: "Ouvrez votre application d’authentification et saisissez le code actuel à 6 chiffres." })}</p></div></div>
            <InputOTP id="login-code" name="mfaCode" value={code} onChange={setCode} maxLength={6} pattern={REGEXP_ONLY_DIGITS} containerClassName="mt-5 justify-center" aria-label="Six-digit authenticator code">
              <InputOTPGroup>{Array.from({ length: 6 }, (_, index) => <InputOTPSlot key={index} index={index} className="h-12 w-11 bg-white text-base sm:w-12" />)}</InputOTPGroup>
            </InputOTP>
            {errors.code && <p className="mt-2 text-center text-[13px] text-[#b42318]" role="alert">{errors.code}</p>}
          </div>
        )}

        <Button type="submit" disabled={loading} className="h-12 w-full rounded-xl bg-[#07172f] text-base text-white hover:bg-[#0a2d5c]">
          {loading ? <><LoaderCircle className="size-4 animate-spin" aria-hidden="true" /> {text({ en: "Please wait…", fr: "Veuillez patienter…" })}</> : <>{mfaRequired ? text({ en: "Verify and continue", fr: "Vérifier et continuer" }) : text({ en: "Sign in", fr: "Se connecter" })}<ArrowRight className="size-4 rtl:rotate-180" aria-hidden="true" /></>}
        </Button>
        <p className="text-center text-[14px] leading-relaxed text-[#686b70]">{text({ en: "New accounts are invitation-only. Open the private link sent by your organization.", fr: "Les nouveaux comptes sont accessibles sur invitation. Ouvrez le lien privé envoyé par votre établissement." })}</p>
      </form>
    </AuthShell>
  );
}
