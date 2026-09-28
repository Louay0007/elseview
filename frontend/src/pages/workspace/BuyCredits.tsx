import { useEffect, useMemo, useState } from "react";
import { apiFetch, backendAvailable, newIdempotencyKey } from "@/lib/api";
import { useWorkspace } from "@/components/workspace/WorkspaceContext";
import { Minus, Plus } from "lucide-react";
import { useAuthLocale } from "@/components/auth/AuthLocale";
import { WorkspaceShell, useWorkspaceNav } from "@/components/workspace/WorkspaceShell";
import "@/components/workspace/BuyCredits.css";

const MIN_CREDITS = 50;
const MAX_CREDITS = 1000000;

const TIERS = [
  { credits: 500, discount: 5, unit: 0.95, total: 475 },
  { credits: 1000, discount: 10, unit: 0.9, total: 900 },
  { credits: 1500, discount: 15, unit: 0.85, total: 1275 },
  { credits: 2000, discount: 20, unit: 0.8, total: 1600 },
] as const;

type Copy = { en: string; fr: string };
type Faq = { question: Copy; paragraphs: Copy[]; bullets?: Copy[]; closing?: Copy };

const FAQS: Faq[] = [
  {
    question: { en: "How much does it cost to use Elseview?", fr: "Combien coûte l’utilisation d’Elseview ?" },
    paragraphs: [
      {
        en: "We offer you complete flexibility with our pay-as-you-go pricing, so you will only pay for what you use, without the need to commit to a subscription or contract. This means you can quickly scale your testing requirements up or down depending on the needs of your business.",
        fr: "Nous offrons une flexibilité totale avec notre tarification à l’utilisation : vous payez uniquement ce que vous utilisez, sans abonnement ni contrat. Vous pouvez donc augmenter ou réduire rapidement vos besoins de test selon votre activité.",
      },
      {
        en: "Each credit costs $1. When your account has enough available credits, you will have access to an unlimited number of users, tests and respondents. When you publish your tests, you’ll need to use your credits to be able to recruit testers from the Elseview panel. If you want to use your own group of testers, you can get a free link to share with them to your test – no credits needed.",
        fr: "Chaque crédit coûte 1 $. Avec suffisamment de crédits disponibles, vous accédez à un nombre illimité d’utilisateurs, de tests et de répondants. Pour publier vos tests, utilisez vos crédits afin de recruter des testeurs dans le panel Elseview. Si vous préférez votre propre groupe, envoyez-leur un lien gratuit vers votre test : aucun crédit n’est nécessaire.",
      },
    ],
  },
  {
    question: { en: "What are credits?", fr: "Que sont les crédits ?" },
    paragraphs: [
      {
        en: "Credits are used to recruit testers for your projects and pay them for their time and insights. You’ll need credits to publish any tests using Elseview’s panel.",
        fr: "Les crédits servent à recruter des testeurs pour vos projets et à les rémunérer pour leur temps et leurs avis. Vous aurez besoin de crédits pour publier tout test utilisant le panel Elseview.",
      },
      {
        en: "Credits start at $1 each, with the minimum number of credits you can buy at any one time is 50. If you’re buying 50 credits, you would pay $50 at $1 each. But when you choose to buy your credits in bulk (500 or more), you’ll qualify for a discount. Here’s how it would work:",
        fr: "Les crédits commencent à 1 $ chacun, et le minimum d’achat est de 50 crédits. Pour 50 crédits, vous payez donc 50 $. Mais si vous achetez vos crédits en volume (500 ou plus), vous bénéficiez d’une remise. Voici comment cela fonctionne :",
      },
    ],
    bullets: [
      { en: "500 credits = 5% discount, so you pay $475", fr: "500 crédits = 5 % de remise, donc vous payez 475 $" },
      { en: "1000 credits = 10% discount, so you pay $900", fr: "1 000 crédits = 10 % de remise, donc vous payez 900 $" },
      { en: "1500 credits = 15% discount, so you pay $1275", fr: "1 500 crédits = 15 % de remise, donc vous payez 1 275 $" },
      { en: "2000 credits = 20% discount, so you pay $1600", fr: "2 000 crédits = 20 % de remise, donc vous payez 1 600 $" },
    ],
    closing: {
      en: "The discounts are included on each transaction up to the next bracket, so if you buy between 500 and 1000 credits, you’ll get a 5% discount on your total. All you need to do is add credits to your basket and your discount will be automatically applied.",
      fr: "Les remises s’appliquent à chaque transaction jusqu’au palier suivant : entre 500 et 1 000 crédits, vous obtenez 5 % de remise sur le total. Ajoutez simplement des crédits à votre panier et la remise sera appliquée automatiquement.",
    },
  },
  {
    question: { en: "How many credits do I need to publish a test?", fr: "Combien de crédits faut-il pour publier un test ?" },
    paragraphs: [
      {
        en: "Publishing a test is a set fee of 10 credits. If you want to use our panel, you can use credits to recruit. Depending on the size of the panel you select, and the type and length of your test, the amount of credits you need to use will change. Here’s an overview of average credit costs per respondent:",
        fr: "Publier un test coûte un forfait de 10 crédits. Si vous utilisez notre panel, vous pouvez employer des crédits pour recruter. Selon la taille du panel choisi, ainsi que le type et la durée de votre test, le nombre de crédits nécessaires varie. Voici un aperçu des coûts moyens par répondant :",
      },
    ],
    bullets: [
      { en: "Preference tests (short length tests) - 2 credits per tester", fr: "Tests de préférence (tests courts) - 2 crédits par testeur" },
      { en: "Card sorting, tree testing and online survey (medium length tests) - 6 credits per tester", fr: "Tri de cartes, test d’arborescence et enquête en ligne (tests moyens) - 6 crédits par testeur" },
    ],
    closing: {
      en: "You can also use our credit estimate tool to work out an estimate of how many credits you’ll need to publish your test.",
      fr: "Vous pouvez aussi utiliser notre outil d’estimation pour calculer le nombre de crédits nécessaire à la publication de votre test.",
    },
  },
  {
    question: { en: "How do I purchase credits?", fr: "Comment acheter des crédits ?" },
    paragraphs: [
      {
        en: "You can buy credits through your Elseview account – and you can save money when you buy credits in bulk. Prices start at as little as $0.80 per credit.",
        fr: "Vous pouvez acheter des crédits depuis votre compte Elseview, avec des économies pour les achats en volume. Les prix commencent à seulement 0,80 $ par crédit.",
      },
    ],
  },
];

