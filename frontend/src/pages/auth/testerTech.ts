import { authWords as words } from "@/lib/auth";
import type { AboutOption } from "./testerAbout";

const preferNot = (): AboutOption => ({ value: "prefer-not", label: words("Prefer not to say", "Je préfère ne pas répondre") });

export const screenTimeOptions: AboutOption[] = [
  { value: "under-1", label: words("Less than 1 hour a day", "Moins d’une heure par jour") },
  { value: "1-2", label: words("1–2 hours a day", "1 à 2 heures par jour") },
  { value: "2-3", label: words("2–3 hours a day", "2 à 3 heures par jour") },
  { value: "3-4", label: words("3–4 hours a day", "3 à 4 heures par jour") },
  { value: "4-6", label: words("4–6 hours a day", "4 à 6 heures par jour") },
  { value: "6-8", label: words("6–8 hours a day", "6 à 8 heures par jour") },
  { value: "8-10", label: words("8–10 hours a day", "8 à 10 heures par jour") },
  { value: "10-plus", label: words("More than 10 hours a day", "Plus de 10 heures par jour") },
  { value: "not-sure", label: words("I don’t know / I never checked", "Je ne sais pas / je n’ai jamais vérifié") },
  preferNot(),
];

export const mostUsedDeviceOptions: AboutOption[] = [
  { value: "smartphone", label: words("Smartphone", "Smartphone") },
  { value: "laptop", label: words("Laptop", "Ordinateur portable") },
  { value: "desktop", label: words("Desktop computer", "Ordinateur de bureau") },
  { value: "tablet", label: words("Tablet", "Tablette") },
  { value: "smart-tv", label: words("Smart TV", "Téléviseur connecté") },
  { value: "console", label: words("Gaming console", "Console de jeu") },
  { value: "wearable", label: words("Smart watch or wearable", "Montre connectée ou objet connecté") },
  { value: "vr", label: words("VR or AR headset", "Casque VR ou AR") },
  { value: "feature-phone", label: words("Feature phone", "Téléphone portable simple") },
  { value: "e-reader", label: words("E-reader", "Liseuse") },
  { value: "other", label: words("Another device", "Un autre appareil") },
  preferNot(),
];

/** Multi-select: the question is inherently plural (“apps you rely on every day”). */
export const dailyAppOptions: AboutOption[] = [
  { value: "social", label: words("Social media", "Réseaux sociaux") },
  { value: "messaging", label: words("Messaging & chat", "Messagerie & discussion") },
  { value: "video-calls", label: words("Video calls", "Appels vidéo") },
  { value: "productivity", label: words("Productivity & work", "Productivité & travail") },
  { value: "email", label: words("Email", "E-mail") },
  { value: "streaming", label: words("Streaming video", "Streaming vidéo") },
  { value: "music", label: words("Music & audio", "Musique & audio") },
  { value: "news", label: words("News & reading", "Actualités & lecture") },
  { value: "shopping", label: words("Shopping", "Commerce") },
  { value: "finance", label: words("Banking & finance", "Banque & finance") },
  { value: "food", label: words("Food delivery", "Livraison de repas") },
  { value: "travel", label: words("Travel & transport", "Voyage & transport") },
  { value: "fitness", label: words("Fitness & health", "Fitness & santé") },
  { value: "photo", label: words("Photo & video editing", "Montage photo & vidéo") },
  { value: "gaming", label: words("Games", "Jeux") },
  { value: "learning", label: words("Education & learning", "Éducation & apprentissage") },
  { value: "maps", label: words("Maps & navigation", "Cartes & navigation") },
  { value: "utilities", label: words("Bills & utilities", "Factures & services") },
  { value: "support", label: words("Customer support & banking apps", "Assistance client & applications bancaires") },
  { value: "other", label: words("Other apps", "Autres applications") },
];

