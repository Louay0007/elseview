import { useEffect, useState } from "react";
import { apiFetch, backendAvailable, newIdempotencyKey } from "@/lib/api";
import { useWorkspace } from "@/components/workspace/WorkspaceContext";
import { Link } from "react-router-dom";
import { Check, ChevronDown, Coins, Facebook, Link2, Twitter, UserPlus, Waypoints, MessageCircle } from "lucide-react";
import { useAuthLocale } from "@/components/auth/AuthLocale";
import { WorkspaceShell, useWorkspaceNav } from "@/components/workspace/WorkspaceShell";
import "@/components/workspace/Refer.css";

export default function Refer() {
  const { text } = useAuthLocale();
  const { firstName, role, displayName, workspaceName, goWithParams } = useWorkspaceNav();
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [earnings, setEarnings] = useState(0);
  const [referError, setReferError] = useState<string | null>(null);
  const { workspaceId } = useWorkspace();

  useEffect(() => {
    if (!backendAvailable() || !workspaceId) return;
    apiFetch<{ items: { amount: number }[] }>(`/workspaces/${workspaceId}/billing/credits`)
      .then((result) => setEarnings((result.items ?? []).reduce((total, item) => total + (item.amount || 0), 0)))
      .catch(() => {});
  }, [workspaceId]);
  const [copied, setCopied] = useState(false);
  const personalLink = `https://app.elseview.com/researcher/sign-up?ref=${displayName.toLowerCase().replace(/\s+/g, "-")}`;
  const emailValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());

  const handleSend = () => {
    if (!emailValid) return;
    setReferError(null);
    if (!backendAvailable() || !workspaceId) {
      setSent(true);
      window.setTimeout(() => setSent(false), 2500);
      return;
    }
    void apiFetch(`/workspaces/${workspaceId}/recruiting/contacts/import`, {
      method: "POST",
      idempotencyKey: newIdempotencyKey(),
      body: { contacts: [{ email: email.trim() }] },
    })
      .then(() => {
        setSent(true);
        setEmail("");
        window.setTimeout(() => setSent(false), 2500);
      })
      .catch(() => setReferError(text({ en: "Invite not sent. Try again.", fr: "Invitation non envoyée. Réessayez." })));
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(personalLink);
    } catch {
      const area = document.createElement("textarea");
      area.value = personalLink;
      document.body.appendChild(area);
      area.select();
      document.execCommand("copy");
      document.body.removeChild(area);
    }
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  };

  return (
    <WorkspaceShell
      workspaceName={workspaceName}
      displayName={displayName}
      firstName={firstName}
      role={role}
      onSettings={() => goWithParams("/settings")}
      onBilling={() => goWithParams("/workspace/billing")}
      onCredits={() => goWithParams("/workspace/credits")}
      onAccount={() => goWithParams("/account")}
      onNotifications={() => goWithParams("/account/notifications")}
      onRefer={() => goWithParams("/account/refer")}
    >
      <div className="refer-grid">
        <section className="refer-hero" aria-labelledby="refer-hero-heading">
          <h1 id="refer-hero-heading" className="refer-hero__title">
            {text({ en: "Invite friends & earn 200 credits!", fr: "Invitez vos amis et gagnez 200 crédits !" })}
          </h1>
          <div className="refer-hero__icons" aria-hidden="true">
            <UserPlus className="refer-hero__icon" strokeWidth={1.4} />
            <Waypoints className="refer-hero__icon" strokeWidth={1.4} />
            <Coins className="refer-hero__icon" strokeWidth={1.4} />
          </div>
          <p className="refer-hero__copy">
            {text({
              en: "Invite researchers to register with Elseview. When they make their first purchase, you get 200 credits for tests and recruitment.",
              fr: "Invitez des chercheurs à s’inscrire sur Elseview. Dès leur premier achat, vous recevez 200 crédits pour tests et recrutement.",
            })}
          </p>
        </section>

        <section className="refer-card" aria-labelledby="refer-card-heading">
          <h2 id="refer-card-heading" className="refer-card__earnings">
            {text({ en: "Total earnings:", fr: "Gains totaux :" })}{" "}
            <span className="refer-card__count">{earnings}</span>{" "}
            <span className="refer-card__unit">{text({ en: "credits", fr: "crédits" })}</span>
          </h2>

          <h3 className="refer-card__label">{text({ en: "Choose workspace", fr: "Choisir l’espace" })}</h3>
          <p className="refer-card__hint">
            {text({
              en: "Pick where your credits go.",
              fr: "Choisissez où vont vos crédits.",
            })}
          </p>
          <label className="refer-field">
            <span className="refer-field__tag">{text({ en: "Workspace", fr: "Espace" })}</span>
            <span className="refer-select">
              <span className="refer-select__value">{workspaceName}</span>
              <ChevronDown className="refer-select__chev" aria-hidden="true" />
            </span>
          </label>

          <h3 className="refer-card__label">{text({ en: "Invite your friends", fr: "Invitez vos amis" })}</h3>
          {referError && <p role="alert" className="refer-error">{referError}</p>}
          {sent && <p role="status" className="refer-sent">{text({ en: "Invite sent.", fr: "Invitation envoyée." })}</p>}
          <div className="refer-row">
            <input
              type="email"
              className="refer-input"
              placeholder={text({ en: "Email address", fr: "Adresse e-mail" })}
              aria-label={text({ en: "Email address", fr: "Adresse e-mail" })}
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
            <button type="button" className="refer-send" disabled={!emailValid} onClick={handleSend}>
              {sent
                ? <Check className="refer-send__icon" aria-hidden="true" />
                : text({ en: "Send", fr: "Envoyer" })}
            </button>
          </div>

          <h3 className="refer-card__label">{text({ en: "Or share your personal link", fr: "Ou partagez votre lien personnel" })}</h3>
          <div className="refer-row">
            <button type="button" className="refer-link" onClick={handleCopy} title={personalLink}>
              <span className="refer-link__text">{personalLink}</span>
              {copied
                ? <Check className="refer-link__icon" aria-hidden="true" />
                : <Link2 className="refer-link__icon" aria-hidden="true" />}
            </button>
            <div className="refer-social" role="group" aria-label={text({ en: "Share", fr: "Partager" })}>
              <a className="refer-social__btn refer-social__btn--fb" href={`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(personalLink)}`} target="_blank" rel="noreferrer" aria-label="Facebook">
                <Facebook className="refer-social__icon" aria-hidden="true" />
              </a>
              <a className="refer-social__btn refer-social__btn--x" href={`https://twitter.com/intent/tweet?url=${encodeURIComponent(personalLink)}`} target="_blank" rel="noreferrer" aria-label="X">
                <Twitter className="refer-social__icon" aria-hidden="true" />
              </a>
              <a className="refer-social__btn refer-social__btn--wa" href={`https://wa.me/?text=${encodeURIComponent(personalLink)}`} target="_blank" rel="noreferrer" aria-label="WhatsApp">
                <MessageCircle className="refer-social__icon" aria-hidden="true" />
              </a>
            </div>
          </div>
          <p className="refer-terms">
            <Link to="/terms" className="refer-terms__link">
              {text({ en: "Terms of use", fr: "Conditions d’utilisation" })}
            </Link>
          </p>
        </section>
      </div>
    </WorkspaceShell>
  );
}
