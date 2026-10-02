import { useMemo, useState } from "react";
import { ArrowDownToLine, ArrowUpFromLine, Database, IdCard, Landmark, Smartphone } from "lucide-react";
import { useAuthLocale } from "@/components/auth/AuthLocale";
import { TesterAccountLayout } from "@/components/tester/TesterAccountHeader";
import { TesterShell } from "@/components/tester/TesterShell";
import { authWords as words } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { mockEarnings, mockPayouts, mockTesterVerified } from "./testerMocks";
import { readTesterProfile } from "./testerProfileStore";
import { routes } from "@/lib/routes";

/** Smallest balance a tester must hold before a payout can be requested. */
const PAYOUT_MINIMUM = 30_000;

const copy = {
  balance: words("Wallet balance", "Solde du portefeuille"),
  inProgress: words("Payouts in progress", "Paiements en cours"),
  completed: words("Payouts completed", "Paiements terminés"),
  payoutMethod: words("Payout method", "Mode de retrait"),
  minimumNote: words("You can request a payout once your wallet balance reaches a minimum of", "Vous pouvez demander un retrait dès que votre solde atteint un minimum de"),
  stillNeeded: words("to go", "à gagner"),
  bankTransfer: words("Bank transfer", "Virement bancaire"),
  bankTransferBody: words("Sent to the account on your profile", "Envoyé au compte de votre profil"),
  mobileWallet: words("Mobile wallet", "Portefeuille mobile"),
  mobileWalletBody: words("Sent to your mobile money number", "Envoyé à votre numéro de money mobile"),
  requestPayout: words("Request payout", "Demander un retrait"),
  history: words("Payout history", "Historique des retraits"),
  historyBody: words("Every payout you have requested, newest first.", "Tous vos retraits, du plus récent au plus ancien."),
  requested: words("Requested", "Demandé"),
  methodLabel: words("Method", "Mode"),
  destination: words("Destination", "Destination"),
  amount: words("Amount", "Montant"),
  noPayouts: words("No payouts yet. Once you request one it will appear here.", "Aucun retrait. Vos retraits apparaîtront ici."),
  verifiedNeeded: words("Verify your identity to enable payouts.", "Vérifiez votre identité pour activer les retraits."),
  locked: words("Identity verification required", "Vérification d’identité requise"),
  notEnough: words("Minimum balance not reached", "Solde minimum non atteint"),
  ready: words("You can request a payout now.", "Vous pouvez demander un retrait maintenant."),
};

type Method = "bank_transfer" | "mobile_wallet";

const methodLabel: Record<"gift_card" | "bank_transfer" | "mobile_wallet", ReturnType<typeof words>> = {
  gift_card: words("Digital gift card", "Carte cadeau numérique"),
  bank_transfer: words("Bank transfer", "Virement bancaire"),
  mobile_wallet: words("Mobile wallet", "Portefeuille mobile"),
};

const payoutStatus: Record<string, { label: ReturnType<typeof words>; className: string }> = {
  delivered: { label: words("Delivered", "Livré"), className: "bg-[#E3EBFA] text-[#1E3A8A]" },
  paid: { label: words("Paid", "Payé"), className: "bg-[#E3EBFA] text-[#1E3A8A]" },
  processing: { label: words("Processing", "En cours"), className: "bg-[#FFF7E6] text-[#8A5A00]" },
};

const tnd = (millimes: number) => `${(millimes / 1000).toFixed(2)} TND`;

