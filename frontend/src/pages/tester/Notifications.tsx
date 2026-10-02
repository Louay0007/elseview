import { useMemo, useState } from "react";
import { Lock } from "lucide-react";
import { useAuthLocale } from "@/components/auth/AuthLocale";
import { TesterAccountLayout } from "@/components/tester/TesterAccountHeader";
import { TesterShell } from "@/components/tester/TesterShell";
import { Switch } from "@/components/ui/switch";
import { authWords as words } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { readTesterProfile } from "./testerProfileStore";
import { routes } from "@/lib/routes";

const copy = {
  emailHeading: words("Email notifications", "Notifications par e-mail"),
  emailIntro: words("Choose the emails and notifications you want to receive from us at your registered email.", "Choisissez les e-mails et notifications que vous souhaitez recevoir à votre adresse enregistrée."),
  registeredEmail: words("Notifications are sent to", "Les notifications sont envoyées à"),
  changeEmail: words("Change email address", "Modifier l’adresse e-mail"),
  testingGroup: words("About your testing", "Au sujet de vos tests"),
  accountGroup: words("About your account", "Au sujet de votre compte"),
  marketingGroup: words("Marketing", "Marketing"),
  systemGroup: words("Required", "Obligatoires"),
  testingTitle: words("New tests available", "Nouveaux tests disponibles"),
  testingBody: words("Be first to know when a study that matches your profile opens.", "Soyez informé dès qu’une étude correspondant à votre profil est ouverte."),
  sessionTitle: words("Session reminders", "Rappels de séance"),
  sessionBody: words("A reminder before each session you have booked, and when its time changes.", "Un rappel avant chaque séance réservée et en cas de changement d’horaire."),
  resultsTitle: words("Results and feedback", "Résultats et retours"),
  resultsBody: words("When a researcher shares the outcome of a test you completed.", "Lorsqu’un chercheur publie les résultats d’un test que vous avez effectué."),
  accountTitle: words("Account related notifications", "Notifications liées au compte"),
  accountBody: words("Based on your account activity we will send you emails to guide your next steps.", "Selon votre activité, nous vous enverrons des e-mails pour guider vos prochaines étapes."),
  payoutTitle: words("Payouts", "Retraits"),
  payoutBody: words("Confirmation when a payout is requested, processed or paid to your account.", "Confirmation lorsqu’un retrait est demandé, traité ou versé sur votre compte."),
  securityTitle: words("Security and sign-in", "Sécurité et connexion"),
  securityBody: words("Alerts when your email or password changes, or a new device signs in.", "Alertes en cas de changement d’e-mail ou de mot de passe, ou de connexion depuis un nouvel appareil."),
  marketingTitle: words("Marketing notifications", "Notifications marketing"),
  marketingBody: words("Email notifications about Elseview updates, new features, offers and latest trends.", "E-mails sur les nouveautés d’Elseview, les nouvelles fonctions, les offres et les tendances."),
  systemTitle: words("System notifications", "Notifications système"),
  systemBody: words("You are receiving these notifications because you agreed to our", "Vous recevez ces notifications car vous avez accepté notre"),
  systemSuffix: words("If you no longer wish to receive these notifications please delete your account.", "Si vous ne souhaitez plus les recevoir, supprimez votre compte."),
  alwaysOn: words("Always on", "Toujours actives"),
  privacyLink: words("privacy policy", "politique de confidentialité"),
  termsLink: words("terms of use", "conditions d’utilisation"),
  save: words("Save preferences", "Enregistrer"),
  saved: words("Preferences saved", "Préférences enregistrées"),
  on: words("On", "Activées"),
  off: words("Off", "Désactivées"),
};

/** Every preference the tester can switch off. System notices are not optional. */
type Preferences = {
  newTests: boolean;
  sessionReminders: boolean;
  results: boolean;
  account: boolean;
  payouts: boolean;
  security: boolean;
  marketing: boolean;
};

const initial: Preferences = {
  newTests: true,
  sessionReminders: true,
  results: true,
  account: true,
  payouts: true,
  security: true,
  marketing: false,
};

