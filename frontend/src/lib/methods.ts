export type MethodInfo = {
  key: string;
  title: { en: string; fr: string };
  body: { en: string; fr: string };
  group: { en: string; fr: string };
};

export const METHOD_REGISTRY: MethodInfo[] = [
  { key: "prototype.task", title: { en: "Prototype", fr: "Prototype" }, body: { en: "People try your design and tell you what happened.", fr: "Les gens essaient votre design et racontent." }, group: { en: "Try it", fr: "Essayer" } },
  { key: "preference", title: { en: "Pick your favorite", fr: "Préférence" }, body: { en: "People pick what they like best. Ties are ok.", fr: "Les gens choisissent ce qu’ils préfèrent." }, group: { en: "Choose", fr: "Choisir" } },
  { key: "five_second", title: { en: "5 second test", fr: "Test de 5 secondes" }, body: { en: "People look for 5 seconds, then say what they remember.", fr: "Les gens regardent 5 secondes puis racontent." }, group: { en: "First look", fr: "Premier regard" } },
  { key: "survey.single", title: { en: "Survey: one answer", fr: "Enquête : un choix" }, body: { en: "One question, one answer. Clear totals.", fr: "Une question, une réponse. Totaux clairs." }, group: { en: "Ask", fr: "Poser" } },
  { key: "survey.multi", title: { en: "Survey: many answers", fr: "Enquête : choix multiples" }, body: { en: "Tick all that apply.", fr: "Cochez tout ce qui s’applique." }, group: { en: "Ask", fr: "Poser" } },
  { key: "survey.rating", title: { en: "Survey: rating", fr: "Enquête : note" }, body: { en: "Rate from low to high.", fr: "Notez de bas en haut." }, group: { en: "Ask", fr: "Poser" } },
  { key: "survey.text", title: { en: "Survey: free text", fr: "Enquête : texte libre" }, body: { en: "People write in their own words.", fr: "Les gens écrivent avec leurs mots." }, group: { en: "Ask", fr: "Poser" } },
  { key: "survey.ranking", title: { en: "Rank in order", fr: "Classer par ordre" }, body: { en: "Drag the best to the top.", fr: "Mettez le meilleur en haut." }, group: { en: "Choose", fr: "Choisir" } },
  { key: "survey.constant_sum", title: { en: "Split points", fr: "Répartir des points" }, body: { en: "Share 100 points between options.", fr: "Répartissez 100 points entre options." }, group: { en: "Choose", fr: "Choisir" } },
  { key: "first_click", title: { en: "First click", fr: "Premier clic" }, body: { en: "See where people click first on your picture.", fr: "Voyez où les gens cliquent en premier." }, group: { en: "First look", fr: "Premier regard" } },
  { key: "card_sort", title: { en: "Card sorting", fr: "Tri de cartes" }, body: { en: "People group cards into piles that make sense.", fr: "Les gens rangent les cartes par idées." }, group: { en: "Organize", fr: "Organiser" } },
  { key: "tree_test", title: { en: "Menu test", fr: "Test menu" }, body: { en: "People find things in your menu. Wrong turns are kept.", fr: "Les gens cherchent dans le menu." }, group: { en: "Organize", fr: "Organiser" } },
  { key: "accessibility.issue", title: { en: "Report a problem", fr: "Signaler un problème" }, body: { en: "People flag what blocks them.", fr: "Les gens signalent ce qui les bloque." }, group: { en: "Fix", fr: "Corriger" } },
  { key: "language.review", title: { en: "Check the wording", fr: "Vérifier le texte" }, body: { en: "People review French, Arabic, or English text.", fr: "Les gens relisent le texte FR, AR ou EN." }, group: { en: "Fix", fr: "Corriger" } },
  { key: "media.review", title: { en: "Video or audio check", fr: "Vérif vidéo ou audio" }, body: { en: "People watch or listen, then answer.", fr: "Les gens regardent ou écoutent, puis répondent." }, group: { en: "Try it", fr: "Essayer" } },
];

export const DASHBOARD_TO_METHOD: Record<string, string> = {
  prototype: "prototype.task",
  card: "card_sort",
  preference: "preference",
  tree: "tree_test",
  survey: "survey.single",
  five: "five_second",
  click: "first_click",
  recruit: "recruit",
};

export function methodByKey(key: string) {
  return METHOD_REGISTRY.find((method) => method.key === key);
}
