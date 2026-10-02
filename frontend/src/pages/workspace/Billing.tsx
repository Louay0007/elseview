import { useEffect, useState } from "react";
import { Users } from "lucide-react";
import { apiFetch, backendAvailable, newIdempotencyKey } from "@/lib/api";
import { useWorkspace } from "@/components/workspace/WorkspaceContext";
import { useAuthLocale } from "@/components/auth/AuthLocale";
import { WorkspaceShell, useWorkspaceNav } from "@/components/workspace/WorkspaceShell";
import "@/components/workspace/Billing.css";

export default function Billing() {
  const { text } = useAuthLocale();
  const { firstName, role, displayName, workspaceName, goWithParams } = useWorkspaceNav();
  const billingEmail = `${displayName.toLowerCase().replace(/\s+/g, ".")}.rjili@issatm.ucar.tn`;
  const { workspaceId } = useWorkspace();
  const [plans, setPlans] = useState<{ id: string; name: string }[]>([]);
  const [invoices, setInvoices] = useState<{ id: string; total: string; status: string }[]>([]);
  const [billingError, setBillingError] = useState<string | null>(null);
  const [teamOpen, setTeamOpen] = useState(false);

  useEffect(() => {
    if (!backendAvailable() || !workspaceId) return;
    apiFetch<{ items: { id: string; name: string }[] }>(`/workspaces/${workspaceId}/billing/plans`)
      .then((result) => setPlans(result.items ?? []))
      .catch(() => {});
    apiFetch<{ items: { id: string; total: string; status: string }[] }>(`/workspaces/${workspaceId}/billing/invoices`)
      .then((result) => setInvoices(result.items ?? []))
      .catch(() => {});
  }, [workspaceId]);

  const subscribeTeam = () => {
    if (!backendAvailable() || !workspaceId) return;
    setBillingError(null);
    const plan = plans[0];
    if (!plan) {
      setBillingError(text({ en: "No plans yet. Try again later.", fr: "Aucun plan pour l’instant. Réessayez." }));
      return;
    }
    void apiFetch(`/workspaces/${workspaceId}/billing/subscriptions`, {
      method: "POST",
      idempotencyKey: newIdempotencyKey(),
      body: { plan_id: plan.id },
    })
      .then(() => setTeamOpen(false))
      .catch(() => setBillingError(text({ en: "Could not switch plans. Try again.", fr: "Changement impossible. Réessayez." })));
  };

  return (
      <WorkspaceShell >
      <div className="bill-body">
      <h1 className="bill-title">{text({ en: "Workspace billing", fr: "Facturation de l’espace" })}</h1>
      <hr className="bill-rule" />

      <div className="bill-grid">
      <section aria-labelledby="billing-workspace-heading">
      <h2 id="billing-workspace-heading" className="bill-section">
              {text({ en: "Workspace information", fr: "Informations sur l’espace" })}
      </h2>
      <div className="bill-card">
      <div className="bill-facts">
      <div>
      <p className="bill-label">{text({ en: "Workspace name", fr: "Nom de l’espace" })}</p>
      <p className="bill-value">{workspaceName}</p>
      </div>
      <div>
      <p className="bill-label">{text({ en: "Workspace plan", fr: "Plan de l’espace" })}</p>
      <p className="bill-value">{text({ en: "Pay-As-You-Go", fr: "Paiement à l’utilisation" })}</p>
      </div>
      <div>
      <p className="bill-label">{text({ en: "Plan renewal amount", fr: "Montant du renouvellement" })}</p>
      <p className="bill-value">{text({ en: "Free forever / $0.00", fr: "Gratuit pour toujours / 0,00 $" })}</p>
      </div>
      <div>
      <p className="bill-label">{text({ en: "Next payment date", fr: "Prochaine date de paiement" })}</p>
      <p className="bill-value">{text({ en: "NA", fr: "S. O." })}</p>
      </div>
      </div>

      <div className="bill-team">
      <p className="bill-team__text">
                  {text({
                    en: "Add team members with the Team plan.",
                    fr: "Ajoutez des membres avec le plan Équipe.",
                  })}
      </p>
      <button type="button" className="bill-team__button" onClick={() => setTeamOpen(true)}>
      <Users className="bill-team__icon" strokeWidth={1.8} aria-hidden="true" />
                  {text({ en: "Switch to Team plan", fr: "Passer au plan Équipe" })}
      </button>
      </div>
      </div>
      </section>

      <section aria-labelledby="billing-info-heading">
      <h2 id="billing-info-heading" className="bill-section">
              {text({ en: "Billing information", fr: "Informations de facturation" })}
      </h2>
      <div className="bill-card">
      <div className="bill-card-head">
      <h3 className="bill-card-title">{text({ en: "Billing info", fr: "Infos de facturation" })}</h3>
      <button type="button" className="bill-edit">
                  {text({ en: "Edit", fr: "Modifier" })}
      </button>
      </div>
      <div className="bill-info">
      <div>
      <p className="bill-label">{text({ en: "Name/company name", fr: "Nom / société" })}</p>
      <p className="bill-value">-</p>
      </div>
      <div>
      <p className="bill-label">{text({ en: "Address", fr: "Adresse" })}</p>
      <p className="bill-value">-</p>
      </div>
      <div>
      <p className="bill-label">{text({ en: "Email", fr: "E-mail" })}</p>
      <p className="bill-value">{billingEmail}</p>
      </div>
      <div>
      <p className="bill-label">{text({ en: "City", fr: "Ville" })}</p>
      <p className="bill-value">-</p>
      </div>
      <div>
      <p className="bill-label">{text({ en: "Country", fr: "Pays" })}</p>
      <p className="bill-value">-</p>
      </div>
      </div>
      </div>
      </section>
      </div>

      <section aria-labelledby="billing-history-heading" className="bill-history">
      <h2 id="billing-history-heading" className="bill-history__title">
            {text({ en: "Billing and Invoice history", fr: "Historique de facturation" })}
      </h2>
          {billingError && <p role="alert" className="bill-error">{billingError}</p>}
          {invoices.length > 0 ? (
      <ul className="bill-invoices">
              {invoices.map((invoice) => (
      <li key={invoice.id}>{invoice.total} · {invoice.status} — {text({ en: "Paid by hand — record only.", fr: "Payé à la main — enregistrement seul." })}</li>
              ))}
      </ul>
          ) : (
      <p className="bill-history__empty">
            {text({ en: "No bills available at this moment.", fr: "Aucune facture pour le moment." })}
      </p>
          )}
      </section>
      {teamOpen && (
      <div className="bill-modal" role="dialog" aria-modal="true" aria-label={text({ en: "Switch to Team plan", fr: "Passer au plan Équipe" })}>
      <div className="bill-modal__card">
      <h2>{text({ en: "Switch to Team plan?", fr: "Passer au plan Équipe ?" })}</h2>
      <p>{text({ en: "Team plan lets you add members. Billing stays manual.", fr: "Le plan Équipe permet d’ajouter des membres. Facturation manuelle." })}</p>
      <div className="bill-modal__actions">
      <button type="button" className="bill-team__button" onClick={() => setTeamOpen(false)}>{text({ en: "Keep current plan", fr: "Garder le plan actuel" })}</button>
      <button type="button" className="bill-team__button" onClick={subscribeTeam}>{text({ en: "Switch plan", fr: "Changer de plan" })}</button>
      </div>
      </div>
      </div>
      )}
      </div>
      </WorkspaceShell>
  );
}
