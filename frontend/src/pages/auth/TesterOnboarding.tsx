import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft, ArrowRight, CalendarDays, ChevronDown, CircleDollarSign, Clock3, Flag, IdCard, KeyRound, Minus, Plus, ShieldCheck, Star } from "lucide-react";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { useAuthLocale } from "@/components/auth/AuthLocale";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { MediterraLogo } from "@/components/MediterraLogo";
import { authWords as words } from "@/lib/auth";
import { countryCallingCodes, defaultCountryIso, getCountryFlag, getCountryName } from "@/lib/phoneCountries";
import { ageOn, testerContactValid, testerProfileValid } from "@/pages/auth/testerProfile";
import {
  childrenOptions,
  disabilityOptions,
  drivingLicenseOptions,
  educationOptions,
  languageOptions,
  otherLanguageOptions,
  relationshipOptions,
  religionOptions,
  testerAboutValid,
  type AboutOption,
} from "@/pages/auth/testerAbout";
import {
  clampHouseholdSize,
  householdIncomeOptions,
  housingStatusOptions,
  HOUSEHOLD_MAX,
  HOUSEHOLD_MIN,
  livingArrangementsOptions,
  testerHouseholdValid,
} from "@/pages/auth/testerHousehold";
import {
  careerStageOptions,
  companySizeOptions,
  departmentOptions,
  employmentStatusOptions,
  industryOptions,
  isEmployedStatus,
  testerWorkValid,
  workingEnvironmentOptions,
} from "@/pages/auth/testerWork";
import {
  dailyAppOptions,
  desktopUserTypeOptions,
  mobileUserTypeOptions,
  mostUsedDeviceOptions,
  ownedDeviceOptions,
  screenTimeOptions,
  testerTechValid,
} from "@/pages/auth/testerTech";
import {
  fitnessOptions,
  hobbyOptions,
  petOptions,
  shoppingFrequencyOptions,
  testerLifestyleValid,
  vehicleOptions,
} from "@/pages/auth/testerLifestyle";
import { bankOptions, paymentMethodOptions, testerFinanceValid } from "@/pages/auth/testerFinance";
import { authRoute, routes } from "@/lib/routes";
import { cn } from "@/lib/utils";

/** All 8 roadmap steps are implemented. */
const STEP_TOTAL = 8;

/**
 * Brand palette. Tailwind scans this file as plain text, so these class
 * strings must stay complete literals — do not assemble them dynamically.
 */
const ACCENT = "#1E3A8A";
const primaryTone = "bg-[#0F172A] text-white hover:bg-[#1E3A8A]";
const disabledTone = "cursor-not-allowed bg-[#E2E8F0] text-[#6B7280]";
const checkboxTone = "size-6 shrink-0 rounded-[7px] border-2 border-[#C4C9D1] bg-white data-[state=checked]:border-[#1E3A8A] data-[state=checked]:bg-[#1E3A8A] data-[state=checked]:text-white [&_svg]:size-4";
const checkboxToneLg = "size-7 shrink-0 rounded-[8px] border-2 border-[#C4C9D1] bg-white data-[state=checked]:border-[#1E3A8A] data-[state=checked]:bg-[#1E3A8A] data-[state=checked]:text-white [&_svg]:size-5";

const copy = {
  stepLabel: (step: number) => words(`${step} / ${STEP_TOTAL}`, `${step} / ${STEP_TOTAL}`),
  title: words("Let's get to know you!", "Apprenons à vous connaître !"),
  subtitle: words("Tell us a bit about yourself", "Parlez-nous un peu de vous"),
  idTitle: words("Complete with ID", "Complétez avec une pièce d’identité"),
  idCta: words("Verify your ID", "Vérifier mon identité"),
  idReady: words("Please have your ID document ready", "Veuillez préparer votre pièce d’identité"),
  idEta: words("Estimated 12h to 24h", "Environ 12 h à 24 h"),
  idUnavailable: words("ID verification isn’t available yet — you can continue with the form below.", "La vérification d’identité n’est pas encore disponible — continuez avec le formulaire ci-dessous."),
  firstName: words("First name", "Prénom"),
  lastName: words("Last name", "Nom"),
  gender: words("Gender", "Genre"),
  male: words("Male", "Homme"),
  female: words("Female", "Femme"),
  dob: words("Date of birth", "Date de naissance"),
  openDob: words("Open date of birth picker", "Ouvrir le sélecteur de date de naissance"),
  dobInvalid: words("Enter a valid date of birth (18+).", "Saisissez une date de naissance valide (18 ans et plus)."),
  nationality: words("Nationality", "Nationalité"),
  residence: words("Country of residency", "Pays de résidence"),
  selectRequired: words("Choose an option to continue.", "Choisissez une option pour continuer."),
  required: words("Required field", "Champ requis"),
  newsletter: words("Subscribe to our awesome newsletter", "S’abonner à notre super infolettre"),
  next: words("Next", "Suivant"),
  incomplete: words("Complete the required fields to continue.", "Complétez les champs obligatoires pour continuer."),
  // Step 2 — contact details
  contactTitle: words("What are your contact details?", "Quelles sont vos coordonnées ?"),
  contactSubtitle: words("We’ll just need your contact info to keep you informed", "Nous avons simplement besoin de vos coordonnées pour vous tenir informé"),
  phone: words("Phone number", "Numéro de téléphone"),
  phoneCountry: words("Country and calling code", "Pays et indicatif téléphonique"),
  phonePlaceholder: words("Phone number", "Numéro de téléphone"),
  phoneInvalid: words("Phone number is not valid", "Le numéro de téléphone n’est pas valide"),
  whatsapp: words("I use WhatsApp on this number", "J’utilise WhatsApp sur ce numéro"),
  back: words("Back", "Retour"),
  // Step 3 — about you
  aboutTitle: words("Share a bit about yourself", "Parlez-nous de vous"),
  aboutSubtitle: words("Tell us a bit about your personal life", "Parlez-nous un peu de votre vie personnelle"),
  relationship: words("Relationship status", "Situation sentimentale"),
  religion: words("Religion", "Religion"),
  education: words("Highest level of education", "Niveau d’études le plus élevé"),
  children: words("Children and dependents", "Enfants et personnes à charge"),
  spokenLanguage: words("Spoken language", "Langues parlées"),
  otherLanguages: words("Other languages", "Autres langues"),
  noDrivingLicense: words("I don’t have a driving license", "Je n’ai pas de permis de conduire"),
  drivingLicense: words("Driving license", "Permis de conduire"),
  noDisability: words("I don’t have any disabilities", "Je n’ai aucun handicap"),
  disability: words("Disability conditions", "Situation de handicap"),
  changeTitle: words("Be part of the change", "Faites partie du mouvement"),
  changeBody: words("Help shape digital products from some of the coolest brands in the MENA region.", "Contribuez à façonner des produits numériques de marques discrètes de la région MENA."),
  // Step 4 — living situation
  householdTitle: words("Tell us about your living situation", "Parlez-nous de votre situation de logement"),
  householdSubtitle: words("Your household info helps us understand you better", "Les informations sur votre foyer nous aident à mieux vous connaître"),
  housingStatus: words("Housing status", "Statut du logement"),
  livingArrangements: words("Living arrangements", "Composition du foyer"),
  householdIncome: words("Monthly household income (USD)", "Revenu mensuel du foyer (USD)"),
  householdSizeLabel: words("How many people live in your household?", "Combien de personnes vivent dans votre foyer ?"),
  decreaseHousehold: words("Decrease number of people", "Diminuer le nombre de personnes"),
  increaseHousehold: words("Increase number of people", "Augmenter le nombre de personnes"),
  householdPeople: words("Number of people in the household", "Nombre de personnes dans le foyer"),
  scoreTitle: words("Keep your tester score high", "Gardez un bon score de testeur"),
  scoreBody: words("Maintaining this high score will ensure you access to more tests.", "Conserver un score élevé vous donne accès à davantage de tests."),
  // Step 5 — professional path
  workTitle: words("Your professional path", "Votre parcours professionnel"),
  workSubtitle: words("We want to know more about your career and goals", "Nous souhaitons en savoir plus sur votre carrière et vos objectifs"),
  employmentStatus: words("Your employment status", "Votre statut d’emploi"),
  industry: words("What industry do you work in?", "Dans quel secteur travaillez-vous ?"),
  department: words("What department do you work in?", "Dans quel service travaillez-vous ?"),
  careerStage: words("Career stage", "Stade de carrière"),
  companySize: words("Company size", "Taille de l’entreprise"),
  workingEnvironment: words("Working environment", "Environnement de travail"),
  // Step 6 — tech habits
  techTitle: words("Your tech habits and preferences", "Vos habitudes et préférences technologiques"),
  techSubtitle: words("Let us know what devices and apps keep you going", "Dites-nous quels appareils et applications vous animent"),
  screenTime: words("Daily screen time", "Temps d’écran quotidien"),
  mostUsedDevice: words("Most used device", "Appareil le plus utilisé"),
  dailyApps: words("Which apps do you rely on every day?", "Sur quelles applications comptez-vous chaque jour ?"),
  mobileUserType: words("Mobile user type", "Profil d’utilisateur mobile"),
  desktopUserType: words("Desktop user type", "Profil d’utilisateur sur ordinateur"),
  ownedDevices: words("Owned devices", "Appareils que vous possédez"),
  // Step 7 — lifestyle
  lifestyleTitle: words("Your day-to-day vibe", "Votre quotidien"),
  lifestyleSubtitle: words("From hobbies to habits, tell us about your rhythm", "Des passions aux habitudes, parlez-nous de votre rythme"),
  petsLabel: words("Pets ownership", "Possession d’animaux"),
  noPets: words("I don’t have pets", "Je n’ai pas d’animaux"),
  petsOwned: words("Pets owned", "Animaux possédés"),
  hobby: words("Hobbies", "Loisirs"),
  fitnessActivities: words("Fitness activities", "Activités physiques"),
  hasVehicle: words("Do you have a vehicle", "Possédez-vous un véhicule ?"),
  yes: words("Yes", "Oui"),
  no: words("No", "Non"),
  shoppingFrequency: words("Frequency of online shopping", "Fréquence des achats en ligne"),
  // Step 8 — finances
  financeTitle: words("How do you manage your finances?", "Comment gérez-vous vos finances ?"),
  financeSubtitle: words("Tell us how you manage your finances and expenses", "Dites-nous comment vous gérez vos finances et vos dépenses"),
  bankingLabel: words("Banking", "Banque"),
  noBankAccount: words("I don’t have a bank account", "Je n’ai pas de compte bancaire"),
  bank: words("What bank do you have?", "Quelle banque utilisez-vous ?"),
  paymentMethods: words("Payment methods used", "Moyens de paiement utilisés"),
  payoutTitle: words("Request a payout when you reach $30", "Demandez un paiement dès 30 $"),
  payoutBody: words("Take between 15/20 short tests to redeem your cash reward.", "Réalisez entre 15/20 tests courts pour débloquer votre récompense en espèces."),
  whyTitle: words("Why it’s important to verify my identity?", "Pourquoi est-il important de vérifier mon identité ?"),
  security: words("Security", "Sécurité"),
  securityBody: words("Verifying your identity helps to prevent fraud and unauthorized access to your account.", "Vérifier votre identité aide à prévenir la fraude et les accès non autorisés à votre compte."),
  access: words("Access to tests", "Accès aux tests"),
  accessBody: words("Some tests might be available only for verified users. Get access to all tests by verifying your identity.", "Certains tests sont réservés aux utilisateurs vérifiés. Accédez à tous les tests en vérifiant votre identité."),
  payouts: words("Payouts", "Paiements"),
  payoutsBody: words("Only verified accounts are eligible to request a payout. If you have not yet verified your identity, please do so before requesting a payout.", "Seuls les comptes vérifiés peuvent demander un paiement. Si votre identité n’est pas encore vérifiée, faites-le avant de demander un paiement."),
  home: words("Home", "Accueil"),
};

