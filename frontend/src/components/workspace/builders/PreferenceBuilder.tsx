import { ImagePlus, Plus, Upload } from "lucide-react";
import { type BuilderProps } from "./types";

export function PreferenceBuilder({ text, custom, onPatch }: BuilderProps) {
  const variants = (custom.variants as string[]) ?? ["", ""];
  const randomize = (custom.randomize as boolean) ?? false;
  const oneAtATime = (custom.one_at_a_time as boolean) ?? false;
  const showTitles = (custom.show_titles as boolean) ?? false;
  const taskInstruction = (custom.task_instruction as string) ?? "";

  const addVariant = () => {
    if (variants.length < 5) onPatch({ variants: [...variants, ""] });
  };

  return (
    <div className="grid min-w-0 gap-6">
      <section className="rounded-2xl border border-[#e8e8ec] bg-white p-5">
        <label className="block text-[14px] font-bold text-[#0b1e4b]" htmlFor="preference-task">{text({ en: "Task", fr: "Tâche" })}</label>
        <p className="mt-1 text-[12.5px] text-[#6d6d70]">{text({ en: "Describe the options you want participants to choose from. For example, “Which design do you prefer?”", fr: "Décrivez les options parmi lesquelles les participants doivent choisir." })}</p>
        <textarea id="preference-task" value={taskInstruction} onChange={(event) => onPatch({ task_instruction: event.target.value })} placeholder={text({ en: "Task description", fr: "Description de la tâche" })} rows={3} className="mt-3 w-full resize-none rounded-lg border border-[#d9d9df] bg-white px-4 py-3 text-[14px] leading-relaxed text-[#0b1e4b] placeholder:text-[#a1a1aa] focus:border-[#1d4ed8] focus:outline-none focus:ring-2 focus:ring-[#1d4ed8]/20" />
        <p className="mt-2 text-right text-[12px] text-[#6d6d70]">{taskInstruction.length}/330</p>
      </section>

      <section className="rounded-2xl border border-[#e8e8ec] bg-white p-5">
        <p className="text-[14px] font-bold text-[#0b1e4b]">{text({ en: "Designs", fr: "Designs" })}</p>
        <p className="mt-1 max-w-[70ch] text-[12.5px] leading-relaxed text-[#6d6d70]">{text({ en: "The designs you choose will be shown to your participants, where they’ll pick the one they prefer. You can randomize the order or show designs one at a time.", fr: "Les designs sélectionnés seront montrés aux participants afin qu’ils choisissent leur préféré." })}</p>
        <div className="mt-4 grid gap-3">
          <label className="flex cursor-pointer items-center gap-3 text-[13.5px] text-[#0b1e4b]"><input type="checkbox" checked={randomize} onChange={(event) => onPatch({ randomize: event.target.checked })} className="size-4" />{text({ en: "Randomize the order that designs are shown to participants", fr: "Randomiser l’ordre d’affichage des designs" })}</label>
          <label className="flex cursor-pointer items-center gap-3 text-[13.5px] text-[#0b1e4b]"><input type="checkbox" checked={oneAtATime} onChange={(event) => onPatch({ one_at_a_time: event.target.checked })} className="size-4" />{text({ en: "Show designs one at a time", fr: "Montrer les designs un par un" })}</label>
          <label className="flex cursor-pointer items-center gap-3 text-[13.5px] text-[#0b1e4b]"><input type="checkbox" checked={showTitles} onChange={(event) => onPatch({ show_titles: event.target.checked })} className="size-4" />{text({ en: "Show design titles to participants", fr: "Afficher les titres des designs" })}</label>
        </div>
        <p className="mt-5 flex items-center gap-2 text-[12.5px] text-[#6d6d70]"><ImagePlus className="size-4 text-[#1d4ed8]" aria-hidden="true" />{text({ en: "Upload between 2 and 5 designs.", fr: "Téléversez entre 2 et 5 designs." })}</p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {variants.map((variant, index) => (
            <label key={index} className="flex min-h-[156px] cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed border-[#d9d9df] px-5 text-center transition hover:border-[#1d4ed8] hover:bg-[#f7f9fc]">
              <Upload className="size-5 text-[#1d4ed8]" strokeWidth={1.7} aria-hidden="true" />
              <span className="mt-3 text-[13.5px] font-semibold text-[#0b1e4b]">{text({ en: "Drag and drop to upload file", fr: "Glissez-déposez un fichier" })}</span>
              <span className="mt-1 text-[11.5px] text-[#6d6d70]">JPG, JPEG, PNG, GIF or MP4 supported</span>
              <input value={variant} onChange={(event) => onPatch({ variants: variants.map((value, itemIndex) => itemIndex === index ? event.target.value : value) })} placeholder={text({ en: "Design title (optional)", fr: "Titre du design (facultatif)" })} className="mt-3 w-full rounded-lg border border-[#d9d9df] bg-white px-3 py-2 text-[12px] text-[#0b1e4b] placeholder:text-[#a1a1aa] focus:border-[#1d4ed8] focus:outline-none" />
            </label>
          ))}
        </div>
        <button type="button" onClick={addVariant} disabled={variants.length >= 5} className="mt-4 inline-flex min-h-[36px] items-center gap-1.5 rounded-full bg-[#18181b] px-4 text-[13px] font-medium text-white hover:bg-black disabled:cursor-not-allowed disabled:opacity-40"><Plus className="size-4" aria-hidden="true" />{text({ en: "Add another design", fr: "Ajouter un design" })}</button>
      </section>
    </div>
  );
}
