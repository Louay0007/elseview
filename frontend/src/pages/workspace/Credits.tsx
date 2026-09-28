import { useEffect, useState } from "react";
import { useAuthLocale } from "@/components/auth/AuthLocale";
import { apiFetch, backendAvailable } from "@/lib/api";
import { useWorkspace } from "@/components/workspace/WorkspaceContext";
import { WorkspaceShell, useWorkspaceNav } from "@/components/workspace/WorkspaceShell";
import "@/components/workspace/Credits.css";

export default function Credits() {
  const { text } = useAuthLocale();
  const { firstName, role, displayName, workspaceName, goWithParams } = useWorkspaceNav();
  const { workspaceId } = useWorkspace();
  const [balance, setBalance] = useState<number | null>(null);
  const [transactions, setTransactions] = useState<{ id: string; amount: number; status: string }[]>([]);

  useEffect(() => {
    if (!backendAvailable() || !workspaceId) return;
    apiFetch<{ items: { id: string; amount: number; status: string }[] }>(`/workspaces/${workspaceId}/billing/credits`)
      .then((result) => {
        const items = result.items ?? [];
        setTransactions(items);
        setBalance(items.reduce((total, item) => total + (item.amount || 0), 0));
      })
      .catch(() => {});
  }, [workspaceId]);

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
      <div className="credits-body">
        <h1 className="credits-title">{text({ en: "Credits", fr: "Crédits" })}</h1>
        <hr className="credits-rule" />

        <section aria-labelledby="credits-wallet-heading" className="credits-card">
          <h2 id="credits-wallet-heading" className="credits-card__label">
            {text({ en: "Your balance", fr: "Votre solde" })}
          </h2>
          <div className="credits-card__balance">
            <p className="credits-card__amount">
              <span className="credits-card__number">{balance ?? 0}</span>
              <span className="credits-card__unit">{text({ en: "Credits", fr: "crédits" })}</span>
            </p>
            <button type="button" className="credits-card__buy" onClick={() => goWithParams("/workspace/credits/buy")}>
              {text({ en: "Buy credits", fr: "Acheter des crédits" })}
            </button>
          </div>
        </section>

        <section aria-labelledby="credits-history-heading" className="credits-history">
          <h2 id="credits-history-heading" className="credits-history__title">
            {text({ en: "Transaction history", fr: "Historique des transactions" })}
          </h2>
          {transactions.length > 0 ? (
            <ul className="credits-history__list">
              {transactions.map((item) => (
                <li key={item.id}>{item.amount} {text({ en: "credits", fr: "crédits" })} · {item.status}</li>
              ))}
            </ul>
          ) : (
            <p className="credits-history__empty">
              {text({ en: "No transactions yet.", fr: "Aucune transaction pour l’instant." })}
            </p>
          )}
        </section>
      </div>
    </WorkspaceShell>
  );
}