export default function TesterEarnings() {
  const { text } = useAuthLocale();
  const firstName = useMemo(() => readTesterProfile().firstName.trim() || undefined, []);
  const [method, setMethod] = useState<Method>("bank_transfer");

  const balance = mockEarnings.total_millimes - mockEarnings.paid_millimes;
  const progress = Math.min(100, Math.round((balance / PAYOUT_MINIMUM) * 100));
  const missing = Math.max(0, PAYOUT_MINIMUM - balance);
  const canRequest = !mockTesterVerified ? "verified" : balance >= PAYOUT_MINIMUM ? "ready" : "short";

  const methods: { key: Method; title: ReturnType<typeof words>; body: ReturnType<typeof words>; icon: typeof Database }[] = [
    { key: "bank_transfer", title: copy.bankTransfer, body: copy.bankTransferBody, icon: Landmark },
    { key: "mobile_wallet", title: copy.mobileWallet, body: copy.mobileWalletBody, icon: Smartphone },
  ];

  const stats = [
    { label: copy.balance, value: balance, icon: Database, tone: "text-[#1E3A8A]" },
    { label: copy.inProgress, value: mockEarnings.pending_millimes, icon: ArrowUpFromLine, tone: "text-[#8A5A00]" },
    { label: copy.completed, value: mockEarnings.paid_millimes, icon: ArrowDownToLine, tone: "text-[#1E3A8A]" },
  ];

  return (
    <TesterShell>
      <TesterAccountLayout active="wallet" firstName={firstName}>

      {!mockTesterVerified && (
        <p className="mt-5 flex flex-wrap items-center gap-2 rounded-[10px] border border-[#DCE4F2] bg-[#E8EFFB] px-3.5 py-2.5 text-[13px] text-[#0F1E3D]">
          <IdCard className="size-4 shrink-0 text-[#1E3A8A]" strokeWidth={1.8} aria-hidden="true" />
          <span>{text(copy.verifiedNeeded)} <a href={routes.testerOnboarding} className="rounded font-semibold text-[#1E3A8A] underline underline-offset-2">{text(copy.locked)}</a></span>
        </p>
      )}

      <div className="mt-7 grid gap-4 sm:grid-cols-3">
        {stats.map(({ label, value, icon: Icon, tone }) => (
          <article key={label.en} className="rounded-2xl border border-[#DCE4F2] bg-[#F7F9FD] p-5 sm:p-6">
            <p className="text-[13px] font-semibold text-[#5A6B87]">{text(label)}</p>
            <p className="mt-3 flex items-center gap-2.5 text-[24px] font-bold leading-none tracking-[-0.02em] text-[#0F1E3D]">
              <Icon className={cn("size-5 shrink-0", tone)} strokeWidth={1.8} aria-hidden="true" />
              {tnd(value)}
            </p>
          </article>
        ))}
      </div>

      <div className="mt-10">
        <h2 className="flex items-center gap-2.5 text-[15px] font-bold text-[#0F1E3D]">
          <span aria-hidden="true" className="h-4 w-1 rounded-full bg-[#1E3A8A]" />
          {text(copy.payoutMethod)}
        </h2>
        <p className="mt-2 max-w-[68ch] text-[14px] leading-relaxed text-[#5A6B87]">
          {text(copy.minimumNote)} <strong className="font-semibold text-[#0F1E3D]">{tnd(PAYOUT_MINIMUM)}</strong>.
        </p>

        <div
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={PAYOUT_MINIMUM / 1000}
          aria-valuenow={balance / 1000}
          aria-label={text(copy.balance)}
          className="mt-4 h-2 w-full overflow-hidden rounded-full bg-[#E3EBFA]"
        >
          <div className="h-full rounded-full bg-[#1E3A8A] transition-[width] duration-500" style={{ width: `${progress}%` }} />
        </div>
        <p className="mt-2 text-[13px] text-[#5A6B87]">
          {canRequest === "ready"
            ? text(copy.ready)
            : canRequest === "verified"
              ? text(copy.verifiedNeeded)
              : <>{tnd(missing)} {text(copy.stillNeeded)}</>}
        </p>

        <fieldset className="mt-6">
          <legend className="sr-only">{text(copy.payoutMethod)}</legend>
          <div className="grid gap-3 sm:grid-cols-2">
            {methods.map(({ key, title, body, icon: Icon }) => {
              const selected = method === key;
              return (
                <label
                  key={key}
                  className={cn(
                    "flex cursor-pointer items-start gap-3 rounded-2xl border bg-white p-4 transition focus-within:ring-2 focus-within:ring-[#1E3A8A] focus-within:ring-offset-2",
                    selected ? "border-[#1E3A8A]" : "border-[#DCE4F2] hover:border-[#9FB2D0]",
                  )}
                >
                  <input
                    type="radio"
                    name="payout-method"
                    value={key}
                    checked={selected}
                    onChange={() => setMethod(key)}
                    className="sr-only"
                  />
                  <span
                    aria-hidden="true"
                    className={cn(
                      "mt-0.5 grid size-[18px] shrink-0 place-items-center rounded-full border-2 transition",
                      selected ? "border-[#1E3A8A]" : "border-[#C4C9D1]",
                    )}
                  >
                    <span className={cn("size-2 rounded-full", selected ? "bg-[#1E3A8A]" : "bg-transparent")} />
                  </span>
                  <span className="min-w-0">
                    <span className="flex items-center gap-2 text-[14.5px] font-bold text-[#0F1E3D]">
                      <Icon className="size-4 shrink-0 text-[#1E3A8A]" strokeWidth={1.8} aria-hidden="true" />
                      {text(title)}
                    </span>
                    <span className="mt-1 block text-[13px] leading-relaxed text-[#5A6B87]">{text(body)}</span>
                  </span>
                </label>
              );
            })}
          </div>
        </fieldset>

        <div className="mt-5 flex flex-wrap items-center gap-4">
          <button
            type="button"
            disabled={canRequest !== "ready"}
            className="inline-flex min-h-11 items-center rounded-full bg-[#0F1E3D] px-6 text-[14px] font-semibold text-white transition hover:bg-[#1E3A8A] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1E3A8A] focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:bg-[#C9D3E4] disabled:text-[#3F5170] disabled:hover:bg-[#C9D3E4]"
          >
            {text(copy.requestPayout)}
          </button>
        </div>
      </div>

      <div className="mt-12">
        <h2 className="flex items-center gap-2.5 text-[15px] font-bold text-[#0F1E3D]">
          <span aria-hidden="true" className="h-4 w-1 rounded-full bg-[#1E3A8A]" />
          {text(copy.history)}
        </h2>
        <p className="mt-2 text-[14px] text-[#5A6B87]">{text(copy.historyBody)}</p>

        {mockPayouts.length === 0 ? (
          <p className="mt-5 rounded-2xl border border-dashed border-[#CDD9EC] bg-[#F7F9FD] p-6 text-[14px] text-[#5A6B87]">{text(copy.noPayouts)}</p>
        ) : (
          <ul className="mt-5 space-y-3">
            {mockPayouts.map((payout) => (
              <li key={payout.id} className="rounded-2xl border border-[#DCE4F2] bg-white p-5 sm:p-6">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-[16px] font-bold text-[#0F1E3D]">{tnd(payout.amount_millimes)}</p>
                    <p className="mt-1 text-[13.5px] text-[#5A6B87]">{payout.destination}</p>
                  </div>
                  <span className={cn("inline-flex shrink-0 items-center rounded-full px-2.5 py-1 text-[12.5px] font-semibold", payoutStatus[payout.status].className)}>
                    {text(payoutStatus[payout.status].label)}
                  </span>
                </div>
                <dl className="mt-4 grid gap-3 border-t border-[#EEF2F9] pt-4 text-[13.5px] sm:grid-cols-2">
                  <div>
                    <dt className="text-[#5A6B87]">{text(copy.requested)}</dt>
                    <dd className="mt-0.5 font-semibold text-[#0F1E3D]">{payout.requested_at}</dd>
                  </div>
                  <div>
                    <dt className="text-[#5A6B87]">{text(copy.methodLabel)}</dt>
                    <dd className="mt-0.5 font-semibold text-[#0F1E3D]">{text(methodLabel[payout.method])}</dd>
                  </div>
                </dl>
              </li>
            ))}
          </ul>
        )}
      </div>
      </TesterAccountLayout>
    </TesterShell>
  );
}
