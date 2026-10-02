import { useMemo, useState } from "react";
import { IdCard, Minus, Plus } from "lucide-react";
import { Link } from "react-router-dom";
import { useAuthLocale } from "@/components/auth/AuthLocale";
import { TesterAccountLayout } from "@/components/tester/TesterAccountHeader";
import { TesterShell } from "@/components/tester/TesterShell";
import {
  CheckboxField, ChipMultiSelect, FormField, RadioGroup, SectionHeading, SelectField, controlClass,
} from "@/components/tester/TesterForm";
import { authWords as words } from "@/lib/auth";
import { countryCallingCodes, getCountryFlag, getCountryName, isValidPhoneNumber, normalizePhoneNumber } from "@/lib/phoneCountries";
import { cn } from "@/lib/utils";
import { ageOn } from "@/pages/auth/testerProfile";
import {
  childrenOptions, disabilityOptions, drivingLicenseOptions, educationOptions, languageOptions,
  otherLanguageOptions, relationshipOptions, religionOptions, type AboutOption,
} from "@/pages/auth/testerAbout";
import {
  clampHouseholdSize, householdIncomeOptions, housingStatusOptions, HOUSEHOLD_MAX, HOUSEHOLD_MIN,
  livingArrangementsOptions,
} from "@/pages/auth/testerHousehold";
import {
  careerStageOptions, companySizeOptions, departmentOptions, employmentStatusOptions,
  industryOptions, isEmployedStatus, workingEnvironmentOptions,
} from "@/pages/auth/testerWork";
import {
  dailyAppOptions, desktopUserTypeOptions, mobileUserTypeOptions, mostUsedDeviceOptions,
  ownedDeviceOptions, screenTimeOptions,
} from "@/pages/auth/testerTech";
import { fitnessOptions, hobbyOptions, petOptions, shoppingFrequencyOptions } from "@/pages/auth/testerLifestyle";
import { bankOptions, paymentMethodOptions } from "@/pages/auth/testerFinance";
import { mockTesterVerified } from "./testerMocks";
import { clearTesterProfile, readTesterProfile, writeTesterProfile, type SavedTesterProfile } from "./testerProfileStore";
import { routes } from "@/lib/routes";

type Localized = { en: string; fr: string };