/** Right-hand rail for every step except step 1, which uses its own three-part card. */
const stepRail = {
  2: { icon: CircleDollarSign, title: copy.payoutTitle, body: copy.payoutBody, tone: "bg-[#E8EFFB] text-[#1E3A8A]" },
  3: { icon: Flag, title: copy.changeTitle, body: copy.changeBody, tone: "bg-[#E4EBF8] text-[#1E40AF]" },
  4: { icon: Star, title: copy.scoreTitle, body: copy.scoreBody, tone: "bg-[#DFE7F5] text-[#152C5E]" },
  5: { icon: CircleDollarSign, title: copy.payoutTitle, body: copy.payoutBody, tone: "bg-[#E8EFFB] text-[#1E3A8A]" },
  6: { icon: Flag, title: copy.changeTitle, body: copy.changeBody, tone: "bg-[#E4EBF8] text-[#1E40AF]" },
  7: { icon: Star, title: copy.scoreTitle, body: copy.scoreBody, tone: "bg-[#DFE7F5] text-[#152C5E]" },
  8: { icon: CircleDollarSign, title: copy.payoutTitle, body: copy.payoutBody, tone: "bg-[#E8EFFB] text-[#1E3A8A]" },
} as const;

export default function TesterOnboarding() {
  const { language, text } = useAuthLocale();
  const navigate = useNavigate();
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [gender, setGender] = useState("");
  const [dob, setDob] = useState("");
  const [nationality, setNationality] = useState("");
  const [residence, setResidence] = useState("");
  const [newsletter, setNewsletter] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [idNotice, setIdNotice] = useState(false);
  const dobRef = useRef<HTMLInputElement>(null);
  const [step, setStep] = useState(1);
  const [countryIso, setCountryIso] = useState(defaultCountryIso);
  const [phone, setPhone] = useState("");
  const [phoneTouched, setPhoneTouched] = useState(false);
  const [whatsapp, setWhatsapp] = useState(false);
  // Step 3
  const [relationship, setRelationship] = useState("");
  const [religion, setReligion] = useState("");
  const [education, setEducation] = useState("");
  const [children, setChildren] = useState("");
  const [languages, setLanguages] = useState<string[]>([]);
  const [otherLanguage, setOtherLanguage] = useState("");
  const [noDrivingLicense, setNoDrivingLicense] = useState(false);
  const [drivingLicense, setDrivingLicense] = useState("");
  const [noDisability, setNoDisability] = useState(false);
  const [disability, setDisability] = useState("");
  // Step 4
  const [housingStatus, setHousingStatus] = useState("");
  const [livingArrangements, setLivingArrangements] = useState("");
  const [monthlyIncome, setMonthlyIncome] = useState("");
  const [householdSize, setHouseholdSize] = useState(1);
  // Step 5
  const [employmentStatus, setEmploymentStatus] = useState("");
  const [industry, setIndustry] = useState("");
  const [department, setDepartment] = useState("");
  const [careerStage, setCareerStage] = useState("");
  const [companySize, setCompanySize] = useState("");
  const [workingEnvironment, setWorkingEnvironment] = useState("");
  // Step 6
  const [screenTime, setScreenTime] = useState("");
  const [mostUsedDevice, setMostUsedDevice] = useState("");
  const [dailyApps, setDailyApps] = useState<string[]>([]);
  const [mobileUserType, setMobileUserType] = useState("");
  const [desktopUserType, setDesktopUserType] = useState("");
  const [ownedDevices, setOwnedDevices] = useState<string[]>([]);
  // Step 7
  const [noPets, setNoPets] = useState(false);
  const [petsOwned, setPetsOwned] = useState("");
  const [hobby, setHobby] = useState("");
  const [fitness, setFitness] = useState("");
  const [hasVehicle, setHasVehicle] = useState("");
  const [shoppingFrequency, setShoppingFrequency] = useState("");
  // Step 8
  const [noBankAccount, setNoBankAccount] = useState(false);
  const [bank, setBank] = useState("");
  const [paymentMethods, setPaymentMethods] = useState<string[]>([]);

  useEffect(() => { document.title = `${text(copy.title)} | Elseview`; }, [text]);

  const goToStep = (nextStep: number) => {
    setStep(nextStep);
    setSubmitted(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const openDobPicker = () => {
    const input = dobRef.current;
    if (!input) return;
    input.focus();
    if (typeof input.showPicker === "function") {
      try {
        input.showPicker();
        return;
      } catch {
        /* showPicker needs a user gesture and is unsupported in some browsers — focusing is enough there */
      }
    }
    // Fallback for engines without showPicker: the native indicator is hidden by CSS,
    // so nudge the segments directly.
    input.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown" }));
  };

  const countries = useMemo(
    () =>
      countryCallingCodes
        .map((country) => ({ iso: country.iso, name: getCountryName(country, language), callingCode: country.callingCode }))
        .sort((a, b) => a.name.localeCompare(b.name, language)),
    [language],
  );

  const selectedCountry =
    countries.find((country) => country.iso === countryIso)
    ?? countries.find((country) => country.iso === defaultCountryIso)
    ?? countries[0];
  const contactValid = testerContactValid(phone, selectedCountry.callingCode, selectedCountry.iso);
  const showPhoneError = (phoneTouched || submitted) && !contactValid;

  const about = {
    relationship,
    religion,
    education,
    children,
    languages,
    otherLanguage,
    noDrivingLicense,
    drivingLicense,
    noDisability,
    disability,
  };
  const aboutValid = testerAboutValid(about);

  const household = { housingStatus, livingArrangements, monthlyIncome, householdSize };
  const householdValid = testerHouseholdValid(household);

  const work = { employmentStatus, industry, department, careerStage, companySize, workingEnvironment };
  const workValid = testerWorkValid(work);
  const employed = isEmployedStatus(employmentStatus);

  const tech = { screenTime, mostUsedDevice, dailyApps, mobileUserType, desktopUserType, ownedDevices };
  const techValid = testerTechValid(tech);

  const lifestyle = { noPets, petsOwned, hobby, fitness, hasVehicle, shoppingFrequency };
  const lifestyleValid = testerLifestyleValid(lifestyle);

  const finance = { noBankAccount, bank, paymentMethods };
  const financeValid = testerFinanceValid(finance);

  const profile = { firstName, lastName, gender, dob, nationality, residence };
  const valid = testerProfileValid(profile);
  const age = ageOn(dob);
  const showDobError = submitted && (age === null || age < 18 || age > 120);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    setSubmitted(true);
    if (step === 1) {
      if (!testerProfileValid(profile)) {
        const firstInvalid =
          !firstName.trim() ? "tester-first-name"
          : !lastName.trim() ? "tester-last-name"
          : gender !== "male" && gender !== "female" ? "tester-gender-male"
          : age === null || age < 18 || age > 120 ? "tester-dob"
          : !nationality ? "tester-nationality"
          : "tester-residence";
        document.getElementById(firstInvalid)?.focus();
        return;
      }
      goToStep(2);
      return;
    }

    if (step === 2) {
      if (!testerContactValid(phone, selectedCountry.callingCode, selectedCountry.iso)) {
        document.getElementById("tester-phone")?.focus();
        return;
      }
      goToStep(3);
      return;
    }

    if (step === 3) {
      if (!testerAboutValid(about)) {
        document.getElementById(
          !relationship ? "about-relationship"
          : !religion ? "about-religion"
          : !education ? "about-education"
          : !children ? "about-children"
          : languages.length === 0 && !otherLanguage ? "about-language-ar"
          : !noDrivingLicense && !drivingLicense ? "about-driving-license"
          : "about-disability",
        )?.focus();
        return;
      }
      goToStep(4);
      return;
    }

    if (step === 4) {
      if (!testerHouseholdValid(household)) {
        document.getElementById(
          !housingStatus ? "household-housing"
          : !livingArrangements ? "household-arrangements"
          : !monthlyIncome ? "household-income"
          : "household-size",
        )?.focus();
        return;
      }
      goToStep(5);
      return;
    }

    if (step === 5) {
      if (!testerWorkValid(work)) {
        document.getElementById(
          !employmentStatus ? "work-status"
          : employed && !industry ? "work-industry"
          : employed && !department ? "work-department"
          : employed && !careerStage ? "work-career-stage"
          : employed && !companySize ? "work-company-size"
          : "work-environment",
        )?.focus();
        return;
      }
      goToStep(6);
      return;
    }

    if (step === 6) {
      if (!testerTechValid(tech)) {
        document.getElementById(
          !screenTime ? "tech-screen-time"
          : !mostUsedDevice ? "tech-most-used-device"
          : dailyApps.length === 0 ? "tech-app-social"
          : !mobileUserType ? "tech-mobile-type"
          : !desktopUserType ? "tech-desktop-type"
          : "tech-device-android",
        )?.focus();
        return;
      }
      goToStep(7);
      return;
    }

    if (step === 7) {
      if (!testerLifestyleValid(lifestyle)) {
        document.getElementById(
          !noPets && !petsOwned ? "lifestyle-pets"
          : !hobby ? "lifestyle-hobby"
          : !fitness ? "lifestyle-fitness"
          : !hasVehicle ? "lifestyle-vehicle-yes"
          : "lifestyle-shopping",
        )?.focus();
        return;
      }
      goToStep(8);
      return;
    }

    if (!testerFinanceValid(finance)) {
      document.getElementById(
        !noBankAccount && !bank ? "finance-bank"
        : "finance-method-cash",
      )?.focus();
      return;
    }
    try {
      window.localStorage.setItem(
        "elseview.tester.profile",
        JSON.stringify({
          ...profile,
          firstName: firstName.trim(),
          lastName: lastName.trim(),
          newsletter,
          countryIso: selectedCountry.iso,
          callingCode: selectedCountry.callingCode,
          phone: phone.trim(),
          whatsapp,
          about,
          household,
          work,
          tech,
          lifestyle,
          finance,
        }),
      );
    } catch { /* private mode: continue without a saved draft */ }
    navigate(authRoute("login", "tester"));
  };

  const inputClass = "h-14 w-full rounded-xl border border-[#b9bec7] bg-white px-5 text-[16px] text-[#18181b] shadow-none outline-none transition placeholder:text-[#a7abb2] hover:border-[#8f96a1] focus:border-[#18181b] md:text-[16px]";

  return (
    <main className="min-h-dvh bg-white text-[#18181b]">
      <header className="mx-auto flex w-full max-w-[1200px] items-center justify-between gap-4 px-5 py-5 sm:px-8">
        <Link to="/" className="inline-flex min-h-11 items-center gap-2 rounded-md text-sm font-medium text-[#626870] hover:text-[#07172f] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff]">
          {text(copy.home)}
        </Link>
        <LanguageSwitcher />
      </header>

      <section className="mx-auto grid w-full max-w-[1120px] gap-12 px-6 pb-16 pt-2 sm:pt-4 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)] lg:gap-16">
        <div className="lg:col-span-2">
          <Link to="/" aria-label="Elseview home" className="mx-auto mb-2 flex w-fit rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff] focus-visible:ring-offset-4">
            <MediterraLogo />
          </Link>
        </div>
        <div>
          <p className="text-[14px] font-medium text-[#9aa0aa]">{text(copy.stepLabel(step))}</p>
          <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-[#E2E8F0]" role="progressbar" aria-valuenow={step} aria-valuemin={1} aria-valuemax={STEP_TOTAL} aria-label={text(copy.stepLabel(step))}>
            <div className="h-full rounded-full transition-[width] duration-300 motion-reduce:transition-none" style={{ width: `${(step / STEP_TOTAL) * 100}%`, backgroundColor: ACCENT }} />
          </div>

          <h1 className="mt-6 text-[30px] font-bold leading-tight tracking-tight sm:text-[34px]">
            {step === 1 ? text(copy.title) : step === 2 ? text(copy.contactTitle) : step === 3 ? text(copy.aboutTitle) : step === 4 ? text(copy.householdTitle) : step === 5 ? text(copy.workTitle) : step === 6 ? text(copy.techTitle) : step === 7 ? text(copy.lifestyleTitle) : text(copy.financeTitle)}
          </h1>
          <p className="mt-2 text-[17px] text-[#6d6d70]">
            {step === 1 ? text(copy.subtitle) : step === 2 ? text(copy.contactSubtitle) : step === 3 ? text(copy.aboutSubtitle) : step === 4 ? text(copy.householdSubtitle) : step === 5 ? text(copy.workSubtitle) : step === 6 ? text(copy.techSubtitle) : step === 7 ? text(copy.lifestyleSubtitle) : text(copy.financeSubtitle)}
          </p>

          {step === 1 && (
        <div>

          <div className="mt-7 rounded-2xl bg-gradient-to-br from-[#E8EFFB] via-[#D3E0F5] to-[#AFC5EC] p-6 sm:p-7">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <p className="text-[22px] font-bold tracking-tight sm:text-[24px]">{text(copy.idTitle)}</p>
              <button
                type="button"
                onClick={() => setIdNotice(true)}
                className="inline-flex min-h-[52px] items-center gap-2.5 rounded-full bg-[#0F172A] px-6 text-[16px] font-semibold text-white transition hover:bg-[#1E3A8A] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff] focus-visible:ring-offset-2"
              >
                <IdCard className="size-5" strokeWidth={1.8} aria-hidden="true" />
                {text(copy.idCta)}
              </button>
            </div>
            <div className="mt-5 flex flex-wrap items-center justify-between gap-x-6 gap-y-2 text-[14px] font-medium text-[#18181b]">
              <p className="inline-flex items-center gap-2"><IdCard className="size-4 shrink-0" strokeWidth={1.8} aria-hidden="true" />{text(copy.idReady)}</p>
              <p className="inline-flex items-center gap-2"><Clock3 className="size-4 shrink-0" strokeWidth={1.8} aria-hidden="true" />{text(copy.idEta)}</p>
            </div>
            {idNotice && <p role="status" className="mt-4 rounded-xl bg-white/80 px-4 py-3 text-[13.5px] leading-relaxed text-[#0B1E4B]">{text(copy.idUnavailable)}</p>}
          </div>

          <form onSubmit={submit} noValidate className="mt-8 space-y-6">
            <div>
              <label htmlFor="tester-first-name" className="sr-only">{text(copy.firstName)}</label>
              <Input id="tester-first-name" name="firstName" value={firstName} onChange={(event) => setFirstName(event.target.value)} placeholder={text(copy.firstName)} autoComplete="given-name" required maxLength={80} className={inputClass} />
              {submitted && !firstName.trim() && <p role="alert" className="mt-2 text-[14px] text-[#f04438]">{text(copy.required)}</p>}
            </div>
            <div>
              <label htmlFor="tester-last-name" className="sr-only">{text(copy.lastName)}</label>
              <Input id="tester-last-name" name="lastName" value={lastName} onChange={(event) => setLastName(event.target.value)} placeholder={text(copy.lastName)} autoComplete="family-name" required maxLength={80} className={inputClass} />
              {submitted && !lastName.trim() && <p role="alert" className="mt-2 text-[14px] text-[#f04438]">{text(copy.required)}</p>}
            </div>

            <fieldset>
              <legend className="text-[17px] font-semibold">{text(copy.gender)}</legend>
              <div className="mt-3 flex flex-wrap items-center gap-x-10 gap-y-3">
                {[{ value: "male", label: copy.male, id: "tester-gender-male" }, { value: "female", label: copy.female, id: "tester-gender-female" }].map((option) => (
                  <label key={option.value} className="inline-flex min-h-11 cursor-pointer items-center gap-3 text-[16px]">
                    <input id={option.id} type="radio" name="gender" value={option.value} checked={gender === option.value} onChange={() => setGender(option.value)} className="sr-only" />
                    <span aria-hidden="true" className={cn("grid size-7 place-items-center rounded-full border-2 transition", gender === option.value ? "border-[#1E3A8A]" : "border-[#C4C9D1]")}>
                      <span className={cn("size-3 rounded-full", gender === option.value ? "bg-[#1E3A8A]" : "bg-transparent")} />
                    </span>
                    {text(option.label)}
                  </label>
                ))}
              </div>
              {submitted && gender !== "male" && gender !== "female" && <p role="alert" className="mt-2 text-[14px] text-[#f04438]">{text(copy.required)}</p>}
            </fieldset>

            <div>
              <label htmlFor="tester-dob" className="sr-only">{text(copy.dob)}</label>
              <div className="relative">
                <input
                  ref={dobRef}
                  id="tester-dob"
                  name="dob"
                  type="date"
                  value={dob}
                  onChange={(event) => setDob(event.target.value)}
                  required
                  aria-label={text(copy.dob)}
                  max={new Date().toISOString().slice(0, 10)}
                  className={cn(
                    inputClass,
                    "pr-14 [&::-webkit-calendar-picker-indicator]:opacity-0",
                    // Hide the native dd/mm/yyyy segments only while empty so the
                    // custom placeholder does not render on top of them.
                    dob === "" && "[&::-webkit-datetime-edit]:text-transparent",
                  )}
                />
                {dob === "" && <span aria-hidden="true" className="pointer-events-none absolute left-5 top-1/2 -translate-y-1/2 text-[16px] text-[#a7abb2]">{text(copy.dob)}</span>}
                <button
                  type="button"
                  onClick={openDobPicker}
                  aria-label={text(copy.openDob)}
                  className="absolute right-1 top-1/2 grid size-12 -translate-y-1/2 place-items-center rounded-lg text-[#7b7f86] transition hover:bg-[#f6f6f7] hover:text-[#18181b] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff]"
                >
                  <CalendarDays className="size-5" strokeWidth={1.8} aria-hidden="true" />
                </button>
              </div>
              {showDobError && <p role="alert" className="mt-2 text-[14px] text-[#f04438]">{text(copy.dobInvalid)}</p>}
            </div>

            <div className="relative">
              <label htmlFor="tester-nationality" className="sr-only">{text(copy.nationality)}</label>
              <select
                id="tester-nationality"
                value={nationality}
                onChange={(event) => setNationality(event.target.value)}
                required
                className={cn(inputClass, "w-full appearance-none pr-12", nationality === "" && "text-[#a7abb2]")}
              >
                <option value="" disabled>{text(copy.nationality)}</option>
                {countries.map((country) => (<option key={country.iso} value={country.iso} className="text-[#18181b]">{country.name}</option>))}
              </select>
              <ChevronDown className="pointer-events-none absolute right-5 top-1/2 size-5 -translate-y-1/2 text-[#7b7f86]" aria-hidden="true" />
              {submitted && !nationality && <p role="alert" className="mt-2 text-[14px] text-[#f04438]">{text(copy.selectRequired)}</p>}
            </div>

            <div className="relative">
              <label htmlFor="tester-residence" className="sr-only">{text(copy.residence)}</label>
              <select
                id="tester-residence"
                value={residence}
                onChange={(event) => setResidence(event.target.value)}
                required
                className={cn(inputClass, "w-full appearance-none pr-12", residence === "" && "text-[#a7abb2]")}
              >
                <option value="" disabled>{text(copy.residence)}</option>
                {countries.map((country) => (<option key={country.iso} value={country.iso} className="text-[#18181b]">{country.name}</option>))}
              </select>
              <ChevronDown className="pointer-events-none absolute right-5 top-1/2 size-5 -translate-y-1/2 text-[#7b7f86]" aria-hidden="true" />
              {submitted && !residence && <p role="alert" className="mt-2 text-[14px] text-[#f04438]">{text(copy.selectRequired)}</p>}
            </div>

            <label className="flex cursor-pointer items-center gap-4">
              <Checkbox
                checked={newsletter}
                onCheckedChange={(value) => setNewsletter(value === true)}
                aria-label={text(copy.newsletter)}
                className={checkboxToneLg}
              />
              <span className="text-[16px] text-[#18181b]">{text(copy.newsletter)}</span>
            </label>

            {submitted && !valid && <p role="alert" className="text-[14px] text-[#f04438]">{text(copy.incomplete)}</p>}
            <button
              type="submit"
              className={`inline-flex h-14 w-full items-center justify-center gap-2.5 rounded-full text-[17px] font-semibold transition sm:max-w-[360px] ${valid ? primaryTone : "bg-[#E2E8F0] text-[#6B7280]"}`}
            >
              {text(copy.next)}
              <ArrowRight className="size-5 rtl:rotate-180" aria-hidden="true" />
            </button>
          </form>
        </div>
        )}

        {step === 2 && (
        <div>
          <form onSubmit={submit} noValidate className="mt-8 space-y-6">
            <div>
              <div
                className={cn(
                  "relative rounded-xl border bg-white transition-colors has-[:focus-visible]:ring-2",
                  showPhoneError
                    ? "border-[#f04438] has-[:focus-visible]:border-[#f04438] has-[:focus-visible]:ring-[#f04438]/20"
                    : "border-[#b9bec7] has-[:focus-visible]:border-[#18181b] has-[:focus-visible]:ring-[#18181b]/10",
                )}
              >
                <span aria-hidden="true" className="pointer-events-none absolute -top-2.5 left-4 bg-white px-1.5 text-[13px] font-medium text-[#6d6d70]">{text(copy.phone)}</span>
                <div className="flex min-w-0 items-stretch">
                  <div className="relative shrink-0 border-r border-[#e4e4e7]">
                    <label htmlFor="tester-phone-country" className="sr-only">{text(copy.phoneCountry)}</label>
                    {/* Real select stays on top (invisible) so the native picker and
                        keyboard/SR behaviour work; the flag + chevron below are visual only. */}
                    <select
                      id="tester-phone-country"
                      name="phoneCountry"
                      value={selectedCountry.iso}
                      onChange={(event) => { setCountryIso(event.target.value); setPhoneTouched(false); }}
                      className="relative z-10 h-14 w-[76px] cursor-pointer appearance-none bg-transparent opacity-0 outline-none"
                    >
                      {countries.map((country) => (
                        <option key={country.iso} value={country.iso}>
                          {getCountryFlag(country.iso)} (+{country.callingCode}) {country.name}
                        </option>
                      ))}
                    </select>
                    <span aria-hidden="true" className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-[20px] leading-none">{getCountryFlag(selectedCountry.iso)}</span>
                    <ChevronDown className="pointer-events-none absolute right-2 top-1/2 size-4 -translate-y-1/2 text-[#7b7f86]" aria-hidden="true" />
                  </div>

                  <span aria-hidden="true" className="flex items-center pl-4 text-[16px] font-medium text-[#18181b]">+{selectedCountry.callingCode}</span>

                  <div className="flex min-w-0 flex-1 items-center pl-3">
                    <label htmlFor="tester-phone" className="sr-only">{text(copy.phonePlaceholder)}</label>
                    <input
                      id="tester-phone"
                      name="phone"
                      type="tel"
                      inputMode="tel"
                      autoComplete="tel-national"
                      dir="ltr"
                      maxLength={24}
                      value={phone}
                      onChange={(event) => setPhone(sanitizePhoneInput(event.target.value))}
                      onBlur={() => setPhoneTouched(true)}
                      placeholder={text(copy.phonePlaceholder)}
                      aria-invalid={showPhoneError}
                      aria-describedby={showPhoneError ? "tester-phone-error" : undefined}
                      className="h-14 w-full min-w-0 bg-transparent px-2 text-[16px] text-[#18181b] outline-none placeholder:text-[#a7abb2]"
                    />
                  </div>
                </div>
              </div>
              {showPhoneError && <p id="tester-phone-error" role="alert" className="mt-2.5 text-[14px] text-[#f04438]">{text(copy.phoneInvalid)}</p>}
            </div>

            <label className="flex cursor-pointer items-center gap-4">
              <Checkbox
                checked={whatsapp}
                onCheckedChange={(value) => setWhatsapp(value === true)}
                aria-label={text(copy.whatsapp)}
                className={checkboxToneLg}
              />
              <span className="text-[16px] text-[#18181b]">{text(copy.whatsapp)}</span>
            </label>

            <div className="flex items-center justify-between gap-4">
              <button
                type="button"
                onClick={() => goToStep(1)}
                className="inline-flex h-14 items-center justify-center gap-2.5 rounded-full border-[1.5px] border-[#18181b] bg-white px-7 text-[16px] font-semibold text-[#18181b] transition hover:bg-[#f6f6f7] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff] focus-visible:ring-offset-2"
              >
                <ArrowLeft className="size-5 rtl:rotate-180" aria-hidden="true" />
                {text(copy.back)}
              </button>
              <button
                type="submit"
                disabled={!contactValid}
                className={cn(
                  "inline-flex h-14 items-center justify-center gap-2.5 rounded-full px-7 text-[16px] font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff] focus-visible:ring-offset-2",
                  contactValid ? primaryTone : disabledTone,
                )}
              >
                {text(copy.next)}
                <ArrowRight className="size-5 rtl:rotate-180" aria-hidden="true" />
              </button>
            </div>
          </form>
        </div>
        )}

        {step === 3 && (
        <div>
          <form onSubmit={submit} noValidate className="mt-8 space-y-5">
            <AboutSelect id="about-relationship" label={copy.relationship} value={relationship} options={relationshipOptions} onChange={setRelationship} invalid={submitted && !relationship} />            <AboutSelect id="about-religion" label={copy.religion} value={religion} options={religionOptions} onChange={setReligion} invalid={submitted && !religion} />
            <AboutSelect id="about-education" label={copy.education} value={education} options={educationOptions} onChange={setEducation} invalid={submitted && !education} />
            <AboutSelect id="about-children" label={copy.children} value={children} options={childrenOptions} onChange={setChildren} invalid={submitted && !children} />

            <AboutCheckboxes
              legend={copy.spokenLanguage}
              idPrefix="about-language"
              options={languageOptions}
              selected={languages}
              onToggle={(value, checked) => setLanguages((current) => checked ? [...current, value] : current.filter((code) => code !== value))}
            />
            {submitted && languages.length === 0 && !otherLanguage && <p role="alert" className="mt-2 text-[14px] text-[#f04438]">{text(copy.selectRequired)}</p>}
            <div className="mt-4">
              <AboutSelect id="about-other-language" label={copy.otherLanguages} value={otherLanguage} options={otherLanguageOptions} onChange={setOtherLanguage} invalid={false} />
            </div>

            <fieldset>
              <label className="inline-flex min-h-11 cursor-pointer items-center gap-3 text-[16px] text-[#18181b]">
                <Checkbox
                  checked={noDrivingLicense}
                  onCheckedChange={(value) => { const next = value === true; setNoDrivingLicense(next); if (next) setDrivingLicense(""); }}
                  aria-label={text(copy.noDrivingLicense)}
                  className={checkboxTone}
                />
                {text(copy.noDrivingLicense)}
              </label>
              <div className="mt-3">
                <AboutSelect id="about-driving-license" label={copy.drivingLicense} value={drivingLicense} options={drivingLicenseOptions} onChange={setDrivingLicense} disabled={noDrivingLicense} invalid={submitted && !noDrivingLicense && !drivingLicense} />
              </div>
            </fieldset>

            <fieldset>
              <label className="inline-flex min-h-11 cursor-pointer items-center gap-3 text-[16px] text-[#18181b]">
                <Checkbox
                  checked={noDisability}
                  onCheckedChange={(value) => { const next = value === true; setNoDisability(next); if (next) setDisability(""); }}
                  aria-label={text(copy.noDisability)}
                  className={checkboxTone}
                />
                {text(copy.noDisability)}
              </label>
              <div className="mt-3">
                <AboutSelect id="about-disability" label={copy.disability} value={disability} options={disabilityOptions} onChange={setDisability} disabled={noDisability} invalid={submitted && !noDisability && !disability} />
              </div>
            </fieldset>

            {submitted && !aboutValid && <p role="alert" className="text-[14px] text-[#f04438]">{text(copy.incomplete)}</p>}

            <div className="flex items-center justify-between gap-4">
              <button
                type="button"
                onClick={() => goToStep(2)}
                className="inline-flex h-14 items-center justify-center gap-2.5 rounded-full border-[1.5px] border-[#18181b] bg-white px-7 text-[16px] font-semibold text-[#18181b] transition hover:bg-[#f6f6f7] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff] focus-visible:ring-offset-2"
              >
                <ArrowLeft className="size-5 rtl:rotate-180" aria-hidden="true" />
                {text(copy.back)}
              </button>
              <button
                type="submit"
                disabled={!aboutValid}
                className={cn(
                  "inline-flex h-14 items-center justify-center gap-2.5 rounded-full px-7 text-[16px] font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff] focus-visible:ring-offset-2",
                  aboutValid ? primaryTone : disabledTone,
                )}
              >
                {text(copy.next)}
                <ArrowRight className="size-5 rtl:rotate-180" aria-hidden="true" />
              </button>
            </div>
          </form>
        </div>
        )}

        {step === 4 && (
        <div>
          <form onSubmit={submit} noValidate className="mt-8 space-y-5">
            <AboutSelect id="household-housing" label={copy.housingStatus} value={housingStatus} options={housingStatusOptions} onChange={setHousingStatus} invalid={submitted && !housingStatus} />
            <AboutSelect id="household-arrangements" label={copy.livingArrangements} value={livingArrangements} options={livingArrangementsOptions} onChange={setLivingArrangements} invalid={submitted && !livingArrangements} />
            <AboutSelect id="household-income" label={copy.householdIncome} value={monthlyIncome} options={householdIncomeOptions} onChange={setMonthlyIncome} invalid={submitted && !monthlyIncome} />

            <div>
              <label htmlFor="household-size" className="block text-[16px] font-semibold text-[#18181b]">{text(copy.householdSizeLabel)}</label>
              <div className="mt-3 inline-flex h-14 items-stretch overflow-hidden rounded-xl border border-[#d8dade] bg-white">
                <button
                  type="button"
                  onClick={() => setHouseholdSize((value) => clampHouseholdSize(value - 1))}
                  disabled={householdSize <= HOUSEHOLD_MIN}
                  aria-label={text(copy.decreaseHousehold)}
                  className="grid w-14 place-items-center text-[#18181b] transition hover:bg-[#f6f6f7] disabled:cursor-not-allowed disabled:text-[#c9ccd1] disabled:hover:bg-transparent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[#0a84ff]"
                >
                  <Minus className="size-5" strokeWidth={2} aria-hidden="true" />
                </button>
                <input
                  id="household-size"
                  name="householdSize"
                  type="number"
                  inputMode="numeric"
                  min={HOUSEHOLD_MIN}
                  max={HOUSEHOLD_MAX}
                  value={householdSize}
                  onChange={(event) => {
                    const parsed = Number.parseInt(event.target.value, 10);
                    setHouseholdSize(Number.isNaN(parsed) ? HOUSEHOLD_MIN : clampHouseholdSize(parsed));
                  }}
                  aria-label={text(copy.householdPeople)}
                  className="h-full w-16 border-x border-[#e4e4e7] bg-transparent text-center text-[16px] font-semibold text-[#18181b] outline-none [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
                />
                <button
                  type="button"
                  onClick={() => setHouseholdSize((value) => clampHouseholdSize(value + 1))}
                  disabled={householdSize >= HOUSEHOLD_MAX}
                  aria-label={text(copy.increaseHousehold)}
                  className="grid w-14 place-items-center text-[#18181b] transition hover:bg-[#f6f6f7] disabled:cursor-not-allowed disabled:text-[#c9ccd1] disabled:hover:bg-transparent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[#0a84ff]"
                >
                  <Plus className="size-5" strokeWidth={2} aria-hidden="true" />
                </button>
              </div>
            </div>

            {submitted && !householdValid && <p role="alert" className="text-[14px] text-[#f04438]">{text(copy.incomplete)}</p>}

            <div className="flex items-center justify-between gap-4">
              <button
                type="button"
                onClick={() => goToStep(3)}
                className="inline-flex h-14 items-center justify-center gap-2.5 rounded-full border-[1.5px] border-[#18181b] bg-white px-7 text-[16px] font-semibold text-[#18181b] transition hover:bg-[#f6f6f7] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff] focus-visible:ring-offset-2"
              >
                <ArrowLeft className="size-5 rtl:rotate-180" aria-hidden="true" />
                {text(copy.back)}
              </button>
              <button
                type="submit"
                disabled={!householdValid}
                className={cn(
                  "inline-flex h-14 items-center justify-center gap-2.5 rounded-full px-7 text-[16px] font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff] focus-visible:ring-offset-2",
                  householdValid ? primaryTone : disabledTone,
                )}
              >
                {text(copy.next)}
                <ArrowRight className="size-5 rtl:rotate-180" aria-hidden="true" />
              </button>
            </div>
          </form>
        </div>
        )}

        {step === 5 && (
        <div>
          <form onSubmit={submit} noValidate className="mt-8 space-y-5">
            <AboutSelect
              id="work-status"
              label={copy.employmentStatus}
              value={employmentStatus}
              options={employmentStatusOptions}
              onChange={(value) => {
                setEmploymentStatus(value);
                // The job questions are meaningless without current paid work.
                if (!isEmployedStatus(value)) {
                  setIndustry("");
                  setDepartment("");
                  setCareerStage("");
                  setCompanySize("");
                }
              }}
              invalid={submitted && !employmentStatus}
            />
            <AboutSelect id="work-industry" label={copy.industry} value={industry} options={industryOptions} onChange={setIndustry} disabled={!employed} invalid={submitted && employed && !industry} />
            <AboutSelect id="work-department" label={copy.department} value={department} options={departmentOptions} onChange={setDepartment} disabled={!employed} invalid={submitted && employed && !department} />
            <AboutSelect id="work-career-stage" label={copy.careerStage} value={careerStage} options={careerStageOptions} onChange={setCareerStage} disabled={!employed} invalid={submitted && employed && !careerStage} />
            <AboutSelect id="work-company-size" label={copy.companySize} value={companySize} options={companySizeOptions} onChange={setCompanySize} disabled={!employed} invalid={submitted && employed && !companySize} />
            <AboutSelect id="work-environment" label={copy.workingEnvironment} value={workingEnvironment} options={workingEnvironmentOptions} onChange={setWorkingEnvironment} invalid={submitted && !workingEnvironment} />

            {submitted && !workValid && <p role="alert" className="text-[14px] text-[#f04438]">{text(copy.incomplete)}</p>}

            <div className="flex items-center justify-between gap-4">
              <button
                type="button"
                onClick={() => goToStep(4)}
                className="inline-flex h-14 items-center justify-center gap-2.5 rounded-full border-[1.5px] border-[#18181b] bg-white px-7 text-[16px] font-semibold text-[#18181b] transition hover:bg-[#f6f6f7] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff] focus-visible:ring-offset-2"
              >
                <ArrowLeft className="size-5 rtl:rotate-180" aria-hidden="true" />
                {text(copy.back)}
              </button>
              <button
                type="submit"
                disabled={!workValid}
                className={cn(
                  "inline-flex h-14 items-center justify-center gap-2.5 rounded-full px-7 text-[16px] font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff] focus-visible:ring-offset-2",
                  workValid ? primaryTone : disabledTone,
                )}
              >
                {text(copy.next)}
                <ArrowRight className="size-5 rtl:rotate-180" aria-hidden="true" />
              </button>
            </div>
          </form>
        </div>
        )}

        {step === 6 && (
        <div>
          <form onSubmit={submit} noValidate className="mt-8 space-y-5">
            <AboutSelect id="tech-screen-time" label={copy.screenTime} value={screenTime} options={screenTimeOptions} onChange={setScreenTime} invalid={submitted && !screenTime} />
            <AboutSelect id="tech-most-used-device" label={copy.mostUsedDevice} value={mostUsedDevice} options={mostUsedDeviceOptions} onChange={setMostUsedDevice} invalid={submitted && !mostUsedDevice} />

            <div>
              <AboutCheckboxes
                legend={copy.dailyApps}
                idPrefix="tech-app"
                options={dailyAppOptions}
                selected={dailyApps}
                onToggle={(value, checked) => setDailyApps((current) => checked ? [...current, value] : current.filter((code) => code !== value))}
              />
              {submitted && dailyApps.length === 0 && <p role="alert" className="mt-2 text-[14px] text-[#f04438]">{text(copy.selectRequired)}</p>}
            </div>

            <AboutSelect id="tech-mobile-type" label={copy.mobileUserType} value={mobileUserType} options={mobileUserTypeOptions} onChange={setMobileUserType} invalid={submitted && !mobileUserType} />
            <AboutSelect id="tech-desktop-type" label={copy.desktopUserType} value={desktopUserType} options={desktopUserTypeOptions} onChange={setDesktopUserType} invalid={submitted && !desktopUserType} />

            <div>
              <AboutCheckboxes
                legend={copy.ownedDevices}
                idPrefix="tech-device"
                options={ownedDeviceOptions}
                selected={ownedDevices}
                onToggle={(value, checked) => setOwnedDevices((current) => checked ? [...current, value] : current.filter((code) => code !== value))}
              />
              {submitted && ownedDevices.length === 0 && <p role="alert" className="mt-2 text-[14px] text-[#f04438]">{text(copy.selectRequired)}</p>}
            </div>

            {submitted && !techValid && <p role="alert" className="text-[14px] text-[#f04438]">{text(copy.incomplete)}</p>}

            <div className="flex items-center justify-between gap-4">
              <button
                type="button"
                onClick={() => goToStep(5)}
                className="inline-flex h-14 items-center justify-center gap-2.5 rounded-full border-[1.5px] border-[#18181b] bg-white px-7 text-[16px] font-semibold text-[#18181b] transition hover:bg-[#f6f6f7] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff] focus-visible:ring-offset-2"
              >
                <ArrowLeft className="size-5 rtl:rotate-180" aria-hidden="true" />
                {text(copy.back)}
              </button>
              <button
                type="submit"
                disabled={!techValid}
                className={cn(
                  "inline-flex h-14 items-center justify-center gap-2.5 rounded-full px-7 text-[16px] font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff] focus-visible:ring-offset-2",
                  techValid ? primaryTone : disabledTone,
                )}
              >
                {text(copy.next)}
                <ArrowRight className="size-5 rtl:rotate-180" aria-hidden="true" />
              </button>
            </div>
          </form>
        </div>
        )}

        {step === 7 && (
        <div>
          <form onSubmit={submit} noValidate className="mt-8 space-y-5">
            <fieldset>
              <legend className="text-[16px] font-semibold text-[#18181b]">{text(copy.petsLabel)}</legend>
              <label className="mt-2 inline-flex min-h-11 cursor-pointer items-center gap-3 text-[16px] text-[#18181b]">
                <Checkbox
                  id="lifestyle-no-pets"
                  checked={noPets}
                  onCheckedChange={(value) => { const next = value === true; setNoPets(next); if (next) setPetsOwned(""); }}
                  className={checkboxTone}
                />
                {text(copy.noPets)}
              </label>
              <div className="mt-3">
                <AboutSelect id="lifestyle-pets" label={copy.petsOwned} value={petsOwned} options={petOptions} onChange={setPetsOwned} disabled={noPets} invalid={submitted && !noPets && !petsOwned} />
              </div>
            </fieldset>

            <AboutSelect id="lifestyle-hobby" label={copy.hobby} value={hobby} options={hobbyOptions} onChange={setHobby} invalid={submitted && !hobby} />
            <AboutSelect id="lifestyle-fitness" label={copy.fitnessActivities} value={fitness} options={fitnessOptions} onChange={setFitness} invalid={submitted && !fitness} />

            <fieldset>
              <legend className="text-[16px] font-semibold text-[#18181b]">{text(copy.hasVehicle)}</legend>
              <div className="mt-2 flex flex-wrap items-center gap-x-10 gap-y-3">
                {vehicleOptions.map((option) => {
                  const checked = hasVehicle === option.value;
                  return (
                    <label key={option.value} className="inline-flex min-h-11 cursor-pointer items-center gap-3 text-[16px] text-[#18181b]">
                      <input
                        id={`lifestyle-vehicle-${option.value}`}
                        type="radio"
                        name="hasVehicle"
                        value={option.value}
                        checked={checked}
                        onChange={() => setHasVehicle(option.value)}
                        className="sr-only"
                      />
                      <span aria-hidden="true" className={cn("grid size-7 place-items-center rounded-full border-2 transition", checked ? "border-[#1E3A8A]" : "border-[#C4C9D1]")}>
                        <span className={cn("size-3 rounded-full transition", checked ? "bg-[#1E3A8A]" : "bg-transparent")} />
                      </span>
                      {text(option.label)}
                    </label>
                  );
                })}
              </div>
              {submitted && !hasVehicle && <p role="alert" className="mt-2 text-[14px] text-[#f04438]">{text(copy.selectRequired)}</p>}
            </fieldset>

            <AboutSelect id="lifestyle-shopping" label={copy.shoppingFrequency} value={shoppingFrequency} options={shoppingFrequencyOptions} onChange={setShoppingFrequency} invalid={submitted && !shoppingFrequency} />

            {submitted && !lifestyleValid && <p role="alert" className="text-[14px] text-[#f04438]">{text(copy.incomplete)}</p>}

            <div className="flex items-center justify-between gap-4">
              <button
                type="button"
                onClick={() => goToStep(6)}
                className="inline-flex h-14 items-center justify-center gap-2.5 rounded-full border-[1.5px] border-[#18181b] bg-white px-7 text-[16px] font-semibold text-[#18181b] transition hover:bg-[#f6f6f7] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff] focus-visible:ring-offset-2"
              >
                <ArrowLeft className="size-5 rtl:rotate-180" aria-hidden="true" />
                {text(copy.back)}
              </button>
              <button
                type="submit"
                disabled={!lifestyleValid}
                className={cn(
                  "inline-flex h-14 items-center justify-center gap-2.5 rounded-full px-7 text-[16px] font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff] focus-visible:ring-offset-2",
                  lifestyleValid ? primaryTone : disabledTone,
                )}
              >
                {text(copy.next)}
                <ArrowRight className="size-5 rtl:rotate-180" aria-hidden="true" />
              </button>
            </div>
          </form>
        </div>
        )}

        {step === 8 && (
        <div>
          <form onSubmit={submit} noValidate className="mt-8 space-y-5">
            <fieldset>
              <legend className="text-[16px] font-semibold text-[#18181b]">{text(copy.bankingLabel)}</legend>
              <label className="mt-2 inline-flex min-h-11 cursor-pointer items-center gap-3 text-[16px] text-[#18181b]">
                <Checkbox
                  id="finance-no-bank"
                  checked={noBankAccount}
                  onCheckedChange={(value) => { const next = value === true; setNoBankAccount(next); if (next) setBank(""); }}
                  className={checkboxTone}
                />
                {text(copy.noBankAccount)}
              </label>
              <div className="mt-3">
                <AboutSelect id="finance-bank" label={copy.bank} value={bank} options={bankOptions} onChange={setBank} disabled={noBankAccount} invalid={submitted && !noBankAccount && !bank} />
              </div>
            </fieldset>

            <div>
              <AboutCheckboxes
                legend={copy.paymentMethods}
                idPrefix="finance-method"
                options={paymentMethodOptions}
                selected={paymentMethods}
                onToggle={(value, checked) => setPaymentMethods((current) => checked ? [...current, value] : current.filter((code) => code !== value))}
              />
              {submitted && paymentMethods.length === 0 && <p role="alert" className="mt-2 text-[14px] text-[#f04438]">{text(copy.selectRequired)}</p>}
            </div>

            {submitted && !financeValid && <p role="alert" className="text-[14px] text-[#f04438]">{text(copy.incomplete)}</p>}

            <div className="flex items-center justify-between gap-4">
              <button
                type="button"
                onClick={() => goToStep(7)}
                className="inline-flex h-14 items-center justify-center gap-2.5 rounded-full border-[1.5px] border-[#18181b] bg-white px-7 text-[16px] font-semibold text-[#18181b] transition hover:bg-[#f6f6f7] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff] focus-visible:ring-offset-2"
              >
                <ArrowLeft className="size-5 rtl:rotate-180" aria-hidden="true" />
                {text(copy.back)}
              </button>
              <button
                type="submit"
                disabled={!financeValid}
                className={cn(
                  "inline-flex h-14 items-center justify-center gap-2.5 rounded-full px-7 text-[16px] font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff] focus-visible:ring-offset-2",
                  financeValid ? primaryTone : disabledTone,
                )}
              >
                {text(copy.next)}
                <ArrowRight className="size-5 rtl:rotate-180" aria-hidden="true" />
              </button>
            </div>
          </form>
        </div>
        )}
        </div>

        {step === 1 ? (
        <aside aria-label={text(copy.whyTitle)} className="h-fit rounded-[24px] border border-[#e8e8ec] bg-white p-8 sm:p-9 lg:sticky lg:top-8">
          <h2 className="text-[22px] font-bold leading-snug tracking-tight sm:text-[24px]">{text(copy.whyTitle)}</h2>
          <div className="mt-8 space-y-8">
            <section>
              <h3 className="flex items-center gap-2.5 text-[18px] font-bold"><ShieldCheck className="size-6 shrink-0" strokeWidth={1.8} aria-hidden="true" />{text(copy.security)}</h3>
              <p className="mt-2.5 text-[15.5px] leading-relaxed text-[#6d6d70]">{text(copy.securityBody)}</p>
            </section>
            <section>
              <h3 className="flex items-center gap-2.5 text-[18px] font-bold"><KeyRound className="size-6 shrink-0" strokeWidth={1.8} aria-hidden="true" />{text(copy.access)}</h3>
              <p className="mt-2.5 text-[15.5px] leading-relaxed text-[#6d6d70]">{text(copy.accessBody)}</p>
            </section>
            <section>
              <h3 className="flex items-center gap-2.5 text-[18px] font-bold"><CircleDollarSign className="size-6 shrink-0" strokeWidth={1.8} aria-hidden="true" />{text(copy.payouts)}</h3>
              <p className="mt-2.5 text-[15.5px] leading-relaxed text-[#6d6d70]">{text(copy.payoutsBody)}</p>
            </section>
          </div>
        </aside>
        ) : (
        <RailCard {...stepRail[step as 2 | 3 | 4 | 5 | 6 | 7 | 8]} />
        )}
      </section>
    </main>
  );
}

function sanitizePhoneInput(value: string) {
  const trimmedValue = value.trimStart();
  const prefix = trimmedValue.startsWith("+") ? "+" : "";
  return `${prefix}${trimmedValue.slice(prefix.length).replace(/[^\d\s().-]/g, "")}`;
}

const aboutSelectClass = "h-14 w-full rounded-xl border border-[#b9bec7] bg-white px-5 text-[16px] text-[#18181b] shadow-none outline-none transition hover:border-[#8f96a1] focus:border-[#18181b] disabled:cursor-not-allowed disabled:bg-[#f6f6f7] disabled:text-[#a7abb2] disabled:hover:border-[#b9bec7]";

function AboutCheckboxes({
  legend,
  idPrefix,
  options,
  selected,
  onToggle,
}: {
  legend: ReturnType<typeof words>;
  idPrefix: string;
  options: AboutOption[];
  selected: string[];
  onToggle: (value: string, checked: boolean) => void;
}) {
  const { text } = useAuthLocale();
  return (
    <fieldset>
      <legend className="text-[16px] font-semibold text-[#18181b]">{text(legend)}</legend>
      <div className="mt-3 flex flex-wrap items-center gap-x-7 gap-y-2.5">
        {options.map((option) => {
          const checked = selected.includes(option.value);
          return (
            <label key={option.value} className="inline-flex min-h-11 cursor-pointer items-center gap-2.5 text-[16px] text-[#18181b]">
              <Checkbox
                id={`${idPrefix}-${option.value}`}
                checked={checked}
                onCheckedChange={(value) => onToggle(option.value, value === true)}
                className={checkboxTone}
              />
              {text(option.label)}
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}

function RailCard({
  icon: Icon,
  title,
  body,
  tone,
}: {
  icon: typeof CircleDollarSign;
  title: ReturnType<typeof words>;
  body: ReturnType<typeof words>;
  tone: string;
}) {
  const { text } = useAuthLocale();
  return (
    <aside aria-label={text(title)} className="h-fit rounded-[24px] border border-[#e8e8ec] bg-white p-8 sm:p-9 lg:sticky lg:top-8">
      <span className={cn("grid size-14 place-items-center rounded-full", tone)}>
        <Icon className="size-7" strokeWidth={1.8} aria-hidden="true" />
      </span>
      <h2 className="mt-6 text-[20px] font-bold leading-snug tracking-tight sm:text-[22px]">{text(title)}</h2>
      <p className="mt-3 text-[15.5px] leading-relaxed text-[#6d6d70]">{text(body)}</p>
    </aside>
  );
}

function AboutSelect({
  id,
  label,
  value,
  options,
  onChange,
  invalid = false,
  disabled = false,
}: {
  id: string;
  label: ReturnType<typeof words>;
  value: string;
  options: AboutOption[];
  onChange: (value: string) => void;
  invalid?: boolean;
  disabled?: boolean;
}) {
  const { text } = useAuthLocale();
  return (
    <div>
      <label htmlFor={id} className="sr-only">{text(label)}</label>
      <div className="relative">
        <select
          id={id}
          name={id}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          required={!disabled}
          disabled={disabled}
          aria-invalid={invalid}
          className={cn(aboutSelectClass, "w-full appearance-none pr-12", value === "" && !disabled && "text-[#a7abb2]")}
        >
          <option value="" disabled>{text(label)}</option>
          {options.map((option) => (
            <option key={option.value} value={option.value} className="text-[#18181b]">{text(option.label)}</option>
          ))}
        </select>
        <ChevronDown className="pointer-events-none absolute right-5 top-1/2 size-5 -translate-y-1/2 text-[#7b7f86]" aria-hidden="true" />
      </div>
      {invalid && <p role="alert" className="mt-2 text-[14px] text-[#f04438]">{text(copy.selectRequired)}</p>}
    </div>
  );
}
