import { AlertCircle, LockKeyhole, WifiOff } from "lucide-react";
import { useAuthLocale } from "@/components/auth/AuthLocale";

export type AuthNoticeKind = "invalid" | "locked" | "offline" | "server" | "expired" | "permission";

const messages: Record<AuthNoticeKind, { title: string; body: string }> = {
  invalid: { title: "We couldn’t sign you in", body: "Check your email and password, then try again." },
  locked: { title: "This account is temporarily locked", body: "Please wait a little before trying again, or contact your administrator." },
  offline: { title: "You appear to be offline", body: "Check your internet connection. Your details have not been submitted." },
  server: { title: "Mediterra is temporarily unavailable", body: "Please try again in a few moments. If the problem continues, contact support." },
  expired: { title: "Your session has ended", body: "For your security, please sign in again." },
  permission: { title: "Your access has changed", body: "Your account permissions have changed. Contact your administrator for help." },
};

export function AuthNotice({ kind }: { kind: AuthNoticeKind }) {
  const message = messages[kind];
  const { language } = useAuthLocale();
  const localized = language === "fr" ? {
    invalid: ["Connexion impossible", "Vérifiez votre e-mail et votre mot de passe, puis réessayez."], locked: ["Ce compte est temporairement bloqué", "Patientez un moment avant de réessayer ou contactez votre administrateur."], offline: ["Vous semblez hors ligne", "Vérifiez votre connexion internet. Vos informations n’ont pas été envoyées."], server: ["Mediterra est temporairement indisponible", "Réessayez dans quelques instants. Si le problème persiste, contactez l’assistance."], expired: ["Votre session est terminée", "Pour votre sécurité, veuillez vous reconnecter."], permission: ["Vos accès ont changé", "Les autorisations de votre compte ont changé. Contactez votre administrateur pour obtenir de l’aide."],
  }[kind] : [message.title, message.body];
  const Icon = kind === "offline" ? WifiOff : kind === "locked" || kind === "permission" ? LockKeyhole : AlertCircle;
  return (
    <div role="alert" className="flex gap-3 rounded-xl border border-[#e0e5eb] bg-[#f8fafc] p-4 text-left">
      <Icon className="mt-0.5 size-5 shrink-0 text-[#0a67c7]" aria-hidden="true" />
      <div><p className="text-[14px] font-semibold text-[#202124]">{localized[0]}</p><p className="mt-1 text-[13px] leading-relaxed text-[#60656d]">{localized[1]}</p></div>
    </div>
  );
}