const copy = {
  account: words("Account", "Compte"),
  scoreIs: words("Your score is", "Votre score est"),
  guidelines: words("Read more about your guidelines", "En savoir plus sur nos règles"),
  save: words("Save updates", "Enregistrer"),
  saved: words("Changes saved", "Modifications enregistrées"),
  tabProfile: words("Your profile", "Votre profil"),
  tabHistory: words("Test history", "Historique des tests"),
  tabWallet: words("Wallet", "Portefeuille"),
  privacyNote: words(
    "Please note that sensitive information in your profile, such as your name, surname, or contact details, will never be shared with the researchers.",
    "Veuillez noter que les informations sensibles de votre profil, telles que votre prénom, nom ou coordonnées, ne seront jamais partagées avec les chercheurs.",
  ),
  privacyLink: words("Learn more about how we use your data.", "En savoir plus sur l’utilisation de vos données."),
  personalInfo: words("Personal information", "Informations personnelles"),
  firstName: words("First name", "Prénom"),
  lastName: words("Last name", "Nom"),
  dob: words("Date of birth", "Date de naissance"),
  nationality: words("Nationality", "Nationalité"),
  residence: words("Country of residency", "Pays de résidence"),
  gender: words("Gender", "Genre"),
  male: words("Male", "Homme"),
  female: words("Female", "Femme"),
  background: words("Personal background", "Contexte personnel"),
  relationship: words("Relationship status", "Situation sentimentale"),
  religion: words("Religion", "Religion"),
  childrenDependents: words("Children and dependents", "Enfants et personnes à charge"),
  education: words("Highest level of education", "Niveau d’études le plus élevé"),
  spokenLanguage: words("Spoken language", "Langues parlées"),
  otherLanguages: words("Other languages", "Autres langues"),
  drivingLicense: words("Driving license", "Permis de conduire"),
  noDrivingLicense: words("I don’t have a driving license", "Je n’ai pas de permis de conduire"),
  disability: words("Disability conditions", "Situation de handicap"),
  noDisability: words("I don’t have any disabilities", "Je n’ai aucun handicap"),
  contact: words("Contact details", "Coordonnées"),
  email: words("Email address", "Adresse e-mail"),
  phone: words("Phone number", "Numéro de téléphone"),
  whatsappNumber: words("WhatsApp number", "Numéro WhatsApp"),
  useWhatsapp: words("I use WhatsApp on this number", "J’utilise WhatsApp sur ce numéro"),
  household: words("Household", "Foyer"),
  housingStatus: words("Housing status", "Statut du logement"),
  livingArrangements: words("Living arrangements", "Composition du foyer"),
  householdIncome: words("Monthly household income (USD)", "Revenu mensuel du foyer (USD)"),
  householdSize: words("How many people live in your household?", "Combien de personnes vivent dans votre foyer ?"),
  decrease: words("Decrease number of people", "Diminuer le nombre de personnes"),
  increase: words("Increase number of people", "Augmenter le nombre de personnes"),
  peopleCount: words("Number of people in the household", "Nombre de personnes dans le foyer"),
  employment: words("Employment & career", "Emploi et carrière"),
  employmentStatus: words("Your employment status", "Votre statut d’emploi"),
  careerStage: words("Career stage", "Stade de carrière"),
  industry: words("What industry do you work in?", "Dans quel secteur travaillez-vous ?"),
  department: words("What department do you work in?", "Dans quel service travaillez-vous ?"),
  companySize: words("Company size", "Taille de l’entreprise"),
  workingEnvironment: words("Working environment", "Environnement de travail"),
  tech: words("Technology usage & preferences", "Usage de la technologie et préférences"),
  screenTime: words("Daily screen time", "Temps d’écran quotidien"),
  mostUsedDevice: words("Most used device", "Appareil le plus utilisé"),
  mobileType: words("Mobile user type", "Profil d’utilisateur mobile"),
  desktopType: words("Desktop user type", "Profil d’utilisateur sur ordinateur"),
  ownedDevices: words("Owned devices", "Appareils que vous possédez"),
  dailyApps: words("Which apps do you rely on every day?", "Sur quelles applications comptez-vous chaque jour ?"),
  lifestyle: words("Lifestyle", "Mode de vie"),
  shoppingFrequency: words("Frequency of online shopping", "Fréquence des achats en ligne"),
  hobbies: words("Hobbies", "Loisirs"),
  fitness: words("Fitness activities", "Activités physiques"),
  noPets: words("I don’t have pets", "Je n’ai pas d’animaux"),
  petsOwned: words("Pets owned", "Animaux possédés"),
  vehicle: words("Do you have a vehicle", "Possédez-vous un véhicule ?"),
  yes: words("Yes", "Oui"),
  no: words("No", "Non"),
  finance: words("Financial & services information", "Informations financières et services"),
  noBankAccount: words("I don’t have a bank account", "Je n’ai pas de compte bancaire"),
  bank: words("What bank do you have?", "Quelle banque utilisez-vous ?"),
  paymentMethods: words("Payment methods used", "Moyens de paiement utilisés"),
  password: words("Password settings", "Paramètres du mot de passe"),
  changePassword: words("Change password", "Changer le mot de passe"),
  deleteAccount: words("Delete account", "Supprimer le compte"),
  deleteWarning: words(
    "Once you delete your account, all tests and unused credits will be removed. This action cannot be undone.",
    "Une fois votre compte supprimé, tous les tests et les crédits non utilisés seront supprimés. Cette action est irréversible.",
  ),
  required: words("This field is required", "Ce champ est requis"),
  verifyNow: words("verify now", "vérifiez maintenant"),
  verifyPrefix: words("To access more tests and enable payouts, please", "Pour accéder à plus de tests et activer les paiements,"),
  verifySuffix: words("Verification may take 3–5 mins. Please have your ID document ready.", "La vérification peut prendre 3 à 5 min. Préparez votre pièce d’identité."),
  confirmDelete: words("Yes, delete my account", "Oui, supprimer mon compte"),
  cancelDelete: words("Cancel", "Annuler"),
};

