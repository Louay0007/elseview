import { authWords as words } from "@/lib/auth";
import type { AboutOption } from "./testerAbout";

const preferNot = (): AboutOption => ({ value: "prefer-not", label: words("Prefer not to say", "Je préfère ne pas répondre") });

export const petOptions: AboutOption[] = [
  { value: "cat", label: words("One cat", "Un chat") },
  { value: "cats", label: words("Two or more cats", "Deux chats ou plus") },
  { value: "dog", label: words("One dog", "Un chien") },
  { value: "dogs", label: words("Two or more dogs", "Deux chiens ou plus") },
  { value: "cats-dogs", label: words("Both cats and dogs", "Des chats et des chiens") },
  { value: "bird", label: words("Birds", "Oiseaux") },
  { value: "fish", label: words("Fish or aquarium", "Poissons ou aquarium") },
  { value: "small-mammal", label: words("Small mammals (rabbit, hamster, guinea pig)", "Petits mammifères (lapin, hamster, cochon d’Inde)") },
  { value: "reptile", label: words("Reptiles", "Reptiles") },
  { value: "farm", label: words("Farm or working animals", "Animaux de ferme ou de travail") },
  { value: "other", label: words("Other pets", "Autres animaux") },
  preferNot(),
];

export const hobbyOptions: AboutOption[] = [
  { value: "sports", label: words("Sports and fitness", "Sport et fitness") },
  { value: "reading", label: words("Reading", "Lecture") },
  { value: "cooking", label: words("Cooking and baking", "Cuisine et pâtisserie") },
  { value: "gaming", label: words("Gaming", "Jeux vidéo") },
  { value: "music", label: words("Music", "Musique") },
  { value: "movies", label: words("Movies and TV", "Cinéma et télévision") },
  { value: "art", label: words("Art and design", "Art et design") },
  { value: "photography", label: words("Photography", "Photographie") },
  { value: "travel", label: words("Travel", "Voyage") },
  { value: "gardening", label: words("Gardening", "Jardinage") },
  { value: "diy", label: words("DIY and crafts", "Bricolage et loisirs créatifs") },
  { value: "fashion", label: words("Fashion and beauty", "Mode et beauté") },
  { value: "tech", label: words("Technology and gadgets", "Technologie et objets connectés") },
  { value: "volunteering", label: words("Volunteering and community", "Bénévolat et vie associative") },
  { value: "religion", label: words("Religion and spirituality", "Religion et spiritualité") },
  { value: "outdoors", label: words("Outdoor activities", "Activités de plein air") },
  { value: "collecting", label: words("Collecting", "Collection") },
  { value: "writing", label: words("Writing", "Écriture") },
  { value: "dancing", label: words("Dancing", "Danse") },
  { value: "other", label: words("Another hobby", "Un autre passe-temps") },
  preferNot(),
];

export const fitnessOptions: AboutOption[] = [
  { value: "none", label: words("I don’t exercise regularly", "Je ne fais pas de sport régulièrement") },
  { value: "walking", label: words("Walking or jogging", "Marche ou course à pied") },
  { value: "running", label: words("Running", "Course à pied") },
  { value: "gym", label: words("Gym or weight training", "Salle de sport ou musculation") },
  { value: "team-sport", label: words("Team sports", "Sports collectifs") },
  { value: "individual-sport", label: words("Individual sports", "Sports individuels") },
  { value: "yoga", label: words("Yoga or pilates", "Yoga ou pilates") },
  { value: "swimming", label: words("Swimming", "Natation") },
  { value: "cycling", label: words("Cycling", "Cyclisme") },
  { value: "martial-arts", label: words("Martial arts", "Arts martiaux") },
  { value: "dancing", label: words("Dancing", "Danse") },
  { value: "hiking", label: words("Hiking or trekking", "Randonnée ou trek") },
  { value: "other", label: words("Other activity", "Une autre activité") },
  preferNot(),
];

export const vehicleOptions: AboutOption[] = [
  { value: "yes", label: words("Yes", "Oui") },
  { value: "no", label: words("No", "Non") },
];

export const shoppingFrequencyOptions: AboutOption[] = [
  { value: "never", label: words("Never", "Jamais") },
  { value: "less-monthly", label: words("Less than once a month", "Moins d’une fois par mois") },
  { value: "monthly", label: words("About once a month", "Environ une fois par mois") },
  { value: "few-monthly", label: words("A few times a month", "Quelques fois par mois") },
  { value: "weekly", label: words("About once a week", "Environ une fois par semaine") },
  { value: "few-weekly", label: words("A few times a week", "Quelques fois par semaine") },
  { value: "several-weekly", label: words("Several times a week", "Plusieurs fois par semaine") },
  { value: "daily", label: words("Every day", "Tous les jours") },
  preferNot(),
];

export type TesterLifestyleDraft = {
  noPets: boolean;
  petsOwned: string;
  hobby: string;
  fitness: string;
  hasVehicle: string;
  shoppingFrequency: string;
};

function isKnown(options: AboutOption[], value: string) {
  return options.some((entry) => entry.value === value);
}

export function testerLifestyleValid(lifestyle: TesterLifestyleDraft): boolean {
  if (!lifestyle.noPets && !isKnown(petOptions, lifestyle.petsOwned)) return false;
  if (!isKnown(hobbyOptions, lifestyle.hobby)) return false;
  if (!isKnown(fitnessOptions, lifestyle.fitness)) return false;
  if (!isKnown(vehicleOptions, lifestyle.hasVehicle)) return false;
  return isKnown(shoppingFrequencyOptions, lifestyle.shoppingFrequency);
}
