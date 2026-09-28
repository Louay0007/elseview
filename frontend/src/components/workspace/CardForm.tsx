import { useMemo, useState } from "react";
import { Check, CreditCard, Info, Lock } from "lucide-react";
import { useAuthLocale } from "@/components/auth/AuthLocale";
import { Checkbox } from "@/components/ui/checkbox";
import { detectBrand, expiryValid, luhnValid, type CardBrand } from "@/lib/card";
import { MastercardLogo, VisaLogo } from "./BrandLogos";

export type CardFormValue = {
  number: string;
  expiry: string;
  cvc: string;
  name: string;
  saveCard: boolean;
  brand: CardBrand;
  valid: boolean;
};

function BrandMark({ brand, className = "h-7 w-auto", tone = "light", dim = false }: { brand: CardBrand; className?: string; tone?: "light" | "dark"; dim?: boolean }) {
  const visaTone = tone === "light" ? "text-white" : "text-[#1A1F71]";
  if (brand === "visa") {
    return <VisaLogo className={`${className} ${visaTone}`} />;
  }
  if (brand === "mastercard") {
    return <MastercardLogo className={className} />;
  }
  return (
    <span className={`flex items-center gap-1.5 ${dim ? "opacity-50" : ""} ${className}`} aria-hidden="true">
      <VisaLogo className={`h-5 w-auto ${visaTone}`} />
      <MastercardLogo className="h-5 w-auto" />
    </span>
  );
}

function groupNumber(digits: string) {
  return digits.replace(/(\d{4})(?=\d)/g, "$1  ").trim();
}

type CardFormProps = {
  onChange: (value: CardFormValue) => void;
  forceTouched?: boolean;
};