const asString = (value: unknown) => (typeof value === "string" ? value : "");
const asBool = (value: unknown) => value === true;
const asNumber = (value: unknown, fallback: number) => (typeof value === "number" && Number.isFinite(value) ? value : fallback);
const asList = (value: unknown) => (Array.isArray(value) ? value.filter((v): v is string => typeof v === "string") : []);

export default function TesterProfile() {
  const { text } = useAuthLocale();
  const [profile, setProfile] = useState<SavedTesterProfile>(() => readTesterProfile());
  const [saved, setSaved] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [touched, setTouched] = useState(false);

  const countryOptions = useMemo<AboutOption[]>(
    () => countryCallingCodes
      .map((c) => ({ value: c.iso, en: getCountryName(c, "en"), fr: getCountryName(c, "fr") }))
      .sort((a, b) => a.en.localeCompare(b.en))
      .map((c) => ({ value: c.value, label: { en: c.en, fr: c.fr } })),
    [],
  );

  const set = <K extends keyof SavedTesterProfile>(key: K, value: SavedTesterProfile[K]) => {
    setProfile((current) => ({ ...current, [key]: value }));
    setSaved(false);
  };
  const setNested = (group: "about" | "household" | "work" | "tech" | "lifestyle" | "finance", key: string, value: unknown) => {
    setProfile((current) => ({ ...current, [group]: { ...(current[group] ?? {}), [key]: value } }));
    setSaved(false);
  };

  const about = profile.about ?? {};
  const household = profile.household ?? {};
  const work = profile.work ?? {};
  const tech = profile.tech ?? {};
  const lifestyle = profile.lifestyle ?? {};
  const finance = profile.finance ?? {};

  const employed = isEmployedStatus(asString(work.employmentStatus));
  const size = asNumber(household.householdSize, 1);
  const error = (condition: boolean) => touched && condition;
  const age = ageOn(profile.dob);
  const countryIso = profile.countryIso ?? "TN";
  const callingCode = profile.callingCode ?? "216";
  const emailInvalid = !profile.email?.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(profile.email);
  const phoneInvalid = !profile.phone?.trim() || !isValidPhoneNumber(normalizePhoneNumber(profile.phone, callingCode, countryIso), callingCode, countryIso);
  const profileInvalid = !profile.firstName.trim() || !profile.lastName.trim() || !profile.dob || age === null || age < 18 || age > 120 || !profile.nationality || !profile.residence || !profile.gender || emailInvalid || phoneInvalid;

  const save = () => {
    setTouched(true);
    if (profileInvalid) {
      const firstInvalid = !profile.firstName.trim() ? "profile-first-name" : !profile.lastName.trim() ? "profile-last-name" : !profile.dob || age === null || age < 18 || age > 120 ? "profile-dob" : !profile.nationality ? "profile-nationality" : !profile.residence ? "profile-residence" : !profile.gender ? "Gender-male" : emailInvalid ? "profile-email" : "profile-phone";
      document.getElementById(firstInvalid)?.focus();
      return;
    }
    setSaved(writeTesterProfile(profile));
  };

  const saveButton = (
    <button
      type="button"
      onClick={save}
      disabled={saved}
      className={cn(
        "inline-flex min-h-11 items-center rounded-full px-6 text-[14px] font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1E3A8A] focus-visible:ring-offset-2",
        saved ? "bg-[#dcfce7] text-[#15803d]" : "bg-[#0F1E3D] text-white hover:bg-[#1E3A8A]",
      )}
    >
      {saved ? text(copy.saved) : text(copy.save)}
    </button>
  );

  return (
    <TesterShell>
      <TesterAccountLayout active="profile" firstName={profile.firstName}>

      <div className="mt-5 flex justify-end">{saveButton}</div>

      {!mockTesterVerified && (
        <p id="guidelines" className="mt-5 flex flex-wrap items-center gap-2 rounded-[10px] border border-[#DCE4F2] bg-[#E8EFFB] px-3.5 py-2.5 text-[13px] text-[#0F1E3D]">
          <IdCard className="size-4 shrink-0 text-[#1E3A8A]" strokeWidth={1.8} aria-hidden="true" />
          <span>{text(copy.verifyPrefix)} <a href={routes.testerOnboarding} className="rounded font-semibold text-[#1E3A8A] underline underline-offset-2">{text(copy.verifyNow)}</a> {text(copy.verifySuffix)}</span>
        </p>
      )}

      <p className="mt-5 max-w-[64ch] text-[13.5px] leading-relaxed text-[#0F1E3D]">
        {text(copy.privacyNote)}{" "}
        <a href={routes.privacy} className="rounded text-[#1E3A8A] underline underline-offset-2">{text(copy.privacyLink)}</a>
      </p>

      <div className="mt-7 space-y-5">
        <section className="space-y-4 rounded-2xl border border-[#DCE4F2] bg-[#F7F9FD] p-5 sm:p-6">
          <SectionHeading>{copy.personalInfo}</SectionHeading>
          <div className="grid gap-4 sm:grid-cols-2">
            <TextField id="profile-first-name" label={copy.firstName} value={profile.firstName} onChange={(v) => set("firstName", v)} required invalid={error(!profile.firstName.trim())} />
            <TextField id="profile-last-name" label={copy.lastName} value={profile.lastName} onChange={(v) => set("lastName", v)} required invalid={error(!profile.lastName.trim())} />
            <DateField id="profile-dob" label={copy.dob} value={profile.dob} onChange={(v) => set("dob", v)} required invalid={error(!profile.dob)} />
            <SelectField id="profile-nationality" label={copy.nationality} value={profile.nationality} options={countryOptions} onChange={(v) => set("nationality", v)} required invalid={error(!profile.nationality)} />
            <SelectField id="profile-residence" label={copy.residence} value={profile.residence} options={countryOptions} onChange={(v) => set("residence", v)} required invalid={error(!profile.residence)} />
          </div>
          <RadioGroup
            legend={copy.gender}
            value={profile.gender}
            onChange={(v) => set("gender", v)}
            options={[{ value: "male", label: copy.male }, { value: "female", label: copy.female }]}
          />
        </section>

        <section className="space-y-4 rounded-2xl border border-[#DCE4F2] bg-[#F7F9FD] p-5 sm:p-6">
          <SectionHeading>{copy.background}</SectionHeading>
          <div className="grid gap-4 sm:grid-cols-2">
            <SelectField id="profile-relationship" label={copy.relationship} value={asString(about.relationship)} options={relationshipOptions} onChange={(v) => setNested("about", "relationship", v)} />
            <SelectField id="profile-religion" label={copy.religion} value={asString(about.religion)} options={religionOptions} onChange={(v) => setNested("about", "religion", v)} />
            <SelectField id="profile-children" label={copy.childrenDependents} value={asString(about.children)} options={childrenOptions} onChange={(v) => setNested("about", "children", v)} />
            <SelectField id="profile-education" label={copy.education} value={asString(about.education)} options={educationOptions} onChange={(v) => setNested("about", "education", v)} />
          </div>
          <ChipMultiSelect id="profile-languages" label={copy.spokenLanguage} options={languageOptions} selected={asList(about.languages)} onChange={(v) => setNested("about", "languages", v)} />
          <div className="grid gap-4 sm:grid-cols-2">
            <SelectField id="profile-other-language" label={copy.otherLanguages} value={asString(about.otherLanguage)} options={otherLanguageOptions} onChange={(v) => setNested("about", "otherLanguage", v)} />
            <div className="space-y-3">
              <CheckboxField id="profile-no-license" label={copy.noDrivingLicense} checked={asBool(about.noDrivingLicense)} onChange={(v) => setNested("about", "noDrivingLicense", v)} />
              <SelectField id="profile-license" label={copy.drivingLicense} value={asString(about.drivingLicense)} options={drivingLicenseOptions} disabled={asBool(about.noDrivingLicense)} onChange={(v) => setNested("about", "drivingLicense", v)} />
            </div>
          </div>
          <div className="space-y-3">
            <CheckboxField id="profile-no-disability" label={copy.noDisability} checked={asBool(about.noDisability)} onChange={(v) => setNested("about", "noDisability", v)} />
            <SelectField id="profile-disability" label={copy.disability} value={asString(about.disability)} options={disabilityOptions} disabled={asBool(about.noDisability)} onChange={(v) => setNested("about", "disability", v)} className="max-w-[300px]" />
          </div>
        </section>

        <section className="space-y-4 rounded-2xl border border-[#DCE4F2] bg-[#F7F9FD] p-5 sm:p-6">
          <SectionHeading>{copy.contact}</SectionHeading>
          <div className="grid gap-4 sm:grid-cols-2">
            <TextField id="profile-email" type="email" label={copy.email} value={profile.email ?? ""} onChange={(v) => set("email", v)} required invalid={error(emailInvalid)} />
            <PhoneField id="profile-phone" label={copy.phone} value={profile.phone ?? ""} callingCode={callingCode} countryIso={countryIso} onChange={(v) => set("phone", v)} invalid={error(phoneInvalid)} />
            <PhoneField id="profile-whatsapp" label={copy.whatsappNumber} value={profile.whatsappPhone ?? profile.phone ?? ""} callingCode={callingCode} countryIso={countryIso} onChange={(v) => set("whatsappPhone", v)} required={false} />
            <div className="flex items-end pb-1">
              <CheckboxField id="profile-use-whatsapp" label={copy.useWhatsapp} checked={asBool(profile.whatsapp)} onChange={(v) => set("whatsapp", v)} />
            </div>
          </div>
        </section>

        <section className="space-y-4 rounded-2xl border border-[#DCE4F2] bg-[#F7F9FD] p-5 sm:p-6">
          <SectionHeading>{copy.household}</SectionHeading>
          <div className="grid gap-4 sm:grid-cols-2">
            <SelectField id="profile-housing" label={copy.housingStatus} value={asString(household.housingStatus)} options={housingStatusOptions} onChange={(v) => setNested("household", "housingStatus", v)} />
            <SelectField id="profile-arrangements" label={copy.livingArrangements} value={asString(household.livingArrangements)} options={livingArrangementsOptions} onChange={(v) => setNested("household", "livingArrangements", v)} />
            <SelectField id="profile-income" label={copy.householdIncome} value={asString(household.monthlyIncome)} options={householdIncomeOptions} onChange={(v) => setNested("household", "monthlyIncome", v)} />
          </div>
          <FormField label={copy.householdSize}>
            <div className="inline-flex h-11 items-stretch overflow-hidden rounded-lg border border-[#CDD9EC] bg-white">
              <button
                type="button"
                onClick={() => setNested("household", "householdSize", clampHouseholdSize(size - 1))}
                disabled={size <= HOUSEHOLD_MIN}
                aria-label={text(copy.decrease)}
                className="grid w-11 place-items-center text-[#1E3A8A] transition hover:bg-[#E3EBFA] disabled:cursor-not-allowed disabled:text-[#C3CEDE] disabled:hover:bg-transparent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[#1E3A8A]"
              >
                <Minus className="size-4" strokeWidth={2.2} aria-hidden="true" />
              </button>
              <input
                id="profile-household-size"
                type="number"
                inputMode="numeric"
                min={HOUSEHOLD_MIN}
                max={HOUSEHOLD_MAX}
                value={size}
                onChange={(e) => {
                  const parsed = Number.parseInt(e.target.value, 10);
                  setNested("household", "householdSize", Number.isNaN(parsed) ? HOUSEHOLD_MIN : clampHouseholdSize(parsed));
                }}
                aria-label={text(copy.peopleCount)}
                className="h-full w-14 border-x border-[#DCE4F2] bg-transparent text-center text-[14.5px] font-semibold text-[#0F1E3D] outline-none [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
              />
              <button
                type="button"
                onClick={() => setNested("household", "householdSize", clampHouseholdSize(size + 1))}
                disabled={size >= HOUSEHOLD_MAX}
                aria-label={text(copy.increase)}
                className="grid w-11 place-items-center text-[#1E3A8A] transition hover:bg-[#E3EBFA] disabled:cursor-not-allowed disabled:text-[#C3CEDE] disabled:hover:bg-transparent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[#1E3A8A]"
              >
                <Plus className="size-4" strokeWidth={2.2} aria-hidden="true" />
              </button>
            </div>
          </FormField>
        </section>

        <section className="space-y-4 rounded-2xl border border-[#DCE4F2] bg-[#F7F9FD] p-5 sm:p-6">
          <SectionHeading>{copy.employment}</SectionHeading>
          <div className="grid gap-4 sm:grid-cols-2">
            <SelectField id="profile-employment" label={copy.employmentStatus} value={asString(work.employmentStatus)} options={employmentStatusOptions} onChange={(v) => setNested("work", "employmentStatus", v)} />
            <SelectField id="profile-career-stage" label={copy.careerStage} value={asString(work.careerStage)} options={careerStageOptions} disabled={!employed} onChange={(v) => setNested("work", "careerStage", v)} />
            <SelectField id="profile-industry" label={copy.industry} value={asString(work.industry)} options={industryOptions} disabled={!employed} onChange={(v) => setNested("work", "industry", v)} />
            <SelectField id="profile-department" label={copy.department} value={asString(work.department)} options={departmentOptions} disabled={!employed} onChange={(v) => setNested("work", "department", v)} />
            <SelectField id="profile-company-size" label={copy.companySize} value={asString(work.companySize)} options={companySizeOptions} disabled={!employed} onChange={(v) => setNested("work", "companySize", v)} />
            <SelectField id="profile-environment" label={copy.workingEnvironment} value={asString(work.workingEnvironment)} options={workingEnvironmentOptions} onChange={(v) => setNested("work", "workingEnvironment", v)} />
          </div>
        </section>

        <section className="space-y-4 rounded-2xl border border-[#DCE4F2] bg-[#F7F9FD] p-5 sm:p-6">
          <SectionHeading>{copy.tech}</SectionHeading>
          <div className="grid gap-4 sm:grid-cols-2">
            <SelectField id="profile-screen-time" label={copy.screenTime} value={asString(tech.screenTime)} options={screenTimeOptions} onChange={(v) => setNested("tech", "screenTime", v)} />
            <SelectField id="profile-most-used" label={copy.mostUsedDevice} value={asString(tech.mostUsedDevice)} options={mostUsedDeviceOptions} onChange={(v) => setNested("tech", "mostUsedDevice", v)} />
            <SelectField id="profile-mobile-type" label={copy.mobileType} value={asString(tech.mobileUserType)} options={mobileUserTypeOptions} onChange={(v) => setNested("tech", "mobileUserType", v)} />
            <SelectField id="profile-desktop-type" label={copy.desktopType} value={asString(tech.desktopUserType)} options={desktopUserTypeOptions} onChange={(v) => setNested("tech", "desktopUserType", v)} />
          </div>
          <ChipMultiSelect id="profile-devices" label={copy.ownedDevices} options={ownedDeviceOptions} selected={asList(tech.ownedDevices)} onChange={(v) => setNested("tech", "ownedDevices", v)} />
          <ChipMultiSelect id="profile-apps" label={copy.dailyApps} options={dailyAppOptions} selected={asList(tech.dailyApps)} onChange={(v) => setNested("tech", "dailyApps", v)} />
        </section>

        <section className="space-y-4 rounded-2xl border border-[#DCE4F2] bg-[#F7F9FD] p-5 sm:p-6">
          <SectionHeading>{copy.lifestyle}</SectionHeading>
          <div className="grid gap-4 sm:grid-cols-2">
            <SelectField id="profile-shopping" label={copy.shoppingFrequency} value={asString(lifestyle.shoppingFrequency)} options={shoppingFrequencyOptions} onChange={(v) => setNested("lifestyle", "shoppingFrequency", v)} />
            <ChipMultiSelect id="profile-hobbies" label={copy.hobbies} options={hobbyOptions} selected={asList(lifestyle.hobby)} onChange={(v) => setNested("lifestyle", "hobby", v)} />
            <ChipMultiSelect id="profile-fitness" label={copy.fitness} options={fitnessOptions} selected={asList(lifestyle.fitness)} onChange={(v) => setNested("lifestyle", "fitness", v)} />
          </div>
          <div className="space-y-3">
            <CheckboxField id="profile-no-pets" label={copy.noPets} checked={asBool(lifestyle.noPets)} onChange={(v) => setNested("lifestyle", "noPets", v)} />
            <SelectField id="profile-pets" label={copy.petsOwned} value={asString(lifestyle.petsOwned)} options={petOptions} disabled={asBool(lifestyle.noPets)} onChange={(v) => setNested("lifestyle", "petsOwned", v)} className="max-w-[300px]" />
          </div>
          <RadioGroup
            legend={copy.vehicle}
            value={asString(lifestyle.hasVehicle)}
            onChange={(v) => setNested("lifestyle", "hasVehicle", v)}
            options={[{ value: "yes", label: copy.yes }, { value: "no", label: copy.no }]}
          />
        </section>

        <section className="space-y-4 rounded-2xl border border-[#DCE4F2] bg-[#F7F9FD] p-5 sm:p-6">
          <SectionHeading>{copy.finance}</SectionHeading>
          <div className="space-y-3">
            <CheckboxField id="profile-no-bank" label={copy.noBankAccount} checked={asBool(finance.noBankAccount)} onChange={(v) => setNested("finance", "noBankAccount", v)} />
            <SelectField id="profile-bank" label={copy.bank} value={asString(finance.bank)} options={bankOptions} disabled={asBool(finance.noBankAccount)} onChange={(v) => setNested("finance", "bank", v)} className="max-w-[300px]" />
          </div>
          <ChipMultiSelect id="profile-payments" label={copy.paymentMethods} options={paymentMethodOptions} selected={asList(finance.paymentMethods)} onChange={(v) => setNested("finance", "paymentMethods", v)} />
        </section>

        <div className="pt-1">{saveButton}</div>

        <section className="space-y-3 rounded-2xl border border-[#DCE4F2] bg-[#F7F9FD] p-5 sm:p-6">
          <SectionHeading>{copy.password}</SectionHeading>
          <Link to={routes.resetPassword} className="inline-flex min-h-11 items-center rounded-full border border-[#1E3A8A] bg-white px-5 text-[14px] font-semibold text-[#1E3A8A] transition hover:bg-[#E3EBFA] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1E3A8A] focus-visible:ring-offset-2">
            {text(copy.changePassword)}
          </Link>
        </section>
        <section className="space-y-3 rounded-2xl border border-[#DCE4F2] bg-[#F7F9FD] p-5 sm:p-6">
          <SectionHeading>{copy.deleteAccount}</SectionHeading>
          <p className="max-w-[70ch] text-[13.5px] leading-relaxed text-[#0F1E3D]">{text(copy.deleteWarning)}</p>
          {confirmingDelete ? (
            <div className="flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={() => { clearTesterProfile(); setProfile(readTesterProfile()); setSaved(false); setTouched(false); setConfirmingDelete(false); }}
                className="inline-flex min-h-11 items-center rounded-full bg-[#d92d20] px-5 text-[14px] font-semibold text-white transition hover:bg-[#b42318] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1E3A8A] focus-visible:ring-offset-2"
              >
                {text(copy.confirmDelete)}
              </button>
              <button type="button" onClick={() => setConfirmingDelete(false)} className="inline-flex min-h-11 items-center rounded-full border border-[#CDD9EC] bg-white px-5 text-[14px] font-semibold text-[#0F1E3D] transition hover:bg-[#F2F5FA] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1E3A8A]">
                {text(copy.cancelDelete)}
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setConfirmingDelete(true)}
              className="inline-flex min-h-11 items-center rounded-full border border-[#d92d20] bg-white px-5 text-[14px] font-semibold text-[#d92d20] transition hover:bg-[#fef3f2] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1E3A8A] focus-visible:ring-offset-2"
            >
              {text(copy.deleteAccount)}
            </button>
          )}
        </section>
      </div>
      </TesterAccountLayout>
    </TesterShell>
  );
}

