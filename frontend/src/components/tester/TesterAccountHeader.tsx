import { Link } from "react-router-dom";
import { useAuthLocale } from "@/components/auth/AuthLocale";
import { authWords as words } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { mockTesterRating } from "@/pages/tester/testerMocks";
import { routes } from "@/lib/routes";

/** The four sections the account area is split into, in reading order. */
const accountTabs = [
  { key: "profile", path: routes.testerProfile, label: words("Your profile", "Votre profil") },
  { key: "history", path: routes.testerHistory, label: words("Test history", "Historique des tests") },
  { key: "wallet", path: routes.testerEarnings, label: words("Wallet", "Portefeuille") },
  { key: "notifications", path: routes.testerNotifications, label: words("Notification settings", "Notifications") },
] as const;

export type AccountTabKey = (typeof accountTabs)[number]["key"];

const copy = {
  account: words("Account", "Compte"),
  scoreIs: words("Your score is", "Votre score est"),
  guidelines: words("Read more about your guidelines", "En savoir plus sur nos règles"),
};

/**
 * Title, score and section tabs shared by every account page. Each section is its
 * own route so a tester can be linked straight to their test history, and the
 * active tab is derived from the caller rather than from the URL so the header
 * still highlights correctly on a route that has no dedicated page.
 */
/**
 * Account tabs plus page body. The width and centring come from the shell so
 * these pages match every other tester page, and the tabs therefore line up
 * with the content below them.
 */
export function TesterAccountLayout({ active, firstName, children }: {
  active: AccountTabKey;
  firstName?: string;
  children: React.ReactNode;
}) {
  return (
    <>
      <TesterAccountHeader active={active} firstName={firstName} />
      {children}
    </>
  );
}

export function TesterAccountHeader({ active, firstName }: { active: AccountTabKey; firstName?: string }) {
  const { text } = useAuthLocale();
  const name = firstName?.trim();
  const withName = (path: string) => (name ? `${path}${path.includes("?") ? "&" : "?"}firstName=${encodeURIComponent(name)}` : path);

  return (
    <>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-[28px] font-bold tracking-[-0.02em] text-[#0F1E3D]">{text(copy.account)}</h1>
          <p className="mt-2 flex flex-wrap items-center gap-2 text-[14px]">
            <span className="rounded-full bg-[#E3EBFA] px-2.5 py-1 text-[#1E3A8A]">{text(copy.scoreIs)} {mockTesterRating}%</span>
            <a href={`${routes.testerProfile}#guidelines`} className="rounded text-[#1E3A8A] underline underline-offset-2 hover:text-[#0F1E3D] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1E3A8A]">{text(copy.guidelines)}</a>
          </p>
        </div>
      </div>

      <div aria-hidden="true" className="mt-6 h-1 w-16 rounded-full bg-[#1E3A8A]" />

      <nav aria-label={text(copy.account)} className="mt-4 flex flex-wrap gap-6 border-b border-[#DCE4F2]">
        {accountTabs.map((tab) => (
          <Link
            key={tab.key}
            to={withName(tab.path)}
            aria-current={tab.key === active ? "page" : undefined}
            className={cn(
              "min-h-11 border-b-2 text-[14.5px] font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1E3A8A]",
              tab.key === active ? "border-[#1E3A8A] text-[#1E3A8A]" : "border-transparent text-[#5A6B87] hover:text-[#0F1E3D]",
            )}
          >
            {text(tab.label)}
          </Link>
        ))}
      </nav>
    </>
  );
}