export function CardForm({ onChange, forceTouched = false }: CardFormProps) {
  const { text } = useAuthLocale();
  const [number, setNumber] = useState("");
  const [expiry, setExpiry] = useState("");
  const [cvc, setCvc] = useState("");
  const [name, setName] = useState("");
  const [saveCard, setSaveCard] = useState(false);
  const [touched, setTouched] = useState(false);
  const showErrors = touched || forceTouched;

  const digits = number.replace(/\D/g, "");
  const brand = detectBrand(digits);
  const numberOk = luhnValid(digits);
  const expiryOk = expiryValid(expiry);
  const cvcOk = /^\d{3,4}$/.test(cvc);
  const nameOk = name.trim().length >= 2;
  const valid = numberOk && expiryOk && cvcOk && nameOk;

  const emit = (patch: Partial<CardFormValue>) => {
    const mergedDigits = (patch.number ?? digits).replace(/\D/g, "");
    const mergedExpiry = patch.expiry ?? expiry;
    const mergedCvc = patch.cvc ?? cvc;
    const mergedName = patch.name ?? name;
    const mergedBrand = detectBrand(mergedDigits);
    onChange({
      number: mergedDigits,
      expiry: mergedExpiry,
      cvc: mergedCvc,
      name: mergedName,
      saveCard: patch.saveCard ?? saveCard,
      brand: mergedBrand,
      valid: luhnValid(mergedDigits) && expiryValid(mergedExpiry) && /^\d{3,4}$/.test(mergedCvc) && mergedName.trim().length >= 2,
    });
  };

  const numberError = showErrors && !numberOk
    ? digits.length === 0
      ? text({ en: "Enter your 16-digit card number.", fr: "Saisissez les 16 chiffres." })
      : text({ en: "Card number is invalid — check the digits and try again.", fr: "Numéro invalide — vérifiez puis réessayez." })
    : null;
  const expiryError = showErrors && expiry.length > 0 && !expiryOk
    ? text({ en: "Use a future date as MM/YY.", fr: "Date future au format MM/AA." })
    : null;

  const field = (hasError: boolean) =>
    `min-h-[56px] w-full rounded-xl border bg-white px-4 text-[15px] text-black outline-none transition-colors placeholder:text-[#8e8e93] focus:ring-2 ${
      hasError
        ? "border-[#dc2626] focus:border-[#dc2626] focus:ring-[#dc2626]/15"
        : "border-[#d9d9df] focus:border-[#1d4ed8] focus:ring-[#1d4ed8]/15"
    }`;

  const formattedExpiry = useMemo(() => expiry, [expiry]);

  return (
    <div>
      <div aria-hidden="true" className="relative overflow-hidden rounded-2xl bg-[#0b1e4b] p-5 text-white shadow-[0_24px_45px_-24px_rgba(11,30,75,.65)]">
        <div aria-hidden="true" className="pointer-events-none absolute -right-16 -top-24 size-64 rounded-full bg-[#1d4ed8]/50 blur-2xl" />
        <div aria-hidden="true" className="pointer-events-none absolute -bottom-28 -left-10 size-56 rounded-full bg-[#0ea5e9]/30 blur-2xl" />
        <div className="relative flex items-start justify-between">
          <svg viewBox="0 0 44 32" className="h-8 w-11" aria-hidden="true">
            <rect x="1" y="1" width="42" height="30" rx="6" fill="none" stroke="#e8c98f" strokeWidth="2" />
            <path d="M1 11h14M1 21h14M29 11h14M29 21h14M15 1v30M29 1v30" stroke="#e8c98f" strokeWidth="2" />
          </svg>
          <span key={brand} className="card-brand-in inline-flex">
            <BrandMark brand={brand} />
          </span>
        </div>
        <p className="relative mt-5 font-mono text-[19px] font-medium tracking-[0.08em] tabular-nums" aria-live="polite">
          {digits ? groupNumber(digits).padEnd(19, "•") : "•••• •••• •••• ••••"}
        </p>
        <div className="relative mt-4 flex items-end justify-between gap-4 text-[12px]">
          <div className="min-w-0">
            <p className="uppercase tracking-[0.14em] text-white/55">{text({ en: "Card holder", fr: "Titulaire" })}</p>
            <p className="mt-1 truncate text-[14px] font-semibold uppercase tracking-wide">{name.trim() || "YOUR NAME"}</p>
          </div>
          <div className="shrink-0 text-right">
            <p className="uppercase tracking-[0.14em] text-white/55">{text({ en: "Expires", fr: "Expire" })}</p>
            <p className="mt-1 text-[14px] font-semibold tabular-nums">{formattedExpiry || "MM/YY"}</p>
          </div>
        </div>
      </div>

      <div className="mt-5 grid gap-3">
        <div>
          <label htmlFor="card-number" className="mb-1.5 block text-[13px] font-semibold text-[#18181b]">
            {text({ en: "Card number", fr: "Numéro de carte" })}
          </label>
          <div className={`flex items-center gap-2 rounded-xl border bg-white pr-3 transition-colors focus-within:ring-2 ${
            numberError ? "border-[#dc2626] focus-within:border-[#dc2626] focus-within:ring-[#dc2626]/15" : "border-[#d9d9df] focus-within:border-[#1d4ed8] focus-within:ring-[#1d4ed8]/15"
          }`}>
            <input id="card-number" value={groupNumber(digits)} inputMode="numeric" autoComplete="cc-number" placeholder="1234 5678 9012 3456"
              onChange={(e) => { const d = e.target.value.replace(/\D/g, "").slice(0, 16); setNumber(d); setTouched(true); emit({ number: d, brand: detectBrand(d) }); }}
              onBlur={() => setTouched(true)}
              aria-invalid={Boolean(numberError)} aria-describedby={numberError ? "card-number-error" : undefined}
              className="min-h-[54px] w-full bg-transparent pl-4 font-mono text-[15px] tracking-wide text-black outline-none placeholder:text-[#8e8e93] tabular-nums" />
            {numberOk
              ? <span className="grid size-7 shrink-0 place-items-center rounded-full bg-[#eef6ee] text-[#1d5c1d]" aria-label={text({ en: "Valid card number", fr: "Numéro valide" })}><Check className="size-4" strokeWidth={2.4} aria-hidden="true" /></span>
              : brand !== "unknown"
                ? <BrandMark brand={brand} tone="dark" className="h-6 w-auto shrink-0" />
                : <CreditCard className="size-5 shrink-0 text-[#8e8e93]" strokeWidth={1.6} aria-hidden="true" />}
          </div>
          {numberError && <p id="card-number-error" role="alert" className="mt-1.5 text-[13px] font-medium text-[#9c2d20]">{numberError}</p>}
        </div>

        <div>
          <label htmlFor="card-name" className="mb-1.5 block text-[13px] font-semibold text-[#18181b]">
            {text({ en: "Name on card", fr: "Nom sur la carte" })}
          </label>
          <input id="card-name" value={name} autoComplete="cc-name" placeholder={text({ en: "e.g. Louay Rjili", fr: "ex. Louay Rjili" })}
            onChange={(e) => { setName(e.target.value); setTouched(true); emit({ name: e.target.value }); }}
            onBlur={() => setTouched(true)}
            className={field(showErrors && !nameOk)} />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label htmlFor="card-expiry" className="mb-1.5 block text-[13px] font-semibold text-[#18181b]">
              {text({ en: "Expiry", fr: "Expiration" })}
            </label>
            <input id="card-expiry" value={expiry} inputMode="numeric" autoComplete="cc-exp" placeholder="MM/YY"
              onChange={(e) => {
                const d = e.target.value.replace(/\D/g, "").slice(0, 4);
                const next = d.length >= 3 ? `${d.slice(0, 2)}/${d.slice(2)}` : d;
                setExpiry(next); setTouched(true); emit({ expiry: next });
              }}
              onBlur={() => setTouched(true)}
              className={field(Boolean(expiryError))} />
            {expiryError && <p role="alert" className="mt-1.5 text-[13px] font-medium text-[#9c2d20]">{expiryError}</p>}
          </div>
          <div>
            <label htmlFor="card-cvc" className="mb-1.5 flex items-center gap-1 text-[13px] font-semibold text-[#18181b]">
              {text({ en: "CVC", fr: "CVC" })}
              <span className="group relative grid size-4 place-items-center text-[#8e8e93]">
                <Info className="size-3.5" strokeWidth={1.8} aria-hidden="true" />
                <span role="tooltip" className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-2 hidden w-44 -translate-x-1/2 rounded-lg bg-black px-3 py-2 text-[12px] font-normal leading-relaxed text-white group-hover:block">
                  {text({ en: "The 3 digits on the back of your card.", fr: "Les 3 chiffres au dos de la carte." })}
                </span>
              </span>
            </label>
            <input id="card-cvc" value={cvc} inputMode="numeric" autoComplete="cc-csc" placeholder="123"
              onChange={(e) => { const next = e.target.value.replace(/\D/g, "").slice(0, 4); setCvc(next); setTouched(true); emit({ cvc: next }); }}
              onBlur={() => setTouched(true)}
              className={`${field(showErrors && !cvcOk)} font-mono tabular-nums`} />
          </div>
        </div>

        <label className="flex cursor-pointer items-center gap-3 text-[14px] text-[#18181b]">
          <Checkbox checked={saveCard} onCheckedChange={(v) => { const next = v === true; setSaveCard(next); emit({ saveCard: next }); }} aria-label={text({ en: "Save card for future payment", fr: "Enregistrer pour les prochains paiements" })} />
          <span>{text({ en: "Save card for future payment", fr: "Enregistrer pour les prochains paiements" })}</span>
        </label>
        <p className="flex items-center gap-1.5 text-[12.5px] text-[#6d6d70]">
          <Lock className="size-3.5" strokeWidth={1.8} aria-hidden="true" />
          {text({ en: "This is a secure 128-bit SSL encrypted payment. Card details never touch our servers unencrypted.", fr: "Paiement sécurisé SSL 128 bits. Vos données restent chiffrées." })}
        </p>
      </div>
    </div>
  );
}