function TextField({ id, label, value, onChange, type = "text", required, invalid, readOnly }: {
  id: string; label: Localized; value: string; onChange: (value: string) => void;
  type?: string; required?: boolean; invalid?: boolean; readOnly?: boolean;
}) {
  return (
    <FormField label={label} required={required} htmlFor={id} error={invalid ? copy.required : undefined}>
      <input
        id={id}
        type={type}
        value={value}
        readOnly={readOnly}
        onChange={(e) => onChange(e.target.value)}
        aria-invalid={invalid || undefined}
        className={cn(controlClass, invalid && "border-[#d92d20]", readOnly && "bg-[#F2F5FA] text-[#5A6B87]")}
      />
    </FormField>
  );
}

function DateField({ id, label, value, onChange, required, invalid }: {
  id: string; label: Localized; value: string; onChange: (value: string) => void; required?: boolean; invalid?: boolean;
}) {
  return (
    <FormField label={label} required={required} htmlFor={id} error={invalid ? copy.required : undefined}>
      <input
        id={id}
        type="date"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        aria-invalid={invalid || undefined}
        className={cn(controlClass, "appearance-none pr-9", invalid && "border-[#d92d20]")}
      />
    </FormField>
  );
}

function PhoneField({ id, label, value, callingCode, countryIso, invalid, required = true, onChange }: { id: string; label: Localized; value: string; callingCode: string; countryIso: string; invalid?: boolean; required?: boolean; onChange: (value: string) => void }) {
  const { text } = useAuthLocale();
  return (
    <FormField label={label} required={required} htmlFor={id} error={invalid ? copy.required : undefined}>
      <div className={cn("flex h-11 items-stretch overflow-hidden rounded-lg border bg-white focus-within:border-[#1E3A8A] focus-within:ring-2 focus-within:ring-[#1E3A8A]/25", invalid ? "border-[#d92d20]" : "border-[#CDD9EC]")}>
        <span aria-hidden="true" className="flex items-center gap-1.5 border-r border-[#DCE4F2] bg-[#F7F9FD] px-2.5 text-[13px] text-[#0F1E3D]">
          <span>{getCountryFlag(countryIso)}</span><span>+{callingCode}</span>
        </span>
        <input
          id={id}
          type="tel"
          inputMode="tel"
          dir="ltr"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={text(copy.phone)}
          className="min-w-0 flex-1 bg-transparent px-3 text-[14.5px] text-[#0F1E3D] outline-none placeholder:text-[#6E8098]"
        />
      </div>
    </FormField>
  );
}
