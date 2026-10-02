import { authWords as words } from "@/lib/auth";
import type { AboutOption } from "./testerAbout";

const preferNot = (): AboutOption => ({ value: "prefer-not", label: words("Prefer not to say", "Je préfère ne pas répondre") });

/**
 * Bank *categories* rather than named institutions: the panel spans several
 * MENA markets plus France, so a hardcoded institution list would be both
 * incomplete and skewed toward whichever country it was written for.
 */
export const bankOptions: AboutOption[] = [
  { value: "local", label: words("A local or regional bank", "Banque locale ou régionale") },
  { value: "national", label: words("A large national bank", "Grande banque nationale") },
  { value: "islamic", label: words("An Islamic bank", "Banque islamique") },
  { value: "digital", label: words("A digital bank or neobank", "Banque numérique ou néobanque") },
  { value: "cooperative", label: words("A credit union or cooperative", "Coopérative ou caisse d’épargne") },
  { value: "microfinance", label: words("A microfinance institution", "Institution de microfinance") },
  { value: "postal", label: words("A post office savings account", "Compte d’épargne postal") },
  { value: "online-provider", label: words("An online-only payment provider", "Prestataire de paiement en ligne") },
  { value: "mobile-money", label: words("A mobile money account", "Compte de monnaie électronique") },
  { value: "other", label: words("Another bank", "Une autre banque") },
  preferNot(),
];

/** Multi-select: people routinely pay with several methods at once. */
export const paymentMethodOptions: AboutOption[] = [
  { value: "cash", label: words("Cash", "Espèces") },
  { value: "debit", label: words("Debit card", "Carte de débit") },
  { value: "credit", label: words("Credit card", "Carte de crédit") },
  { value: "mobile", label: words("Mobile payment (Apple Pay, Google Pay…)", "Paiement mobile (Apple Pay, Google Pay…)") },
  { value: "wallet", label: words("Digital wallet", "Portefeuille électronique") },
  { value: "transfer", label: words("Bank transfer", "Virement bancaire") },
  { value: "direct-debit", label: words("Direct debit", "Prélèvement automatique") },
  { value: "cheque", label: words("Cheque", "Chèque") },
  { value: "remittance", label: words("Money transfer service", "Service de transfert d’argent") },
  { value: "prepaid", label: words("Prepaid or stored-value card", "Carte prépayée ou carte rechargeable") },
  { value: "crypto", label: words("Cryptocurrency", "Cryptomonnaie") },
  { value: "other", label: words("Another method", "Un autre moyen de paiement") },
];

export type TesterFinanceDraft = {
  noBankAccount: boolean;
  bank: string;
  paymentMethods: string[];
};

function isKnown(options: AboutOption[], value: string) {
  return options.some((entry) => entry.value === value);
}

export function testerFinanceValid(finance: TesterFinanceDraft): boolean {
  if (!finance.noBankAccount && !isKnown(bankOptions, finance.bank)) return false;
  // Payment methods still apply without a bank account (cash, mobile money, …).
  return finance.paymentMethods.some((code) => isKnown(paymentMethodOptions, code));
}