export const mobileUserTypeOptions: AboutOption[] = [
  { value: "light", label: words("Light user — now and then", "Utilisateur léger — de temps en temps") },
  { value: "regular", label: words("Regular user — a few times a week", "Utilisateur régulier — quelques fois par semaine") },
  { value: "heavy", label: words("Heavy user — several times a day", "Utilisateur intensif — plusieurs fois par jour") },
  { value: "power", label: words("Power user — all day, every day", "Super-utilisateur — toute la journée, tous les jours") },
  { value: "business", label: words("Business user", "Utilisateur professionnel") },
  { value: "social", label: words("Social user", "Utilisateur social") },
  { value: "gamer", label: words("Gamer", "Joueur") },
  { value: "creator", label: words("Content creator", "Créateur de contenu") },
  { value: "shopper", label: words("Shopper", "Acheteur") },
  { value: "student", label: words("Student", "Étudiant") },
  { value: "simple", label: words("Simple needs — I only call and message", "Besoins simples — appels et messages uniquement") },
  { value: "none", label: words("I don’t use a mobile phone", "Je n’utilise pas de téléphone portable") },
  preferNot(),
];

export const desktopUserTypeOptions: AboutOption[] = [
  { value: "none", label: words("I don’t use a desktop or laptop", "Je n’utilise pas d’ordinateur") },
  { value: "light", label: words("Light user — now and then", "Utilisateur léger — de temps en temps") },
  { value: "regular", label: words("Regular user — a few times a week", "Utilisateur régulier — quelques fois par semaine") },
  { value: "heavy", label: words("Heavy user — most of the day", "Utilisateur intensif — la majeure partie de la journée") },
  { value: "professional", label: words("Professional or work use", "Usage professionnel") },
  { value: "creative", label: words("Creative professional", "Professionnel créatif") },
  { value: "developer", label: words("Developer or technical power user", "Développeur ou super-utilisateur technique") },
  { value: "gamer", label: words("Gamer", "Joueur") },
  { value: "student", label: words("Student", "Étudiant") },
  { value: "remote", label: words("Remote worker", "Télétravailleur") },
  preferNot(),
];

/** Multi-select: people own more than one device. */
export const ownedDeviceOptions: AboutOption[] = [
  { value: "android", label: words("Android smartphone", "Smartphone Android") },
  { value: "iphone", label: words("iPhone", "iPhone") },
  { value: "feature-phone", label: words("Feature phone", "Téléphone portable simple") },
  { value: "laptop", label: words("Laptop", "Ordinateur portable") },
  { value: "desktop", label: words("Desktop computer", "Ordinateur de bureau") },
  { value: "tablet", label: words("Tablet", "Tablette") },
  { value: "smart-tv", label: words("Smart TV", "Téléviseur connecté") },
  { value: "console", label: words("Gaming console", "Console de jeu") },
  { value: "wearable", label: words("Smart watch or wearable", "Montre connectée ou objet connecté") },
  { value: "e-reader", label: words("E-reader", "Liseuse") },
  { value: "vr", label: words("VR or AR headset", "Casque VR ou AR") },
  { value: "other", label: words("Another device", "Un autre appareil") },
];

export type TesterTechDraft = {
  screenTime: string;
  mostUsedDevice: string;
  dailyApps: string[];
  mobileUserType: string;
  desktopUserType: string;
  ownedDevices: string[];
};

function isKnown(options: AboutOption[], value: string) {
  return options.some((entry) => entry.value === value);
}

export function testerTechValid(tech: TesterTechDraft): boolean {
  if (!isKnown(screenTimeOptions, tech.screenTime)) return false;
  if (!isKnown(mostUsedDeviceOptions, tech.mostUsedDevice)) return false;
  if (!isKnown(mobileUserTypeOptions, tech.mobileUserType)) return false;
  if (!isKnown(desktopUserTypeOptions, tech.desktopUserType)) return false;
  if (!tech.dailyApps.some((code) => isKnown(dailyAppOptions, code))) return false;
  if (!tech.ownedDevices.some((code) => isKnown(ownedDeviceOptions, code))) return false;
  return true;
}
