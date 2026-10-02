import { authWords as words } from "@/lib/auth";
import type { AboutOption } from "./testerAbout";

const preferNot = (): AboutOption => ({ value: "prefer-not", label: words("Prefer not to say", "Je préfère ne pas répondre") });

export const employmentStatusOptions: AboutOption[] = [
  { value: "employed-full-time", label: words("Employed full-time", "CDI à temps plein") },
  { value: "employed-part-time", label: words("Employed part-time", "Temps partiel") },
  { value: "self-employed", label: words("Self-employed", "Indépendant·e") },
  { value: "freelancer", label: words("Freelancer or contractor", "Freelance ou prestataire") },
  { value: "business-owner", label: words("Business owner", "Chef·fe d’entreprise") },
  { value: "student", label: words("Student", "Étudiant·e") },
  { value: "recent-graduate", label: words("Recently graduated, looking for work", "Diplômé·e récemment, en recherche d’emploi") },
  { value: "unemployed-looking", label: words("Unemployed and looking for work", "Sans emploi, en recherche de travail") },
  { value: "unemployed-not-looking", label: words("Unemployed and not looking for work", "Sans emploi et sans recherche") },
  { value: "retired", label: words("Retired", "Retraité·e") },
  { value: "homemaker", label: words("Homemaker or stay-at-home parent", "Parent au foyer / personne au foyer") },
  { value: "unable-to-work", label: words("Unable to work", "Dans l’impossibilité de travailler") },
  { value: "caregiver-full-time", label: words("Full-time caregiver", "Personne aidante à temps plein") },
  preferNot(),
];

/**
 * The job-specific questions (industry, department, career stage, company size)
 * only make sense for statuses that involve current paid work.
 */
const EMPLOYED_STATUSES = new Set(["employed-full-time", "employed-part-time", "self-employed", "freelancer", "business-owner"]);

export function isEmployedStatus(status: string) {
  return EMPLOYED_STATUSES.has(status);
}

export const industryOptions: AboutOption[] = [
  { value: "advertising", label: words("Advertising & marketing", "Publicité & marketing") },
  { value: "agriculture", label: words("Agriculture, forestry & fishing", "Agriculture, sylviculture & pêche") },
  { value: "automotive", label: words("Automotive", "Automobile") },
  { value: "banking", label: words("Banking & financial services", "Banque & services financiers") },
  { value: "biotech", label: words("Biotech & pharmaceuticals", "Biotechnologie & pharmacie") },
  { value: "construction", label: words("Construction & real estate", "Construction & immobilier") },
  { value: "consulting", label: words("Consulting & professional services", "Conseil & services professionnels") },
  { value: "consumer-goods", label: words("Consumer goods & retail", "Grande consommation & distribution") },
  { value: "education", label: words("Education & training", "Éducation & formation") },
  { value: "energy", label: words("Energy & utilities", "Énergie & services aux collectivités") },
  { value: "entertainment", label: words("Entertainment & media", "Divertissement & médias") },
  { value: "fashion", label: words("Fashion & textiles", "Mode & textile") },
  { value: "food-beverage", label: words("Food & beverage", "Alimentation & boissons") },
  { value: "government", label: words("Government & public sector", "Secteur public & administration") },
  { value: "healthcare", label: words("Healthcare", "Santé") },
  { value: "hospitality", label: words("Hospitality & travel", "Hôtellerie & voyage") },
  { value: "insurance", label: words("Insurance", "Assurance") },
  { value: "hr-recruitment", label: words("Human resources & recruitment", "Ressources humaines & recrutement") },
  { value: "it-software", label: words("IT & software", "Informatique & logiciels") },
  { value: "legal", label: words("Legal services", "Services juridiques") },
  { value: "logistics", label: words("Logistics & transportation", "Logistique & transport") },
  { value: "manufacturing", label: words("Manufacturing", "Industrie & fabrication") },
  { value: "mining", label: words("Mining & natural resources", "Mines & ressources naturelles") },
  { value: "nonprofit", label: words("Nonprofit & NGO", "Association & ONG") },
  { value: "religion", label: words("Religion & faith", "Religion et foi") },
  { value: "research", label: words("Research & development", "Recherche & développement") },
  { value: "telecom", label: words("Telecommunications", "Télécommunications") },
  { value: "tourism", label: words("Tourism", "Tourisme") },
  { value: "other", label: words("Another industry", "Un autre secteur") },
  preferNot(),
];

