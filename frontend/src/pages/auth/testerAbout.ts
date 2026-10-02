import { authWords as words } from "@/lib/auth";

export type AboutOption = { value: string; label: ReturnType<typeof words> };

const preferNot = (): AboutOption => ({ value: "prefer-not", label: words("Prefer not to say", "Je préfère ne pas répondre") });

export const relationshipOptions: AboutOption[] = [
  { value: "single", label: words("Single", "Célibataire") },
  { value: "dating", label: words("In a relationship", "En couple") },
  { value: "engaged", label: words("Engaged", "Fiancé·e") },
  { value: "married", label: words("Married", "Marié·e") },
  { value: "partnership", label: words("Domestic partnership", "Union de fait") },
  { value: "civil-union", label: words("Civil union / partnership", "Pacs") },
  { value: "divorced", label: words("Divorced", "Divorcé·e") },
  { value: "separated", label: words("Separated", "Séparé·e") },
  { value: "widowed", label: words("Widowed", "Veuf·ve") },
  preferNot(),
];

export const religionOptions: AboutOption[] = [
  { value: "islam", label: words("Islam", "Islam") },
  { value: "christianity", label: words("Christianity", "Christianisme") },
  { value: "judaism", label: words("Judaism", "Judaïsme") },
  { value: "hinduism", label: words("Hinduism", "Hindouisme") },
  { value: "buddhism", label: words("Buddhism", "Bouddhisme") },
  { value: "sikhism", label: words("Sikhism", "Sikhisme") },
  { value: "atheism", label: words("Atheism", "Athéisme") },
  { value: "agnosticism", label: words("Agnosticism", "Agnosticisme") },
  { value: "other", label: words("Another religion or belief", "Autre religion ou croyance") },
  preferNot(),
];

export const educationOptions: AboutOption[] = [
  { value: "none", label: words("No formal schooling", "Aucune scolarité formelle") },
  { value: "primary", label: words("Primary school", "École primaire") },
  { value: "lower-secondary", label: words("Lower secondary", "Collège") },
  { value: "upper-secondary", label: words("Upper secondary (high school)", "Lycée") },
  { value: "vocational", label: words("Vocational training or technical diploma", "Formation professionnelle ou diplôme technique") },
  { value: "some-college", label: words("Some college, no degree", "Quelques années d’études, sans diplôme") },
  { value: "bachelor", label: words("Bachelor’s degree", "Licence / baccalauréat") },
  { value: "master", label: words("Master’s degree", "Master") },
  { value: "doctorate", label: words("Doctorate (PhD)", "Doctorat") },
  preferNot(),
];

export const childrenOptions: AboutOption[] = [
  { value: "none", label: words("No children", "Aucun enfant") },
  { value: "1", label: words("1 child", "1 enfant") },
  { value: "2", label: words("2 children", "2 enfants") },
  { value: "3", label: words("3 children", "3 enfants") },
  { value: "4", label: words("4 children", "4 enfants") },
  { value: "5-plus", label: words("5 or more children", "5 enfants ou plus") },
  { value: "dependents", label: words("I care for dependents", "J’ai des personnes à charge") },
  preferNot(),
];

export const languageOptions: AboutOption[] = [
  { value: "ar", label: words("Arabic", "Arabe") },
  { value: "en", label: words("English", "Anglais") },
  { value: "fr", label: words("French", "Français") },
  { value: "es", label: words("Spanish", "Espagnol") },
  { value: "de", label: words("German", "Allemand") },
  { value: "it", label: words("Italian", "Italien") },
  { value: "pt", label: words("Portuguese", "Portugais") },
  { value: "tr", label: words("Turkish", "Turc") },
  { value: "ber", label: words("Tamazight (Berber)", "Tamazight (berbère)") },
  { value: "fa", label: words("Persian", "Persan") },
  { value: "ur", label: words("Urdu", "Ourdou") },
  { value: "hi", label: words("Hindi", "Hindi") },
  { value: "zh", label: words("Mandarin", "Mandarin") },
  { value: "ru", label: words("Russian", "Russe") },
];