function quoteFor(count: number) {
  const tier = [...TIERS].reverse().find((entry) => count >= entry.credits);
  const unit = tier ? tier.unit : 1;
  return { unit, total: count * unit };
}

export default function BuyCredits() {
  const { language, text } = useAuthLocale();
  const { firstName, role, displayName, workspaceName, goWithParams } = useWorkspaceNav();
  const [credits, setCredits] = useState("50");
  const { workspaceId } = useWorkspace();
  const [serverQuote, setServerQuote] = useState<number | null>(null);
  const [receipt, setReceipt] = useState<string | null>(null);
  const [buyError, setBuyError] = useState<string | null>(null);
  const [buying, setBuying] = useState(false);

  useEffect(() => {
    if (!backendAvailable() || !workspaceId || !valid) return;
    const timer = window.setTimeout(() => {
      apiFetch<{ total: number }>(`/workspaces/${workspaceId}/billing/credits/estimate`, {
        method: "POST",
        body: { credits: safeCredits },
      })
        .then((result) => setServerQuote(result.total))
        .catch(() => {});
    }, 400);
    return () => window.clearTimeout(timer);
  });

  const checkout = () => {
    if (!backendAvailable() || !workspaceId || !valid || buying) return;
    setBuying(true);
    setBuyError(null);
    void apiFetch<{ id: string }>(`/workspaces/${workspaceId}/billing/credits`, {
      method: "POST",
      idempotencyKey: newIdempotencyKey(),
      body: { credits: safeCredits },
    })
      .then((result) => setReceipt(result.id))
      .catch(() => setBuyError(text({ en: "Could not complete the purchase. Try again.", fr: "Achat impossible. Réessayez." })))
      .finally(() => setBuying(false));
  };
  const [touched, setTouched] = useState(false);
  const [openFaq, setOpenFaq] = useState<boolean[]>(FAQS.map(() => false));

  const parsedCredits = credits === "" ? Number.NaN : Number(credits);
  const valid = Number.isInteger(parsedCredits) && parsedCredits >= MIN_CREDITS && parsedCredits <= MAX_CREDITS;
  const safeCredits = Number.isFinite(parsedCredits) && parsedCredits > 0 ? Math.floor(parsedCredits) : 0;
  const quote = quoteFor(safeCredits);
  const numberFormat = useMemo(() => new Intl.NumberFormat(language === "fr" ? "fr-FR" : "en-US"), [language]);
  const moneyFormat = useMemo(
    () => new Intl.NumberFormat(language === "fr" ? "fr-FR" : "en-US", { style: "currency", currency: "USD" }),
    [language],
  );

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
      <div className="buy-body">
        <h1 className="buy-title">{text({ en: "Buy Credits", fr: "Acheter des crédits" })}</h1>
        <hr className="buy-rule" />

        <div className="buy-panel">
          <div className="buy-left">
            <h2 className="buy-need">{text({ en: "How many credits do you need?", fr: "De combien de crédits avez-vous besoin ?" })}</h2>
            <p className="buy-minimum">
              {text({
                en: "Min. 50 credits per buy.",
                fr: "Un minimum de 50 crédits est requis par transaction.",
              })}
            </p>

            <div className="buy-field">
              <label className="buy-field__label" htmlFor="buy-credits">
                {text({ en: "Credits", fr: "Crédits" })}
              </label>
              <input
                id="buy-credits"
                className="buy-field__input"
                value={credits}
                inputMode="numeric"
                autoComplete="off"
                min={MIN_CREDITS}
                max={MAX_CREDITS}
                aria-invalid={touched && !valid}
                aria-describedby={touched && !valid ? "buy-credits-error" : undefined}
                onChange={(event) => setCredits(event.target.value.replace(/[^\d]/g, "").slice(0, 7))}
                onBlur={() => setTouched(true)}
              />
            </div>
            <p className="buy-rate">
              {text({ en: `1 credit=${moneyFormat.format(quote.unit)}`, fr: `1 crédit = ${moneyFormat.format(quote.unit)}` })}
            </p>
            <p className="buy-discount">
              {text({ en: "Get up to", fr: "Jusqu’à" })}{" "}
              <strong>{text({ en: "20%", fr: "20 %" })}</strong>{" "}
              {text({ en: "discount on bulk amount", fr: "de remise sur les achats en volume" })}
            </p>
            {touched && !valid && (
              <p id="buy-credits-error" role="alert" className="buy-error">
                {text({
                  en: "Enter at least 50 credits.",
                  fr: "Saisissez au moins 50 crédits.",
                })}
              </p>
            )}

            <div className="buy-summary">
              <div>
                <p className="buy-summary__label">
                  {text({ en: `Price for ${numberFormat.format(safeCredits)} credits`, fr: `Prix pour ${numberFormat.format(safeCredits)} crédits` })}
                </p>
                <p className="buy-summary__price">{moneyFormat.format(quote.total)}</p>
              </div>
              <p className="buy-summary__deposit">
                {text({ en: "Credits will be deposited into", fr: "Les crédits seront ajoutés à" })}
                <span className="buy-summary__workspace">{workspaceName}</span>
              </p>
            </div>
            {buyError && <p role="alert" className="buy-error">{buyError}</p>}
            {receipt && <p role="status" className="buy-receipt">{text({ en: "Purchase recorded. Credits are on the way.", fr: "Achat enregistré. Crédits en route." })}</p>}
            <button type="button" className="buy-checkout" disabled={!valid || buying} onClick={checkout}>
              {text({ en: "Check out", fr: "Payer" })}
            </button>
          </div>

          <div className="buy-right">
            <div className="buy-table-head" aria-hidden="true">
              <span>{text({ en: "Credits", fr: "Crédits" })}</span>
              <span>{text({ en: "Price per credit", fr: "Prix par crédit" })}</span>
              <span>{text({ en: "Buy it for", fr: "Acheter pour" })}</span>
            </div>
            {TIERS.map((tier) => (
              <button
                key={tier.credits}
                type="button"
                className={safeCredits === tier.credits ? "buy-tier buy-tier--active" : "buy-tier"}
                aria-pressed={safeCredits === tier.credits}
                onClick={() => {
                  setCredits(String(tier.credits));
                  setTouched(true);
                }}
              >
                <span className="buy-tier__credits">
                  {numberFormat.format(tier.credits)}
                  <span className="buy-tier__save">
                    {text({ en: `Save ${tier.discount}%`, fr: `-${tier.discount} %` })}
                  </span>
                </span>
                <span className="buy-tier__unit">
                  {moneyFormat.format(tier.unit)}
                  {text({ en: "/credit", fr: "/crédit" })}
                </span>
                <span className="buy-tier__total">{moneyFormat.format(tier.total)}</span>
              </button>
            ))}
            <p className="buy-note">
              {text({
                en: "You can use credits to recruit participants from the Elseview panel for your tests at any time. Plus, they don’t expire – so take advantage of bulk-buying discounts now.",
                fr: "Vous pouvez utiliser vos crédits à tout moment pour recruter des participants du panel Elseview. De plus, ils n’expirent pas : profitez dès maintenant des remises sur les achats en volume.",
              })}
            </p>
          </div>
        </div>

        <section aria-labelledby="buy-faq-heading" className="buy-faq">
          <h2 id="buy-faq-heading" className="buy-faq__title">{text({ en: "FAQs", fr: "FAQ" })}</h2>
          {FAQS.map((faq, index) => {
            const open = openFaq[index];
            return (
              <div key={text(faq.question)} className="buy-faq__item">
                <h3>
                  <button
                    type="button"
                    className="buy-faq__button"
                    aria-expanded={open}
                    onClick={() => setOpenFaq((current) => current.map((value, position) => (position === index ? !value : value)))}
                  >
                    {text(faq.question)}
                    {open ? <Minus className="buy-faq__icon" aria-hidden="true" /> : <Plus className="buy-faq__icon" aria-hidden="true" />}
                  </button>
                </h3>
                {open && (
                  <div className="buy-faq__answer">
                    {faq.paragraphs.map((paragraph) => (
                      <p key={paragraph.en}>{text(paragraph)}</p>
                    ))}
                    {faq.bullets && (
                      <ul>
                        {faq.bullets.map((bullet) => (
                          <li key={bullet.en}>{text(bullet)}</li>
                        ))}
                      </ul>
                    )}
                    {faq.closing && <p>{text(faq.closing)}</p>}
                  </div>
                )}
              </div>
            );
          })}
        </section>
      </div>
    </WorkspaceShell>
  );
}