export default function TesterNotifications() {
  const { text } = useAuthLocale();
  const [prefs, setPrefs] = useState<Preferences>(initial);
  const [saved, setSaved] = useState(false);
  const profile = useMemo(() => readTesterProfile(), []);

  const set = <K extends keyof Preferences>(key: K, value: boolean) => {
    setPrefs((current) => ({ ...current, [key]: value }));
    setSaved(false);
  };

  const enabledCount = Object.values(prefs).filter(Boolean).length;

  return (
    <TesterShell>
      <TesterAccountLayout active="notifications" firstName={profile.firstName}>

      <div className="mt-6">
        <h2 className="flex items-center gap-2.5 text-[15px] font-bold text-[#0F1E3D]">
          <span aria-hidden="true" className="h-4 w-1 rounded-full bg-[#1E3A8A]" />
          {text(copy.emailHeading)}
        </h2>
        <p className="mt-2 max-w-[68ch] text-[14px] leading-relaxed text-[#5A6B87]">{text(copy.emailIntro)}</p>

        {profile.email && (
          <p className="mt-4 flex flex-wrap items-center gap-2 rounded-xl border border-[#DCE4F2] bg-[#F7F9FD] px-4 py-3 text-[13.5px]">
            <span className="text-[#5A6B87]">{text(copy.registeredEmail)}</span>
            <span className="font-semibold break-all text-[#0F1E3D]">{profile.email}</span>
            <a href={routes.testerProfile} className="rounded font-semibold text-[#1E3A8A] underline underline-offset-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1E3A8A]">{text(copy.changeEmail)}</a>
          </p>
        )}
      </div>

      <div className="mt-8 space-y-5">
        <PreferenceGroup title={copy.testingGroup}>
          <PreferenceRow id="pref-new-tests" title={copy.testingTitle} body={copy.testingBody} checked={prefs.newTests} onChange={(value) => set("newTests", value)} />
          <PreferenceRow id="pref-sessions" title={copy.sessionTitle} body={copy.sessionBody} checked={prefs.sessionReminders} onChange={(value) => set("sessionReminders", value)} />
          <PreferenceRow id="pref-results" title={copy.resultsTitle} body={copy.resultsBody} checked={prefs.results} onChange={(value) => set("results", value)} />
        </PreferenceGroup>

        <PreferenceGroup title={copy.accountGroup}>
          <PreferenceRow id="pref-account" title={copy.accountTitle} body={copy.accountBody} checked={prefs.account} onChange={(value) => set("account", value)} />
          <PreferenceRow id="pref-payouts" title={copy.payoutTitle} body={copy.payoutBody} checked={prefs.payouts} onChange={(value) => set("payouts", value)} />
          <PreferenceRow id="pref-security" title={copy.securityTitle} body={copy.securityBody} checked={prefs.security} onChange={(value) => set("security", value)} />
        </PreferenceGroup>

        <PreferenceGroup title={copy.marketingGroup}>
          <PreferenceRow id="pref-marketing" title={copy.marketingTitle} body={copy.marketingBody} checked={prefs.marketing} onChange={(value) => set("marketing", value)} />
        </PreferenceGroup>

        <section className="rounded-2xl border border-[#DCE4F2] bg-[#F7F9FD] p-5 sm:p-6">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-[15px] font-bold text-[#0F1E3D]">{text(copy.systemTitle)}</h3>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-[#E3EBFA] px-2.5 py-1 text-[12px] font-semibold text-[#1E3A8A]">
              <Lock className="size-3" strokeWidth={2.2} aria-hidden="true" />
              {text(copy.alwaysOn)}
            </span>
          </div>
          <p className="mt-2 max-w-[68ch] text-[13.5px] leading-relaxed text-[#5A6B87]">
            {text(copy.systemBody)}{" "}
            <a href={routes.privacy} className="rounded text-[#1E3A8A] underline underline-offset-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1E3A8A]">{text(copy.privacyLink)}</a>{" "}
            {text(words("and", "et"))}{" "}
            <a href={routes.terms} className="rounded text-[#1E3A8A] underline underline-offset-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1E3A8A]">{text(copy.termsLink)}</a>.{" "}
            {text(copy.systemSuffix)}
          </p>
        </section>
      </div>

      <div className="mt-8 flex flex-wrap items-center gap-4">
        <button
          type="button"
          onClick={() => setSaved(true)}
          disabled={saved}
          className={cn(
            "inline-flex min-h-11 items-center rounded-full px-6 text-[14px] font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1E3A8A] focus-visible:ring-offset-2",
            saved ? "bg-[#DCFCE7] text-[#15803D]" : "bg-[#0F1E3D] text-white hover:bg-[#1E3A8A]",
          )}
        >
          {text(saved ? copy.saved : copy.save)}
        </button>
        <p role="status" className="text-[13px] text-[#5A6B87]">
          {enabledCount} / {Object.keys(prefs).length} {text(copy.on)}
        </p>
      </div>
      </TesterAccountLayout>
    </TesterShell>
  );
}

function PreferenceGroup({ title, children }: { title: ReturnType<typeof words>; children: React.ReactNode }) {
  const { text } = useAuthLocale();
  return (
    <fieldset className="rounded-2xl border border-[#DCE4F2] bg-white p-5 sm:p-6">
      <legend className="px-1 text-[13px] font-semibold uppercase tracking-wide text-[#5A6B87]">{text(title)}</legend>
      <div className="divide-y divide-[#EEF2F9]">{children}</div>
    </fieldset>
  );
}

/** One preference: a title, the reason it exists, and the switch that controls it. */
function PreferenceRow({ id, title, body, checked, onChange }: {
  id: string;
  title: ReturnType<typeof words>;
  body: ReturnType<typeof words>;
  checked: boolean;
  onChange: (value: boolean) => void;
}) {
  const { text } = useAuthLocale();
  return (
    <div className="flex items-start justify-between gap-6 py-4 first:pt-1 last:pb-1">
      <div className="min-w-0">
        <label htmlFor={id} className="block cursor-pointer text-[15px] font-semibold text-[#0F1E3D]">{text(title)}</label>
        <p className="mt-1 max-w-[58ch] text-[13.5px] leading-relaxed text-[#5A6B87]">{text(body)}</p>
      </div>
      <Switch
        id={id}
        checked={checked}
        onCheckedChange={onChange}
        aria-label={text(title)}
        className="mt-1 h-6 w-11 shrink-0 rounded-full border-2 border-[#CDD9EC] data-[state=checked]:border-[#1E3A8A] data-[state=checked]:bg-[#1E3A8A]"
      />
    </div>
  );
}