export const departmentOptions: AboutOption[] = [
  { value: "administration", label: words("Administration", "Administration") },
  { value: "business-development", label: words("Business development", "Développement d’affaires") },
  { value: "customer-service", label: words("Customer service & support", "Service client & assistance") },
  { value: "design", label: words("Design & creative", "Design & création") },
  { value: "engineering", label: words("Engineering & product", "Ingénierie & produit") },
  { value: "finance", label: words("Finance & accounting", "Finance & comptabilité") },
  { value: "hr", label: words("Human resources", "Ressources humaines") },
  { value: "it", label: words("Information technology", "Informatique") },
  { value: "legal-compliance", label: words("Legal & compliance", "Juridique & conformité") },
  { value: "marketing", label: words("Marketing & communications", "Marketing & communication") },
  { value: "operations", label: words("Operations & logistics", "Opérations & logistique") },
  { value: "project-management", label: words("Project management", "Gestion de projet") },
  { value: "procurement", label: words("Procurement & purchasing", "Achats & approvisionnement") },
  { value: "public-relations", label: words("Public relations", "Relations publiques") },
  { value: "qa", label: words("Quality assurance", "Assurance qualité") },
  { value: "research-dev", label: words("Research & development", "Recherche & développement") },
  { value: "sales", label: words("Sales", "Ventes") },
  { value: "security-risk", label: words("Security & risk", "Sécurité & risques") },
  { value: "strategy", label: words("Strategy & business analysis", "Stratégie & analyse d’activité") },
  { value: "technical-support", label: words("Technical support", "Assistance technique") },
  { value: "training", label: words("Training & development", "Formation & développement") },
  { value: "other", label: words("Another department", "Un autre service") },
  preferNot(),
];

export const careerStageOptions: AboutOption[] = [
  { value: "student-intern", label: words("Student or intern", "Étudiant·e ou stagiaire") },
  { value: "entry", label: words("Entry-level (0–2 years)", "Début de carrière (0 à 2 ans)") },
  { value: "mid", label: words("Mid-level (3–5 years)", "Intermédiaire (3 à 5 ans)") },
  { value: "senior", label: words("Senior (6–9 years)", "Confirmé·e (6 à 9 ans)") },
  { value: "lead-manager", label: words("Lead or manager (10+ years)", "Responsable ou manager (10 ans et plus)") },
  { value: "director", label: words("Director or head of department", "Directeur·rice ou chef·fe de service") },
  { value: "executive", label: words("C-level or executive", "Direction générale ou COMEX") },
  { value: "founder", label: words("Founder or owner", "Fondateur·rice ou propriétaire") },
  { value: "portfolio", label: words("Freelancer building a portfolio", "Freelance en constitution de portfolio") },
  { value: "retired-transition", label: words("Retired or changing career", "Retraité·e ou reconversion") },
  preferNot(),
];

export const companySizeOptions: AboutOption[] = [
  { value: "solo", label: words("Just me", "Moi uniquement") },
  { value: "2-10", label: words("2–10 employees", "2 à 10 employés") },
  { value: "11-50", label: words("11–50 employees", "11 à 50 employés") },
  { value: "51-200", label: words("51–200 employees", "51 à 200 employés") },
  { value: "201-500", label: words("201–500 employees", "201 à 500 employés") },
  { value: "501-1000", label: words("501–1,000 employees", "501 à 1 000 employés") },
  { value: "1001-5000", label: words("1,001–5,000 employees", "1 001 à 5 000 employés") },
  { value: "5000-plus", label: words("More than 5,000 employees", "Plus de 5 000 employés") },
  { value: "not-applicable", label: words("Not applicable", "Non applicable") },
  preferNot(),
];

export const workingEnvironmentOptions: AboutOption[] = [
  { value: "remote", label: words("Fully remote", "100 % télétravail") },
  { value: "hybrid-remote", label: words("Hybrid, mostly remote", "Hybride, majoritairement en télétravail") },
  { value: "hybrid-onsite", label: words("Hybrid, mostly on-site", "Hybride, majoritairement sur site") },
  { value: "onsite", label: words("Fully on-site", "100 % sur site") },
  { value: "field", label: words("Field-based with client visits", "Terrain avec visites clients") },
  { value: "mobile", label: words("Mobile or on the road", "Mobile / sur la route") },
  { value: "shift", label: words("Rotating shifts", "Postes en rotation") },
  { value: "night-shift", label: words("Night shift", "Équipe de nuit") },
  { value: "home-based", label: words("Home-based or domestic work", "Travail à domicile ou à la maison") },
  { value: "coworking", label: words("Coworking space", "Espace de coworking") },
  { value: "seasonal", label: words("Seasonal or temporary work", "Travail saisonnier ou temporaire") },
  { value: "unemployed", label: words("Not currently working", "Je ne travaille pas actuellement") },
  preferNot(),
];

export type TesterWorkDraft = {
  employmentStatus: string;
  industry: string;
  department: string;
  careerStage: string;
  companySize: string;
  workingEnvironment: string;
};

function isKnown(options: AboutOption[], value: string) {
  return options.some((entry) => entry.value === value);
}

export function testerWorkValid(work: TesterWorkDraft): boolean {
  if (!isKnown(employmentStatusOptions, work.employmentStatus)) return false;
  if (!isKnown(workingEnvironmentOptions, work.workingEnvironment)) return false;

  if (!isEmployedStatus(work.employmentStatus)) return true;

  return (
    isKnown(industryOptions, work.industry) &&
    isKnown(departmentOptions, work.department) &&
    isKnown(careerStageOptions, work.careerStage) &&
    isKnown(companySizeOptions, work.companySize)
  );
}
