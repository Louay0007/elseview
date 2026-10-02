import { authWords as words } from "@/lib/auth";
import type { AboutOption } from "./testerAbout";

const preferNot = (): AboutOption => ({ value: "prefer-not", label: words("Prefer not to say", "Je préfère ne pas répondre") });

/** Household size is a bounded stepper rather than a free-text field. */
export const HOUSEHOLD_MIN = 1;
export const HOUSEHOLD_MAX = 20;

export const housingStatusOptions: AboutOption[] = [
  { value: "own-outright", label: words("I own my home outright", "Je suis propriétaire sans prêt") },
  { value: "own-mortgage", label: words("I own my home with a mortgage", "Je suis propriétaire avec un prêt en cours") },
  { value: "rent-private", label: words("I rent from a private landlord", "Je loue chez un bailleur privé") },
  { value: "rent-social", label: words("I rent social or subsidised housing", "Je loue un logement social ou subventionné") },
  { value: "rent-employer", label: words("My employer provides my housing", "Mon employeur me fournit le logement") },
  { value: "rent-shared", label: words("I rent a room in a shared flat", "Je loue une chambre en colocation") },
  { value: "with-family", label: words("I live with family or relatives", "Je vis avec ma famille ou des proches") },
  { value: "with-friends", label: words("I live with friends or other adults", "Je vis avec des amis ou d’autres adultes") },
  { value: "student", label: words("I live in student or campus housing", "Je vis en résidence étudiante ou sur le campus") },
  { value: "temporary", label: words("I live in temporary or seasonal housing", "Je loge temporairement ou saisonnièrement") },
  { value: "shelter", label: words("I live in a shelter or transitional home", "Je suis en hébergement d’urgence ou de transition") },
  { value: "employer-rent", label: words("I rent a property for business or staff", "Je loue un local pour mon activité ou mes équipes") },
  preferNot(),
];

export const livingArrangementsOptions: AboutOption[] = [
  { value: "alone", label: words("I live alone", "Je vis seul·e") },
  { value: "partner", label: words("I live with a partner", "Je vis avec mon·e partenaire") },
  { value: "partner-children", label: words("I live with a partner and children", "Je vis avec mon·e partenaire et mes enfants") },
  { value: "children-only", label: words("I live with my children only", "Je vis avec mes enfants uniquement") },
  { value: "family", label: words("I live with other family members", "Je vis avec d’autres membres de ma famille") },
  { value: "multigenerational", label: words("I live in a multigenerational household", "Je vis dans un foyer multigénérationnel") },
  { value: "friends", label: words("I live with friends in a shared flat", "Je vis en colocation avec des amis") },
  { value: "roommates", label: words("I live with roommates", "Je vis avec des colocataires") },
  { value: "student", label: words("I live in a student residence", "Je vis en résidence étudiante") },
  { value: "caregiver", label: words("I live with someone I care for", "Je vis avec une personne dont je m’occupe") },
  preferNot(),
];

export const householdIncomeOptions: AboutOption[] = [
  { value: "under-500", label: words("Under $500", "Moins de 500 $") },
  { value: "500-1000", label: words("$500 – $1,000", "500 – 1 000 $") },
  { value: "1000-2000", label: words("$1,000 – $2,000", "1 000 – 2 000 $") },
  { value: "2000-3000", label: words("$2,000 – $3,000", "2 000 – 3 000 $") },
  { value: "3000-5000", label: words("$3,000 – $5,000", "3 000 – 5 000 $") },
  { value: "5000-7500", label: words("$5,000 – $7,500", "5 000 – 7 500 $") },
  { value: "7500-10000", label: words("$7,500 – $10,000", "7 500 – 10 000 $") },
  { value: "10000-15000", label: words("$10,000 – $15,000", "10 000 – 15 000 $") },
  { value: "15000-plus", label: words("Over $15,000", "Plus de 15 000 $") },
  { value: "no-income", label: words("No household income", "Aucun revenu du foyer") },
  preferNot(),
];

export type TesterHouseholdDraft = {
  housingStatus: string;
  livingArrangements: string;
  monthlyIncome: string;
  householdSize: number;
};

function isKnown(options: AboutOption[], value: string) {
  return options.some((entry) => entry.value === value);
}

export function clampHouseholdSize(value: number) {
  if (!Number.isFinite(value)) return HOUSEHOLD_MIN;
  return Math.min(HOUSEHOLD_MAX, Math.max(HOUSEHOLD_MIN, Math.round(value)));
}

export function testerHouseholdValid(household: TesterHouseholdDraft): boolean {
  if (!isKnown(housingStatusOptions, household.housingStatus)) return false;
  if (!isKnown(livingArrangementsOptions, household.livingArrangements)) return false;
  if (!isKnown(householdIncomeOptions, household.monthlyIncome)) return false;
  return Number.isInteger(household.householdSize) && household.householdSize >= HOUSEHOLD_MIN && household.householdSize <= HOUSEHOLD_MAX;
}