export const otherLanguageOptions: AboutOption[] = [
  { value: "amharic", label: words("Amharic", "Amharique") },
  { value: "hausa", label: words("Hausa", "Haussa") },
  { value: "yoruba", label: words("Yoruba", "Yoruba") },
  { value: "igbo", label: words("Igbo", "Igbo") },
  { value: "swahili", label: words("Swahili", "Swahili") },
  { value: "zulu", label: words("Zulu", "Zulu") },
  { value: "somali", label: words("Somali", "Somali") },
  { value: "kurdish", label: words("Kurdish", "Kurde") },
  { value: "polish", label: words("Polish", "Polonais") },
  { value: "dutch", label: words("Dutch", "Néerlandais") },
  { value: "greek", label: words("Greek", "Grec") },
  { value: "japanese", label: words("Japanese", "Japonais") },
  { value: "korean", label: words("Korean", "Coréen") },
  { value: "other", label: words("Another language", "Une autre langue") },
];

export const drivingLicenseOptions: AboutOption[] = [
  { value: "manual", label: words("Manual transmission", "Boîte manuelle") },
  { value: "automatic", label: words("Automatic transmission", "Boîte automatique") },
  { value: "both", label: words("Manual and automatic", "Manuelle et automatique") },
  { value: "motorcycle", label: words("Motorcycle licence", "Permis moto") },
  { value: "light-vehicle", label: words("Light vehicle", "Véhicule léger") },
  { value: "heavy-vehicle", label: words("Heavy vehicle or truck", "Poids lourd ou camion") },
  { value: "professional", label: words("Professional or commercial licence", "Permis professionnel ou commercial") },
  { value: "provisional", label: words("Learner or provisional licence", "Permis provisoire ou learner") },
  { value: "international", label: words("International driving permit", "Permis de conduire international") },
];

export const disabilityOptions: AboutOption[] = [
  { value: "visual", label: words("Visual impairment or blindness", "Déficience visuelle ou cécité") },
  { value: "hearing", label: words("Hearing impairment or deafness", "Déficience auditive ou surdité") },
  { value: "mobility", label: words("Mobility or physical impairment", "Déficience motrice ou physique") },
  { value: "speech", label: words("Speech or language impairment", "Déficience de la parole ou du langage") },
  { value: "learning", label: words("Cognitive or learning disability", "Déficience cognitive ou troubles d’apprentissage") },
  { value: "neurological", label: words("Neurological condition", "Affection neurologique") },
  { value: "mental-health", label: words("Mental health condition", "Santé mentale") },
  { value: "chronic", label: words("Chronic illness or long-term condition", "Maladie chronique ou affection de longue durée") },
  { value: "other", label: words("Another disability", "Une autre situation de handicap") },
];

export type TesterAboutDraft = {
  relationship: string;
  religion: string;
  education: string;
  children: string;
  languages: string[];
  otherLanguage: string;
  noDrivingLicense: boolean;
  drivingLicense: string;
  noDisability: boolean;
  disability: string;
};

function isKnown(option: AboutOption[], value: string) {
  return option.some((entry) => entry.value === value);
}

export function testerAboutValid(about: TesterAboutDraft): boolean {
  if (!isKnown(relationshipOptions, about.relationship)) return false;
  if (!isKnown(religionOptions, about.religion)) return false;
  if (!isKnown(educationOptions, about.education)) return false;
  if (!isKnown(childrenOptions, about.children)) return false;

  // At least one language, either a ticked box or the “other” dropdown.
  const hasLanguage =
    about.languages.some((code) => isKnown(languageOptions, code)) || isKnown(otherLanguageOptions, about.otherLanguage);
  if (!hasLanguage) return false;

  // The dependent selects are only required when “I don’t have…” is unticked.
  if (!about.noDrivingLicense && !isKnown(drivingLicenseOptions, about.drivingLicense)) return false;
  if (!about.noDisability && !isKnown(disabilityOptions, about.disability)) return false;

  return true;
}
