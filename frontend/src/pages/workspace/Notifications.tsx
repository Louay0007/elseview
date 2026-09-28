import { useEffect, useState } from "react";
import { apiFetch, backendAvailable } from "@/lib/api";
import { useWorkspace } from "@/components/workspace/WorkspaceContext";
import { Link } from "react-router-dom";
import { useAuthLocale } from "@/components/auth/AuthLocale";
import { WorkspaceShell, useWorkspaceNav } from "@/components/workspace/WorkspaceShell";
import "@/components/workspace/Notifications.css";

export default function Notifications() {
  const { text } = useAuthLocale();
  const { firstName, role, displayName, workspaceName, goWithParams } = useWorkspaceNav();
  const [marketing, setMarketing] = useState(true);
  const [accountRelated, setAccountRelated] = useState(true);
  const [notifError, setNotifError] = useState<string | null>(null);
  const { workspaceId } = useWorkspace();

  useEffect(() => {
    if (!backendAvailable() || !workspaceId) return;
    apiFetch<{ marketing: boolean; account: boolean }>(`/workspaces/${workspaceId}/collaboration/notification-preferences`)
      .then((result) => {
        setMarketing(result.marketing ?? true);
        setAccountRelated(result.account ?? true);
      })
      .catch(() => {});
  }, [workspaceId]);

  const save = (nextMarketing: boolean, nextAccount: boolean) => {
    setMarketing(nextMarketing);
    setAccountRelated(nextAccount);
    setNotifError(null);
    if (!backendAvailable() || !workspaceId) return;
    void apiFetch(`/workspaces/${workspaceId}/collaboration/notification-preferences`, {
      method: "PUT",
      body: { marketing: nextMarketing, account: nextAccount },
    }).catch(() => {
      setMarketing(marketing);
      setAccountRelated(accountRelated);
      setNotifError(text({ en: "Save failed. Try again.", fr: "Enregistrement impossible. Réessayez." }));
    });
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
      <div className="notif-body">
        <h1 className="notif-title">{text({ en: "Notification settings", fr: "Paramètres de notification" })}</h1>
        <hr className="notif-rule" />

        <section aria-labelledby="notif-email-heading">
          <h2 id="notif-email-heading" className="notif-section">
            {text({ en: "Email notifications", fr: "Notifications par e-mail" })}
          </h2>
          <p className="notif-lead">
            {text({
              en: "Choose which emails we send.",
              fr: "Choisissez les e-mails envoyés à votre adresse.",
            })}
          </p>
        </section>

        {notifError && <p role="alert" className="notif-error">{notifError}</p>}

        <hr className="notif-divider" />

        <section className="notif-row" aria-labelledby="notif-marketing-heading">
          <div>
            <h3 id="notif-marketing-heading" className="notif-row__title">
              {text({ en: "Marketing notifications", fr: "Notifications marketing" })}
            </h3>
            <p className="notif-row__copy">
              {text({
                en: "News about updates, features, and offers.",
                fr: "Nouveautés, fonctionnalités et offres.",
              })}
            </p>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={marketing}
            aria-label={text({ en: "Marketing notifications", fr: "Notifications marketing" })}
            className={marketing ? "notif-switch notif-switch--on" : "notif-switch"}
            onClick={() => save(!marketing, accountRelated)}
          >
            <span className="notif-switch__thumb" aria-hidden="true" />
          </button>
        </section>

        <section className="notif-row" aria-labelledby="notif-account-heading">
          <div>
            <h3 id="notif-account-heading" className="notif-row__title">
              {text({ en: "Account related notifications", fr: "Notifications liées au compte" })}
            </h3>
            <p className="notif-row__copy">
              {text({
                en: "Tips based on your account activity.",
                fr: "Conseils selon votre activité.",
              })}
            </p>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={accountRelated}
            aria-label={text({ en: "Account related notifications", fr: "Notifications liées au compte" })}
            className={accountRelated ? "notif-switch notif-switch--on" : "notif-switch"}
            onClick={() => save(marketing, !accountRelated)}
          >
            <span className="notif-switch__thumb" aria-hidden="true" />
          </button>
        </section>

        <section className="notif-row notif-row--static" aria-labelledby="notif-system-heading">
          <div>
            <h3 id="notif-system-heading" className="notif-row__title">
              {text({ en: "System notifications", fr: "Notifications système" })}
            </h3>
            <p className="notif-row__copy">
              {text({
                en: "You get these because you agreed to our ",
                fr: "Vous recevez ces notifications car vous avez accepté notre ",
              })}
              <Link to="/privacy" className="notif-link">
                {text({ en: "privacy policy", fr: "politique de confidentialité" })}
              </Link>
              {text({ en: " and ", fr: " et nos " })}
              <Link to="/terms" className="notif-link">
                {text({ en: "terms of use", fr: "conditions d’utilisation" })}
              </Link>
              .
              <br />
              {text({
                en: "To stop, delete your account.",
                fr: "Pour les arrêter, supprimez votre compte.",
              })}
            </p>
          </div>
        </section>
      </div>
    </WorkspaceShell>
  );
}
