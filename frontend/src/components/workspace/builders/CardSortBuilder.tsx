import { AlignLeft, Minus, Plus, Upload } from "lucide-react";
import { type BuilderProps } from "./types";

export function CardSortBuilder({ text, custom, onPatch }: BuilderProps) {
  const sortType = (custom.sort_type as "open" | "closed" | null) ?? null;
  const cards = (custom.cards as string[]) ?? [""];
  const randomize = (custom.randomize as boolean) ?? false;
  const taskInstruction = (custom.task_instruction as string) ?? "";

  return (
    <div className="grid min-w-0 gap-6">
      <section className="rounded-2xl border border-[#e8e8ec] bg-white p-5">
        <label className="block text-[14px] font-bold text-[#0b1e4b]" htmlFor="cs-task">
          {text({ en: "Task", fr: "Tâche" })}
        </label>
        <p className="mt-1 text-[12.5px] text-[#6d6d70]">
          {text({ en: "Provide the tester with contextualized instructions on how to categorize the content on your cards.", fr: "Donnez aux testeurs des instructions contextualisées pour catégoriser le contenu." })}
        </p>
        <textarea
          id="cs-task"
          value={taskInstruction}
          onChange={(e) => onPatch({ task_instruction: e.target.value })}
          placeholder={text({ en: "e.g. We'd like to understand how you group items and what names you would give to those groups", fr: "ex. Nous aimerions comprendre comment vous groupez les éléments et quels noms vous donneriez à ces groupes" })}
          rows={3}
          className="mt-3 w-full resize-none rounded-lg border border-[#d9d9df] bg-white px-4 py-3 text-[14px] leading-relaxed text-[#0b1e4b] placeholder:text-[#a1a1aa] focus:border-[#1d4ed8] focus:outline-none focus:ring-2 focus:ring-[#1d4ed8]/20"
        />
        <p className="mt-2 text-right text-[12px] text-[#6d6d70]">{taskInstruction.length}/330</p>
      </section>

      <section className="rounded-2xl border border-[#e8e8ec] bg-white p-5">
        <p className="text-[14px] font-bold text-[#0b1e4b]">{text({ en: "Type", fr: "Type" })}</p>
        <p className="mt-1 text-[12.5px] text-[#6d6d70]">{text({ en: "Choose between open and close card sorting.", fr: "Choisissez entre tri ouvert et fermé." })}</p>
        
        <div className="mt-4 grid gap-3">
          <label className={`cursor-pointer rounded-xl border-2 p-4 transition ${sortType === "open" ? "border-[#1d4ed8] bg-[#f7f9fc]" : "border-[#e8e8ec] hover:border-[#1d4ed8]/40"}`}>
            <div className="flex items-start gap-3">
              <input
                type="radio"
                name="sort-type"
                value="open"
                checked={sortType === "open"}
                onChange={() => onPatch({ sort_type: "open" })}
                className="mt-0.5"
              />
              <div className="min-w-0 flex-1">
                <p className="text-[14px] font-bold text-[#0b1e4b]">{text({ en: "Open card sorting", fr: "Tri de cartes ouvert" })}</p>
                <p className="mt-1 text-[13px] text-[#6d6d70]">{text({ en: "Participants create and name their own categories", fr: "Les participants créent et nomment leurs propres catégories" })}</p>
                <p className="mt-2 text-[12px] italic text-[#6d6d70]">{text({ en: "Requires categories for all cards in this test", fr: "Nécessite des catégories pour toutes les cartes de ce test" })}</p>
              </div>
            </div>
          </label>

          <label className={`cursor-pointer rounded-xl border-2 p-4 transition ${sortType === "closed" ? "border-[#1d4ed8] bg-[#f7f9fc]" : "border-[#e8e8ec] hover:border-[#1d4ed8]/40"}`}>
            <div className="flex items-start gap-3">
              <input
                type="radio"
                name="sort-type"
                value="closed"
                checked={sortType === "closed"}
                onChange={() => onPatch({ sort_type: "closed" })}
                className="mt-0.5"
              />
              <div className="min-w-0 flex-1">
                <p className="text-[14px] font-bold text-[#0b1e4b]">{text({ en: "Closed card sorting", fr: "Tri de cartes fermé" })}</p>
                <p className="mt-1 text-[13px] text-[#6d6d70]">{text({ en: "You choose the categories that participants use", fr: "Vous choisissez les catégories que les participants utilisent" })}</p>
              </div>
            </div>
          </label>
        </div>

        <div className="mt-5 flex items-center gap-2 rounded-lg bg-[#f3e8ff] px-4 py-3">
          <AlignLeft className="size-4 shrink-0 text-[#7c3aed]" />
          <p className="text-[12.5px] text-[#6b21a8]">
            {text({ en: "Please note, only participants using desktop will be able to complete the test.", fr: "Veuillez noter que seuls les participants sur ordinateur pourront effectuer le test." })}
          </p>
        </div>
      </section>

      <section className="rounded-2xl border border-[#e8e8ec] bg-white p-5">
        <p className="text-[14px] font-bold text-[#0b1e4b]">{text({ en: "Card sorting settings", fr: "Paramètres du tri" })}</p>
        <label className="mt-4 flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={randomize}
            onChange={(e) => onPatch({ randomize: e.target.checked })}
            className="size-4"
          />
          <span className="text-[13.5px] text-[#0b1e4b]">
            {text({ en: "Randomize the order in which the cards will be shown to the testers", fr: "Randomiser l'ordre dans lequel les cartes seront montrées" })}
          </span>
        </label>
      </section>

      <section className="rounded-2xl border border-[#e8e8ec] bg-white p-5">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[14px] font-bold text-[#0b1e4b]">{text({ en: "Cards", fr: "Cartes" })}</p>
            <p className="mt-1 text-[12.5px] text-[#6d6d70]">
              {text({ en: "Create the cards you want participants to categorise. Make sure to have a separate card name per row. You can also import the cards from a CSV file.", fr: "Créez les cartes que les participants doivent catégoriser." })} <button type="button" className="text-[#1d4ed8] hover:underline">{text({ en: "Download CSV template", fr: "Télécharger modèle CSV" })}</button>
            </p>
          </div>
          <button
            type="button"
            className="inline-flex min-h-[36px] items-center gap-1.5 rounded-full border border-[#d9d9df] px-4 text-[13px] font-medium text-[#0b1e4b] hover:bg-[#f7f9fc]"
          >
            <Upload className="size-4" strokeWidth={1.8} aria-hidden="true" />
            {text({ en: "Import", fr: "Importer" })}
          </button>
        </div>

        <div className="mt-4 space-y-2">
          {cards.map((card, i) => (
            <div key={i} className="flex items-center gap-2">
              <input
                value={card}
                onChange={(e) => onPatch({ cards: cards.map((c, j) => (j === i ? e.target.value : c)) })}
                placeholder={text({ en: "Card name", fr: "Nom de la carte" })}
                className="min-h-[44px] flex-1 rounded-lg border border-[#d9d9df] bg-white px-4 text-[14px] text-[#0b1e4b] placeholder:text-[#a1a1aa] focus:border-[#1d4ed8] focus:outline-none focus:ring-2 focus:ring-[#1d4ed8]/20"
              />
              {cards.length > 1 && (
                <button
                  type="button"
                  onClick={() => onPatch({ cards: cards.filter((_, j) => j !== i) })}
                  className="grid size-9 shrink-0 place-items-center rounded-lg text-[#6d6d70] hover:bg-[#f4f4f5]"
                  aria-label={text({ en: "Remove card", fr: "Supprimer" })}
                >
                  <Minus className="size-4" />
                </button>
              )}
            </div>
          ))}
        </div>

        <button
          type="button"
          onClick={() => onPatch({ cards: [...cards, ""] })}
          className="mt-3 inline-flex items-center gap-1.5 text-[13px] font-medium text-[#1d4ed8] hover:underline"
        >
          <Plus className="size-4" />
          {text({ en: "Add card", fr: "Ajouter une carte" })}
        </button>

        <p className="mt-4 text-[12px] text-[#6d6d70]">{cards.filter(c => c.trim()).length}/100</p>
      </section>
    </div>
  );
}
