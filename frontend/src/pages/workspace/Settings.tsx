import { useEffect, useState, type FormEvent } from "react";
import { apiFetch, backendAvailable, newIdempotencyKey } from "@/lib/api";
import { useWorkspace } from "@/components/workspace/WorkspaceContext";
import { Plus, Trash2, Users, X } from "lucide-react";
import { useAuthLocale } from "@/components/auth/AuthLocale";
import { WorkspaceShell, useWorkspaceNav } from "@/components/workspace/WorkspaceShell";
import "@/components/workspace/Settings.css";

const MAX_NAME = 30;

export default function Settings() {
  const { text } = useAuthLocale();
  const { firstName, role, displayName, workspaceName, goWithParams } = useWorkspaceNav();
  const initialWorkspace = workspaceName;

  const [name, setName] = useState(initialWorkspace);
  const [saving, setSaving] = useState(false);
  const [savedTick, setSavedTick] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmText, setConfirmText] = useState("");
  const [members, setMembers] = useState<{ id: string; role: string; status: string }[]>([]);
  const [audit, setAudit] = useState<{ id: string; action: string; created_at: string }[]>([]);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteOpen, setInviteOpen] = useState(false);
  const [settingsError, setSettingsError] = useState<string | null>(null);
  const { workspaceId } = useWorkspace();

  useEffect(() => {
    if (!backendAvailable() || !workspaceId) return;
    apiFetch<{ items: { id: string; role: string; status: string }[] }>(`/workspaces/${workspaceId}/members`)
      .then((result) => setMembers(result.items ?? []))
      .catch(() => {});
    apiFetch<{ items: { id: string; action: string; created_at: string }[] }>(`/workspaces/${workspaceId}/audit`)
      .then((result) => setAudit(result.items ?? []))
      .catch(() => {});
  }, [workspaceId]);

  const sendInvite = (event: FormEvent) => {
    event.preventDefault();
    if (!workspaceId || !inviteEmail.trim()) return;
    setSettingsError(null);
    void apiFetch(`/workspaces/${workspaceId}/invitations`, {
      method: "POST",
      idempotencyKey: newIdempotencyKey(),
      body: { email: inviteEmail.trim(), role: "researcher" },
    })
      .then(() => { setInviteEmail(""); setInviteOpen(false); })
      .catch(() => setSettingsError(text({ en: "Could not send the invite. Try again.", fr: "Invitation non envoyée. Réessayez." })));
  };

  const trimmed = name.trim();
  const tooLong = name.length > MAX_NAME;
  const empty = trimmed.length === 0;
  const dirty = trimmed !== initialWorkspace;
  const canSave = dirty && !empty && !tooLong && !saving;
  const error = empty
    ? text({ en: "Enter a workspace name.", fr: "Saisissez un nom d’espace." })
    : tooLong
      ? text({ en: "Use 30 characters or less.", fr: "30 caractères maximum." })
      : null;

  const handleSave = () => {
    if (!canSave) return;
    setSaving(true);
    window.setTimeout(() => {
      setSaving(false);
      setSavedTick(true);
      window.setTimeout(() => setSavedTick(false), 2500);
    }, 700);
  };

  const confirmReady = confirmText.trim() === initialWorkspace;

  return (
      <WorkspaceShell >
      <div className="stg-body">
      <h1 className="stg-title">{text({ en: "Settings", fr: "Réglages" })}</h1>
      <hr className="stg-rule" />

      <div className="stg-name-row">
      <div className="stg-field">
      <label className="stg-floating" htmlFor="workspace-name">
      <span className="stg-floating__text">{text({ en: "Workspace name", fr: "Nom de l'espace" })}</span>
      <input
                id="workspace-name"
                className="stg-input"
                value={name}
                maxLength={MAX_NAME + 10}
                onChange={(e) => setName(e.target.value)}
                onBlur={() => setName((v) => v.trim())}
                autoComplete="off"
                aria-invalid={error ? true : undefined}
                aria-describedby={error ? "workspace-name-error" : "workspace-name-count"}
              />
      </label>
            {error
              ? <p id="workspace-name-error" role="alert" className="stg-error">{error}</p>
              : <p id="workspace-name-count" className="stg-count">{name.length}/{MAX_NAME}</p>}
      </div>
      <button
            type="button"
            className="stg-save"
            disabled={!canSave}
            aria-busy={saving}
            onClick={handleSave}
          >
            {saving
              ? text({ en: "Saving…", fr: "Enregistrement…" })
              : savedTick
                ? text({ en: "Saved", fr: "Enregistré" })
                : text({ en: "Save", fr: "Enregistrer" })}
      </button>
      </div>

        {settingsError && <p role="alert" className="stg-error">{settingsError}</p>}
      <h2 className="stg-section">{text({ en: "Workspace team members", fr: "Membres de l'espace" })}</h2>
        {members.length > 0 ? (
      <ul className="stg-members">
            {members.map((member) => (
      <li key={member.id} className="stg-members__row">
      <span className="stg-members__role">{member.role} · {member.status}</span>
      </li>
            ))}
      </ul>
        ) : null}
        {inviteOpen ? (
      <form onSubmit={sendInvite} className="stg-invite">
      <label htmlFor="invite-email" className="stg-floating__text">{text({ en: "Email to invite", fr: "E-mail à inviter" })}</label>
      <input id="invite-email" type="email" value={inviteEmail} onChange={(event) => setInviteEmail(event.target.value)} className="stg-input" placeholder={text({ en: "name@company.com", fr: "nom@société.com" })} />
      <button type="submit" className="stg-save">{text({ en: "Send invite", fr: "Envoyer" })}</button>
      </form>
        ) : (
      <button type="button" className="stg-pill" onClick={() => setInviteOpen(true)}>
            {text({ en: "Invite a member", fr: "Inviter un membre" })}
      </button>
        )}
        {audit.length > 0 ? (
      <ul className="stg-audit">
            {audit.slice(0, 10).map((event) => (
      <li key={event.id} className="stg-audit__row">{event.action} · {event.created_at}</li>
            ))}
      </ul>
        ) : null}
      <div className="stg-upgrade">
      <p className="stg-upgrade__text">
            {text({ en: "Team plan lets you add members to this workspace.", fr: "Le plan Équipe permet d’ajouter des membres à cet espace." })}
      </p>
      <div className="stg-upgrade__actions">
      <button type="button" className="stg-pill">
      <Users className="stg-pill__icon" strokeWidth={1.8} aria-hidden="true" />
              {text({ en: "Upgrade workspace", fr: "Améliorer l'espace" })}
      </button>
      <button type="button" className="stg-pill">
      <Plus className="stg-pill__icon" strokeWidth={1.8} aria-hidden="true" />
              {text({ en: "Create new Team workspace", fr: "Créer un espace Équipe" })}
      </button>
      </div>
      </div>

      <h2 className="stg-section">{text({ en: "Delete workspace", fr: "Supprimer l'espace" })}</h2>
      <p className="stg-delete-desc">
          {text({ en: "Deleting removes all tests and unused credits in this workspace.", fr: "La suppression retire tous les tests et crédits inutilisés de cet espace." })}
      <strong className="stg-delete-warn">
            {text({ en: "This action cannot be undone.", fr: "Cette action est définitive." })}
      </strong>
      </p>
      <button type="button" className="stg-delete" onClick={() => { setConfirmText(""); setConfirmOpen(true); }}>
      <Trash2 className="stg-delete__icon" strokeWidth={1.8} aria-hidden="true" />
          {text({ en: "Delete workspace", fr: "Supprimer l'espace" })}
      </button>
      </div>

      {confirmOpen && (
      <div className="stg-modal" role="dialog" aria-modal="true" aria-labelledby="stg-delete-title">
      <button type="button" className="stg-modal__scrim" aria-label={text({ en: "Close", fr: "Fermer" })} onClick={() => setConfirmOpen(false)} />
      <div className="stg-modal__card">
      <button type="button" className="stg-modal__close" aria-label={text({ en: "Close", fr: "Fermer" })} onClick={() => setConfirmOpen(false)}>
      <X className="size-5" strokeWidth={1.6} />
      </button>
      <h2 id="stg-delete-title">{text({ en: "Delete this workspace?", fr: "Supprimer cet espace ?" })}</h2>
      <p>
              {text({
                en: `This removes all tests and unused credits in ${initialWorkspace}. You cannot undo this.`,
                fr: `Cela retire tous les tests et crédits de ${initialWorkspace}. Action définitive.`,
              })}
      </p>
      <label className="stg-modal__label" htmlFor="stg-confirm-name">
              {text({ en: `Type ${initialWorkspace} to confirm`, fr: `Écrivez ${initialWorkspace} pour confirmer` })}
      </label>
      <input
              id="stg-confirm-name"
              className="stg-modal__input"
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              autoComplete="off"
              placeholder={initialWorkspace}
            />
      <div className="stg-modal__actions">
      <button type="button" className="stg-pill stg-pill--dark" autoFocus onClick={() => setConfirmOpen(false)}>
                {text({ en: "Keep workspace", fr: "Garder l'espace" })}
      </button>
      <button type="button" className="stg-delete" disabled={!confirmReady}>
      <Trash2 className="stg-delete__icon" strokeWidth={1.8} aria-hidden="true" />
                {text({ en: "Delete workspace", fr: "Supprimer l'espace" })}
      </button>
      </div>
      </div>
      </div>
      )}
      </WorkspaceShell>
  );
}
