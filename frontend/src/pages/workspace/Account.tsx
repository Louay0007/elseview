import { useEffect, useMemo, useState } from "react";
import { apiFetch, backendAvailable } from "@/lib/api";
import { Check, ChevronDown, Eye, EyeOff, Lock, MoreVertical, User, X } from "lucide-react";
import { useAuthLocale } from "@/components/auth/AuthLocale";
import { WorkspaceShell, useWorkspaceNav } from "@/components/workspace/WorkspaceShell";
import "@/components/workspace/Account.css";

type AccountForm = {
  firstName: string;
  lastName: string;
  phone: string;
  whatsappNumber: string;
  useWhatsapp: boolean;
  company: string;
  jobRole: string;
  teamSize: string;
};

export default function Account() {
  const { text } = useAuthLocale();
  const { firstName, role, displayName, workspaceName, goWithParams } = useWorkspaceNav();
  const email = useMemo(
    () => `${displayName.toLowerCase().replace(/\s+/g, ".")}.rjili@issatm.ucar.tn`,
    [displayName],
  );
  const initial = useMemo<AccountForm>(
    () => ({
      firstName: firstName || "louay",
      lastName: "rjili",
      phone: "+216 518 037 06",
      whatsappNumber: "+216 518 037 06",
      useWhatsapp: true,
      company: "sohabi",
      jobRole: "Product manager",
      teamSize: "2-5",
    }),
    [firstName],
  );
  const [form, setForm] = useState(initial);
  const [saving, setSaving] = useState(false);
  const [savedTick, setSavedTick] = useState(false);
  const [passwordOpen, setPasswordOpen] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [changing, setChanging] = useState(false);
  const [sessions, setSessions] = useState<{ id: string; expires_at: string }[]>([]);
  const [accountError, setAccountError] = useState<string | null>(null);

  useEffect(() => {
    if (!backendAvailable()) return;
    apiFetch<{ items: { id: string; expires_at: string }[] }>("/me/login-sessions")
      .then((result) => setSessions(result.items ?? []))
      .catch(() => {});
  }, []);

  const canChangePassword =
    currentPassword.length > 0 && newPassword.length >= 8 && confirmPassword === newPassword && !changing;

  useEffect(() => {
    if (!passwordOpen) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setPasswordOpen(false);
    };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [passwordOpen]);

  const closePassword = () => {
    setPasswordOpen(false);
    setCurrentPassword("");
    setNewPassword("");
    setConfirmPassword("");
    setShowCurrent(false);
    setShowNew(false);
    setShowConfirm(false);
  };

  const handleChangePassword = () => {
    if (!canChangePassword) return;
    setChanging(true);
    setAccountError(null);
    if (!backendAvailable()) {
      window.setTimeout(() => { setChanging(false); closePassword(); }, 700);
      return;
    }
    void apiFetch("/auth/password-reset/confirm", {
      method: "POST",
      body: { token: currentPassword, password: newPassword },
    })
      .then(() => closePassword())
      .catch(() => {
        setAccountError(text({ en: "Could not change the password. Check the current one and try again.", fr: "Mot de passe non modifié. Vérifiez l’actuel et réessayez." }));
        setChanging(false);
      });
  };

  const revokeSession = (id: string) => {
    if (!backendAvailable()) return;
    void apiFetch(`/me/login-sessions/${id}`, { method: "DELETE" })
      .then(() => setSessions((current) => current.filter((session) => session.id !== id)))
      .catch(() => setAccountError(text({ en: "Could not revoke that session.", fr: "Session non révoquée." })));
  };

  const dirty = JSON.stringify(form) !== JSON.stringify(initial);
  const canSave =
    dirty &&
    !saving &&
    form.firstName.trim().length > 0 &&
    form.lastName.trim().length > 0 &&
    form.phone.trim().length > 0 &&
    form.whatsappNumber.trim().length > 0 &&
    form.company.trim().length > 0 &&
    form.jobRole.trim().length > 0 &&
    form.teamSize.trim().length > 0;

  const update = (field: keyof AccountForm, value: string | boolean) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const handleSave = () => {
    if (!canSave) return;
    setSaving(true);
    window.setTimeout(() => {
      setSaving(false);
      setSavedTick(true);
      window.setTimeout(() => setSavedTick(false), 2500);
    }, 700);
  };

  return (
      <WorkspaceShell >
      <div className="acc-body">
      <h1 className="acc-title">{text({ en: "Account", fr: "Compte" })}</h1>
      <hr className="acc-rule" />

      <section aria-labelledby="account-details-heading">
      <h2 id="account-details-heading" className="acc-section">
            {text({ en: "Personal details", fr: "Coordonnées personnelles" })}
      </h2>
      <div className="acc-grid">
      <label className="acc-field">
      <span className="acc-field__label">{text({ en: "First name", fr: "Prénom" })}</span>
      <input
                className="acc-input"
                value={form.firstName}
                autoComplete="given-name"
                onChange={(event) => update("firstName", event.target.value)}
              />
      </label>
      <label className="acc-field">
      <span className="acc-field__label">{text({ en: "Last name", fr: "Nom" })}</span>
      <input
                className="acc-input"
                value={form.lastName}
                autoComplete="family-name"
                onChange={(event) => update("lastName", event.target.value)}
              />
      </label>

      <label className="acc-field">
      <span className="acc-field__label">{text({ en: "Phone number", fr: "Numéro de téléphone" })}</span>
      <span className="acc-phone-prefix" aria-hidden="true">
      <span>🇹🇳</span>
      <span>+216</span>
      <ChevronDown className="acc-phone-prefix__chevron" />
      </span>
      <input
                className="acc-input acc-input--phone"
                value={form.phone}
                type="tel"
                inputMode="tel"
                autoComplete="tel-national"
                onChange={(event) => update("phone", event.target.value)}
              />
      </label>
      <label className="acc-field">
      <span className="acc-field__label">{text({ en: "WhatsApp number", fr: "Numéro WhatsApp" })}</span>
      <span className="acc-phone-prefix" aria-hidden="true">
      <span>🇹🇳</span>
      <span>+216</span>
      <ChevronDown className="acc-phone-prefix__chevron" />
      </span>
      <input
                className="acc-input acc-input--phone"
                value={form.whatsappNumber}
                type="tel"
                inputMode="tel"
                autoComplete="tel-national"
                onChange={(event) => update("whatsappNumber", event.target.value)}
              />
      </label>

      <label className="acc-check">
      <input
                type="checkbox"
                checked={form.useWhatsapp}
                onChange={(event) => update("useWhatsapp", event.target.checked)}
              />
      <span className={form.useWhatsapp ? "acc-check__box acc-check__box--on" : "acc-check__box acc-check__box--off"} aria-hidden="true">
      <Check className="acc-icon" strokeWidth={3} />
      </span>
              {text({ en: "I use WhatsApp on this number", fr: "J’utilise WhatsApp sur ce numéro" })}
      </label>
      <span aria-hidden="true" />

      <label className="acc-field">
      <span className="acc-field__label">{text({ en: "Email address", fr: "Adresse e-mail" })}</span>
      <span className="acc-input-wrap">
      <input className="acc-input" value={email} disabled aria-label={text({ en: "Email address", fr: "Adresse e-mail" })} />
      <span className="acc-lock" aria-hidden="true">
      <Lock className="acc-lock__icon" />
      </span>
      </span>
      </label>
      <button type="button" className="acc-change">
              {text({ en: "Change email", fr: "Modifier l’e-mail" })}
      </button>

      <label className="acc-field">
      <span className="acc-field__label">{text({ en: "Company", fr: "Société" })}</span>
      <input
                className="acc-input"
                value={form.company}
                autoComplete="organization"
                onChange={(event) => update("company", event.target.value)}
              />
      </label>
      <label className="acc-field">
      <span className="acc-field__label">{text({ en: "Job role", fr: "Poste" })}</span>
      <span className="acc-input-wrap">
      <input
                  className="acc-input"
                  value={form.jobRole}
                  autoComplete="organization-title"
                  onChange={(event) => update("jobRole", event.target.value)}
                />
                {form.jobRole && (
      <button
                    type="button"
                    className="acc-icon-button"
                    aria-label={text({ en: "Clear job role", fr: "Effacer le poste" })}
                    onClick={() => update("jobRole", "")}
                  >
      <X className="acc-icon" />
      </button>
                )}
      </span>
      </label>

      <label className="acc-field">
      <span className="acc-field__label">{text({ en: "Research & design team size", fr: "Taille de l’équipe recherche et design" })}</span>
      <span className="acc-input-wrap">
      <input
                  className="acc-input"
                  value={form.teamSize}
                  autoComplete="off"
                  onChange={(event) => update("teamSize", event.target.value)}
                />
                {form.teamSize && (
      <button
                    type="button"
                    className="acc-icon-button"
                    aria-label={text({ en: "Clear team size", fr: "Effacer la taille de l’équipe" })}
                    onClick={() => update("teamSize", "")}
                  >
      <X className="acc-icon" />
      </button>
                )}
      </span>
      </label>
      </div>
      <button type="button" className="acc-save" disabled={!canSave} aria-busy={saving} onClick={handleSave}>
            {saving
              ? text({ en: "Saving…", fr: "Enregistrement…" })
              : savedTick
                ? text({ en: "Saved", fr: "Enregistré" })
                : text({ en: "Save updates", fr: "Enregistrer" })}
      </button>
      </section>

      <section aria-labelledby="account-workspaces-heading" className="acc-workspaces">
      <h2 id="account-workspaces-heading" className="acc-section">
            {text({ en: "Workspaces", fr: "Espaces" })}
      </h2>
      <div className="acc-table-head" role="row">
      <span role="columnheader">{text({ en: "Workspaces", fr: "Espaces" })}</span>
      <span role="columnheader">{text({ en: "Role", fr: "Rôle" })}</span>
      <span role="columnheader">{text({ en: "Member since", fr: "Membre depuis" })}</span>
      <span />
      </div>
      <div className="acc-table-row" role="row">
      <div className="acc-workspace" role="rowheader">
      <span className="acc-workspace__avatar">
      <span className="acc-workspace__status" aria-hidden="true" />
      <User className="acc-icon" aria-hidden="true" />
      </span>
      <span>
      <p className="acc-workspace__name">{workspaceName}</p>
      <p className="acc-workspace__type">{text({ en: "Individual workspace", fr: "Espace individuel" })}</p>
      </span>
      </div>
      <p className="acc-table-value" role="cell">{text({ en: "Admin", fr: "Admin" })}</p>
      <p className="acc-table-value" role="cell">25-09-2026</p>
      <button
              type="button"
              className="acc-icon-button acc-row-menu"
              aria-label={text({ en: "Workspace options", fr: "Options de l’espace" })}
            >
      <MoreVertical className="acc-icon" />
      </button>
      </div>
      </section>

      <section aria-labelledby="account-password-heading" className="acc-password">
      <h2 id="account-password-heading" className="acc-section">
            {text({ en: "Change password", fr: "Modifier le mot de passe" })}
      </h2>
      <button type="button" className="acc-password__button" onClick={() => setPasswordOpen(true)}>
      <Lock className="acc-icon" aria-hidden="true" />
            {text({ en: "Change password", fr: "Modifier le mot de passe" })}
      </button>
      </section>

        {sessions.length > 0 && (
      <section aria-labelledby="account-sessions-heading" className="acc-password">
      <h2 id="account-sessions-heading" className="acc-section">
              {text({ en: "Signed-in devices", fr: "Appareils connectés" })}
      </h2>
            {accountError && <p role="alert" className="acc-delete__copy">{accountError}</p>}
      <ul className="acc-sessions">
              {sessions.map((session) => (
      <li key={session.id} className="acc-sessions__row">
      <span className="acc-table-value">{text({ en: "Session", fr: "Session" })} · {session.expires_at}</span>
      <button type="button" className="acc-change" onClick={() => revokeSession(session.id)}>
                    {text({ en: "Revoke", fr: "Révoquer" })}
      </button>
      </li>
              ))}
      </ul>
      </section>
        )}

      <section aria-labelledby="account-delete-heading" className="acc-delete">
      <h2 id="account-delete-heading" className="acc-section">
            {text({ en: "Delete account", fr: "Supprimer le compte" })}
      </h2>
      <p className="acc-delete__copy">
            {text({
              en: "Deleting removes your tests and unused credits.",
              fr: "La suppression retire vos tests et crédits inutilisés.",
            })}{" "}
      <strong>
              {text({ en: "You cannot undo this.", fr: "Action définitive." })}
      </strong>
      </p>
      <button type="button" className="acc-delete__button">
            {text({ en: "Delete account", fr: "Supprimer le compte" })}
      </button>
      </section>
      {passwordOpen && (
      <div
          className="acc-modal"
          role="dialog"
          aria-modal="true"
          aria-label={text({ en: "Change password", fr: "Modifier le mot de passe" })}
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) closePassword();
          }}
        >
      <div className="acc-modal__card">
      <div className="acc-modal__head">
      <h2 className="acc-modal__title">{text({ en: "Change password", fr: "Modifier le mot de passe" })}</h2>
      <button type="button" className="acc-modal__close" aria-label={text({ en: "Close", fr: "Fermer" })} onClick={closePassword}>
      <X className="acc-icon" aria-hidden="true" />
      </button>
      </div>
      <label className="acc-modal__field">
      <input
                type={showCurrent ? "text" : "password"}
                className="acc-modal__input"
                placeholder={text({ en: "Current password", fr: "Mot de passe actuel" })}
                autoComplete="current-password"
                value={currentPassword}
                onChange={(event) => setCurrentPassword(event.target.value)}
              />
      <button
                type="button"
                className="acc-modal__eye"
                aria-label={showCurrent ? text({ en: "Hide password", fr: "Masquer le mot de passe" }) : text({ en: "Show password", fr: "Afficher le mot de passe" })}
                aria-pressed={showCurrent}
                onClick={() => setShowCurrent((value) => !value)}
              >
                {showCurrent ? <EyeOff className="acc-icon" aria-hidden="true" /> : <Eye className="acc-icon" aria-hidden="true" />}
      </button>
      </label>
      <label className="acc-modal__field">
      <input
                type={showNew ? "text" : "password"}
                className="acc-modal__input"
                placeholder={text({ en: "New password", fr: "Nouveau mot de passe" })}
                autoComplete="new-password"
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
              />
      <button
                type="button"
                className="acc-modal__eye"
                aria-label={showNew ? text({ en: "Hide password", fr: "Masquer le mot de passe" }) : text({ en: "Show password", fr: "Afficher le mot de passe" })}
                aria-pressed={showNew}
                onClick={() => setShowNew((value) => !value)}
              >
                {showNew ? <EyeOff className="acc-icon" aria-hidden="true" /> : <Eye className="acc-icon" aria-hidden="true" />}
      </button>
      </label>
      <label className="acc-modal__field">
      <input
                type={showConfirm ? "text" : "password"}
                className="acc-modal__input"
                placeholder={text({ en: "Confirm password", fr: "Confirmer le mot de passe" })}
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
              />
      <button
                type="button"
                className="acc-modal__eye"
                aria-label={showConfirm ? text({ en: "Hide password", fr: "Masquer le mot de passe" }) : text({ en: "Show password", fr: "Afficher le mot de passe" })}
                aria-pressed={showConfirm}
                onClick={() => setShowConfirm((value) => !value)}
              >
                {showConfirm ? <EyeOff className="acc-icon" aria-hidden="true" /> : <Eye className="acc-icon" aria-hidden="true" />}
      </button>
      </label>
            {accountError && <p role="alert" className="acc-delete__copy">{accountError}</p>}
      <button type="button" className="acc-modal__submit" disabled={!canChangePassword} onClick={handleChangePassword}>
              {changing
                ? text({ en: "Saving…", fr: "Enregistrement…" })
                : text({ en: "Change password", fr: "Modifier le mot de passe" })}
      </button>
      </div>
      </div>
      )}
      </div>
      </WorkspaceShell>
  );
}
