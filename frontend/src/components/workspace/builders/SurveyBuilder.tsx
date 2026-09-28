import { useState } from "react";
import {
  FieldError,
  OrderedOptions,
  PreviewBox,
  Section,
  Segmented,
  Toggle,
  areaCls,
  inputCls,
  type BuilderProps,
} from "./types";
import {
  clampMaxLength,
  clampMultiBounds,
  constantSumError,
  filledValues,
  multiBoundsError,
  optionsError,
  questionError,
  scaleValues,
  allocatedSum,
  allocationTotal,
} from "./validation";

const KIND: Record<string, { heading: string; hint: string }> = {
  "survey.single": { heading: "Single-choice question", hint: "Testers pick exactly one answer." },
  "survey.multi": { heading: "Multiple-choice question", hint: "Testers tick all answers that fit." },
  "survey.rating": { heading: "Rating question", hint: "Testers rate on your scale." },
  "survey.text": { heading: "Free-text question", hint: "Testers write in their own words." },
  "survey.ranking": { heading: "Ranking question", hint: "Testers put answers in order." },
  "survey.constant_sum": { heading: "Constant-sum question", hint: "Testers split points between answers." },
};

function QuestionField({ text, question, onPatch }: {
  text: BuilderProps["text"];
  question: string;
  onPatch: BuilderProps["onPatch"];
}) {
  const err = questionError(question);
  return (
    <Section
      labelledBy="sv-q-h"
      title={text({ en: "Question", fr: "Question" })}
      hint={text({ en: "Shown exactly as written.", fr: "Affichée telle quelle." })}
    >
      <label className="grid gap-1.5 text-[13.5px] font-semibold text-[#0b1e4b]" htmlFor="sv-question">
        {text({ en: "Question prompt", fr: "Énoncé de la question" })}
      </label>
      <textarea
        id="sv-question"
        value={question}
        onChange={(e) => onPatch({ question: e.target.value })}
        placeholder={text({ en: "What brings you here today?", fr: "Qu’est-ce qui vous amène ici ?" })}
        aria-label={text({ en: "Question prompt", fr: "Énoncé de la question" })}
        aria-invalid={err ? true : undefined}
        rows={2}
        className={areaCls}
      />
      {err && <FieldError>{text({ en: "Add a question before continuing.", fr: "Ajoutez une question pour continuer." })}</FieldError>}
    </Section>
  );
}

function SingleBody({ text, custom, onPatch }: BuilderProps) {
  const question = (custom.question as string) ?? "";
  const options = (custom.options as string[]) ?? ["", ""];
  const allowOther = (custom.allow_other as boolean) ?? false;
  const required = (custom.require_answer as boolean) ?? true;
  const randomize = (custom.randomize as boolean) ?? false;
  const filled = filledValues(options);
  const optErr = optionsError(options, 2);

  return (
    <div className="grid min-w-0 gap-5">
      <QuestionField text={text} question={question} onPatch={onPatch} />
      <Section
        labelledBy="sv-opt-h"
        title={text({ en: "Answer options", fr: "Options de réponse" })}
        hint={text({ en: "Need at least two filled answers.", fr: "Au moins deux réponses remplies." })}
      >
        <OrderedOptions
          items={options}
          onChange={(next) => onPatch({ options: next, option_count: next.length })}
          itemLabel={text({ en: "Option", fr: "Option" })}
          addLabel={text({ en: "Add option", fr: "Ajouter une option" })}
          min={2}
        />
        {optErr && <FieldError>{text({ en: "Fill in at least two answers.", fr: "Renseignez au moins deux réponses." })}</FieldError>}
        <Toggle
          checked={allowOther}
          onChange={(v) => onPatch({ allow_other: v })}
          label={text({ en: "Include an “Other” option", fr: "Inclure une option « Autre »" })}
          hint={text({ en: "Testers can write their own answer.", fr: "Les testeurs écrivent leur réponse." })}
        />
      </Section>
      <Section labelledBy="sv-behav-h" title={text({ en: "Behaviour", fr: "Comportement" })}>
        <Toggle checked={required} onChange={(v) => onPatch({ require_answer: v })} label={text({ en: "Answer required", fr: "Réponse obligatoire" })} />
        <Toggle checked={randomize} onChange={(v) => onPatch({ randomize: v })} label={text({ en: "Shuffle options", fr: "Mélanger les options" })} />
      </Section>
      <PreviewBox title={text({ en: "Participant preview", fr: "Aperçu participant" })}>
        <p className="text-[14px] font-semibold text-[#0b1e4b]">{question || text({ en: "Your question appears here.", fr: "Votre question apparaît ici." })}</p>
        <fieldset className="mt-3 grid gap-2">
          <legend className="sr-only">{text({ en: "Answers", fr: "Réponses" })}</legend>
          {filled.length === 0 && <p className="text-[13px] text-[#6d6d70]">{text({ en: "Answers appear once you fill them in.", fr: "Les réponses apparaissent une fois renseignées." })}</p>}
          {filled.map((opt, i) => (
            <label key={i} className="flex cursor-pointer items-center gap-2.5 rounded-xl border border-[#e8e8ec] px-3 py-2.5 text-[13.5px] text-[#0b1e4b] hover:border-[#1d4ed8]/50">
              <input type="radio" name="sv-single-preview" className="size-4 accent-[#1d4ed8]" />
              {opt}
            </label>
          ))}
          {allowOther && (
            <label className="flex cursor-pointer items-center gap-2.5 rounded-xl border border-dashed border-[#d9d9df] px-3 py-2.5 text-[13.5px] text-[#0b1e4b]">
              <input type="radio" name="sv-single-preview" className="size-4 accent-[#1d4ed8]" />
              {text({ en: "Other:", fr: "Autre :" })}
              <input aria-label={text({ en: "Other answer", fr: "Autre réponse" })} placeholder="…" className="min-w-0 flex-1 border-b border-[#d9d9df] text-[13.5px] outline-none focus:border-[#1d4ed8]" />
            </label>
          )}
        </fieldset>
      </PreviewBox>
    </div>
  );
}

function MultiBody({ text, custom, onPatch }: BuilderProps) {
  const question = (custom.question as string) ?? "";
  const options = (custom.options as string[]) ?? ["", ""];
  const required = (custom.require_answer as boolean) ?? true;
  const randomize = (custom.randomize as boolean) ?? false;
  const filled = filledValues(options);
  const bounds = clampMultiBounds(custom.min_selected, custom.max_selected, Math.max(filled.length, 1));
  const optErr = optionsError(options, 2);
  const boundErr = multiBoundsError(bounds.min, bounds.max, filled.length);

  return (
    <div className="grid min-w-0 gap-5">
      <QuestionField text={text} question={question} onPatch={onPatch} />
      <Section
        labelledBy="sv-opt-h"
        title={text({ en: "Answer options", fr: "Options de réponse" })}
        hint={text({ en: "Need at least two filled answers.", fr: "Au moins deux réponses remplies." })}
      >
        <OrderedOptions
          items={options}
          onChange={(next) => onPatch({ options: next, option_count: next.length })}
          itemLabel={text({ en: "Option", fr: "Option" })}
          addLabel={text({ en: "Add option", fr: "Ajouter une option" })}
          min={2}
        />
        {optErr && <FieldError>{text({ en: "Fill in at least two answers.", fr: "Renseignez au moins deux réponses." })}</FieldError>}
      </Section>
      <Section
        labelledBy="sv-lim-h"
        title={text({ en: "Selection limits", fr: "Limites de sélection" })}
        hint={text({ en: `Maximum cannot exceed ${filled.length} filled option${filled.length === 1 ? "" : "s"}.`, fr: `Le maximum ne peut pas dépasser ${filled.length} option(s) remplie(s).` })}
      >
        <div className="grid grid-cols-2 gap-3">
          <label className="grid gap-1.5 text-[13.5px] font-semibold text-[#0b1e4b]">
            {text({ en: "Minimum", fr: "Minimum" })}
            <input type="number" min={1} max={bounds.max} value={bounds.min} onChange={(e) => onPatch({ min_selected: clampMultiBounds(Number(e.target.value), bounds.max, Math.max(filled.length, 1)).min })} className={inputCls} />
          </label>
          <label className="grid gap-1.5 text-[13.5px] font-semibold text-[#0b1e4b]">
            {text({ en: "Maximum", fr: "Maximum" })}
            <input type="number" min={bounds.min} max={Math.max(filled.length, 1)} value={bounds.max} onChange={(e) => onPatch({ max_selected: clampMultiBounds(bounds.min, Number(e.target.value), Math.max(filled.length, 1)).max })} className={inputCls} />
          </label>
        </div>
        {boundErr === "max-exceeds-options" && <FieldError>{text({ en: "Maximum cannot exceed the filled options.", fr: "Le maximum ne peut pas dépasser les options remplies." })}</FieldError>}
        {boundErr === "min-exceeds-max" && <FieldError>{text({ en: "Minimum cannot exceed maximum.", fr: "Le minimum ne peut pas dépasser le maximum." })}</FieldError>}
      </Section>
      <Section labelledBy="sv-behav-h" title={text({ en: "Behaviour", fr: "Comportement" })}>
        <Toggle checked={required} onChange={(v) => onPatch({ require_answer: v })} label={text({ en: "Answer required", fr: "Réponse obligatoire" })} />
        <Toggle checked={randomize} onChange={(v) => onPatch({ randomize: v })} label={text({ en: "Shuffle options", fr: "Mélanger les options" })} />
      </Section>
      <PreviewBox title={text({ en: "Participant preview", fr: "Aperçu participant" })}>
        <p className="text-[14px] font-semibold text-[#0b1e4b]">{question || text({ en: "Your question appears here.", fr: "Votre question apparaît ici." })}</p>
        <p className="mt-1 text-[12px] text-[#6d6d70]">{text({ en: `Pick ${bounds.min} to ${bounds.max}.`, fr: `Choisissez de ${bounds.min} à ${bounds.max}.` })}</p>
        <div className="mt-3 grid gap-2">
          {filled.length === 0 && <p className="text-[13px] text-[#6d6d70]">{text({ en: "Answers appear once you fill them in.", fr: "Les réponses apparaissent une fois renseignées." })}</p>}
          {filled.map((opt, i) => (
            <label key={i} className="flex cursor-pointer items-center gap-2.5 rounded-xl border border-[#e8e8ec] px-3 py-2.5 text-[13.5px] text-[#0b1e4b] hover:border-[#1d4ed8]/50">
              <input type="checkbox" className="size-4 accent-[#1d4ed8]" />
              {opt}
            </label>
          ))}
        </div>
      </PreviewBox>
    </div>
  );
}

function RatingBody({ text, custom, onPatch }: BuilderProps) {
  const question = (custom.question as string) ?? "";
  const scale = (custom.scale as string) ?? "1-5";
  const lowLabel = (custom.low_label as string) ?? "";
  const highLabel = (custom.high_label as string) ?? "";
  const neutralLabel = (custom.neutral_label as string) ?? "";
  const required = (custom.require_answer as boolean) ?? true;
  const values = scaleValues(scale);

  return (
    <div className="grid min-w-0 gap-5">
      <QuestionField text={text} question={question} onPatch={onPatch} />
      <Section labelledBy="sv-scale-h" title={text({ en: "Scale setup", fr: "Échelle" })}>
        <Segmented
          name="sv-scale"
          value={scale}
          onChange={(value) => onPatch({ scale: value })}
          options={[
            { value: "1-5", title: "1 to 5" },
            { value: "1-7", title: "1 to 7" },
            { value: "1-10", title: "1 to 10" },
          ]}
        />
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="grid gap-1.5 text-[13.5px] font-semibold text-[#0b1e4b]">{text({ en: "Low endpoint label", fr: "Label bas" })}
            <input value={lowLabel} onChange={(e) => onPatch({ low_label: e.target.value })} placeholder={text({ en: "Not at all", fr: "Pas du tout" })} className={`${inputCls} font-normal`} />
          </label>
          <label className="grid gap-1.5 text-[13.5px] font-semibold text-[#0b1e4b]">{text({ en: "High endpoint label", fr: "Label haut" })}
            <input value={highLabel} onChange={(e) => onPatch({ high_label: e.target.value })} placeholder={text({ en: "Very much", fr: "Énormément" })} className={`${inputCls} font-normal`} />
          </label>
        </div>
        <label className="grid gap-1.5 text-[13.5px] font-semibold text-[#0b1e4b]">{text({ en: "Neutral label (optional)", fr: "Label neutre (facultatif)" })}
          <input value={neutralLabel} onChange={(e) => onPatch({ neutral_label: e.target.value })} placeholder={text({ en: "Neither / no opinion", fr: "Ni l’un ni l’autre" })} className={`${inputCls} font-normal`} />
        </label>
      </Section>
      <Section labelledBy="sv-behav-h" title={text({ en: "Behaviour", fr: "Comportement" })}>
        <Toggle checked={required} onChange={(v) => onPatch({ require_answer: v })} label={text({ en: "Answer required", fr: "Réponse obligatoire" })} />
      </Section>
      <PreviewBox title={text({ en: "Participant preview", fr: "Aperçu participant" })}>
        <p className="text-[14px] font-semibold text-[#0b1e4b]">{question || text({ en: "Your question appears here.", fr: "Votre question apparaît ici." })}</p>
        <div className="mt-3 flex flex-wrap items-center gap-2" role="radiogroup" aria-label={question || "Rating"}>
          {values.map((n) => (
            <label key={n} className="grid size-11 cursor-pointer place-items-center rounded-full border border-[#d9d9df] text-[14px] font-semibold text-[#0b1e4b] transition hover:border-[#1d4ed8] has-checked:border-[#1d4ed8] has-checked:bg-[#eef4ff]">
              <input type="radio" name="sv-rating-preview" value={n} className="sr-only" />
              {n}
            </label>
          ))}
        </div>
        <div className="mt-2 flex items-center justify-between text-[12px] text-[#6d6d70]">
          <span>{lowLabel || `1`}</span>
          {neutralLabel ? <span>{neutralLabel}</span> : <span aria-hidden="true" />}
          <span>{highLabel || `${values.length}`}</span>
        </div>
      </PreviewBox>
    </div>
  );
}

function TextBody({ text, custom, onPatch }: BuilderProps) {
  const question = (custom.question as string) ?? "";
  const placeholder = (custom.placeholder as string) ?? "";
  const mode = (custom.response_mode as string) ?? "short";
  const maxLength = clampMaxLength(custom.max_length);
  const required = (custom.require_answer as boolean) ?? true;
  const [draft, setDraft] = useState("");

  return (
    <div className="grid min-w-0 gap-5">
      <QuestionField text={text} question={question} onPatch={onPatch} />
      <Section labelledBy="sv-len-h" title={text({ en: "Answer setup", fr: "Réponse" })}>
        <Segmented
          name="sv-mode"
          value={mode}
          onChange={(value) => onPatch({ response_mode: value })}
          options={[
            { value: "short", title: text({ en: "Short answer", fr: "Réponse courte" }), body: text({ en: "One line.", fr: "Une ligne." }) },
            { value: "long", title: text({ en: "Long answer", fr: "Réponse longue" }), body: text({ en: "Several lines.", fr: "Plusieurs lignes." }) },
          ]}
        />
        <label className="grid gap-1.5 text-[13.5px] font-semibold text-[#0b1e4b]" htmlFor="sv-placeholder">
          {text({ en: "Placeholder (optional)", fr: "Exemple (facultatif)" })}
        </label>
        <input
          id="sv-placeholder"
          value={placeholder}
          onChange={(e) => onPatch({ placeholder: e.target.value })}
          placeholder={text({ en: "e.g. Type your answer…", fr: "ex. Écrivez votre réponse…" })}
          maxLength={120}
          className={`${inputCls} font-normal`}
        />
        <label className="grid gap-1.5 text-[13.5px] font-semibold text-[#0b1e4b]" htmlFor="sv-maxlen">
          {text({ en: `Max characters (${maxLength})`, fr: `Caractères max (${maxLength})` })}
        </label>
        <input
          id="sv-maxlen"
          type="number"
          min={50}
          max={5000}
          step={50}
          value={maxLength}
          onChange={(e) => onPatch({ max_length: clampMaxLength(Number(e.target.value)) })}
          className={inputCls}
        />
        <p className="text-[12px] text-[#6d6d70]">{text({ en: "Kept between 50 and 5,000 characters.", fr: "Compris entre 50 et 5 000 caractères." })}</p>
      </Section>
      <Section labelledBy="sv-behav-h" title={text({ en: "Behaviour", fr: "Comportement" })}>
        <Toggle checked={required} onChange={(v) => onPatch({ require_answer: v })} label={text({ en: "Answer required", fr: "Réponse obligatoire" })} />
      </Section>
      <PreviewBox title={text({ en: "Participant preview", fr: "Aperçu participant" })}>
        <p className="text-[14px] font-semibold text-[#0b1e4b]">{question || text({ en: "Your question appears here.", fr: "Votre question apparaît ici." })}</p>
        <div className="mt-3">
          {mode === "long" ? (
            <textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value.slice(0, maxLength))}
              placeholder={placeholder || text({ en: "Type your answer…", fr: "Écrivez votre réponse…" })}
              rows={4}
              aria-label={text({ en: "Your answer", fr: "Votre réponse" })}
              className={areaCls}
            />
          ) : (
            <input
              value={draft}
              onChange={(e) => setDraft(e.target.value.slice(0, maxLength))}
              placeholder={placeholder || text({ en: "Type your answer…", fr: "Écrivez votre réponse…" })}
              aria-label={text({ en: "Your answer", fr: "Votre réponse" })}
              maxLength={maxLength}
              className={inputCls}
            />
          )}
          <p className="mt-1.5 text-right text-[12px] text-[#6d6d70]" aria-live="polite">{draft.length}/{maxLength}</p>
        </div>
      </PreviewBox>
    </div>
  );
}

function RankingBody({ text, custom, onPatch }: BuilderProps) {
  const question = (custom.question as string) ?? "";
  const items = (custom.options as string[]) ?? ["", ""];
  const randomize = (custom.randomize as boolean) ?? false;
  const requireFull = (custom.require_full_ranking as boolean) ?? true;
  const filled = filledValues(items);
  const optErr = optionsError(items, 2);

  return (
    <div className="grid min-w-0 gap-5">
      <QuestionField text={text} question={question} onPatch={onPatch} />
      <Section
        labelledBy="sv-items-h"
        title={text({ en: "Items to rank", fr: "Éléments à classer" })}
        hint={text({ en: "Need at least two filled items. Reorder with the arrow buttons (keyboard accessible).", fr: "Au moins deux éléments remplis. Réordonnez avec les flèches (accessibles au clavier)." })}
      >
        <OrderedOptions
          items={items}
          onChange={(next) => onPatch({ options: next, item_count: next.length })}
          itemLabel={text({ en: "Item", fr: "Élément" })}
          addLabel={text({ en: "Add item", fr: "Ajouter un élément" })}
          min={2}
        />
        {optErr && <FieldError>{text({ en: "Fill in at least two items.", fr: "Renseignez au moins deux éléments." })}</FieldError>}
      </Section>
      <Section labelledBy="sv-behav-h" title={text({ en: "Behaviour", fr: "Comportement" })}>
        <Toggle checked={randomize} onChange={(v) => onPatch({ randomize: v })} label={text({ en: "Randomize starting order", fr: "Ordre de départ aléatoire" })} />
        <Toggle
          checked={requireFull}
          onChange={(v) => onPatch({ require_full_ranking: v })}
          label={text({ en: "Require a complete ranking", fr: "Exiger un classement complet" })}
          hint={text({ en: "Testers must order every item.", fr: "Les testeurs classent chaque élément." })}
        />
      </Section>
      <PreviewBox title={text({ en: "Participant preview", fr: "Aperçu participant" })}>
        <p className="text-[14px] font-semibold text-[#0b1e4b]">{question || text({ en: "Your question appears here.", fr: "Votre question apparaît ici." })}</p>
        {filled.length === 0 ? (
          <p className="mt-3 text-[13px] text-[#6d6d70]">{text({ en: "Items appear once you fill them in.", fr: "Les éléments apparaissent une fois renseignés." })}</p>
        ) : (
          <ol className="mt-3 grid gap-2">
            {filled.map((item, i) => (
              <li key={i} className="flex items-center gap-3 rounded-xl border border-[#e8e8ec] px-3 py-2.5">
                <span aria-hidden="true" className="grid size-7 shrink-0 place-items-center rounded-full bg-[#1d4ed8] text-[12px] font-bold text-white">{i + 1}</span>
                <span className="text-[13.5px] text-[#0b1e4b]">{item}</span>
              </li>
            ))}
          </ol>
        )}
      </PreviewBox>
    </div>
  );
}

function ConstantSumBody({ text, custom, onPatch }: BuilderProps) {
  const question = (custom.question as string) ?? "";
  const options = (custom.options as string[]) ?? ["", ""];
  const total = allocationTotal(custom.total_points);
  const required = (custom.require_answer as boolean) ?? true;
  const rawAlloc = Array.isArray(custom.trial_allocation) ? (custom.trial_allocation as number[]) : [];
  const alloc = options.map((_, i) => (typeof rawAlloc[i] === "number" && rawAlloc[i] >= 0 ? Math.floor(rawAlloc[i]) : 0));
  const filled = filledValues(options);
  const sum = allocatedSum(alloc);
  const remaining = total - sum;
  const err = constantSumError(alloc, total, filled.length);
  const optErr = optionsError(options, 2);

  const setAlloc = (index: number, value: number) => {
    const next = alloc.map((v, j) => (j === index ? Math.max(0, Math.floor(Number(value) || 0)) : v));
    onPatch({ trial_allocation: next });
  };

  return (
    <div className="grid min-w-0 gap-5">
      <QuestionField text={text} question={question} onPatch={onPatch} />
      <Section
        labelledBy="sv-opt-h"
        title={text({ en: "Answer options", fr: "Options de réponse" })}
        hint={text({ en: `Testers split ${total} points.`, fr: `Les testeurs répartissent ${total} points.` })}
      >
        <OrderedOptions
          items={options}
          onChange={(next) => onPatch({ options: next, option_count: next.length })}
          itemLabel={text({ en: "Option", fr: "Option" })}
          addLabel={text({ en: "Add option", fr: "Ajouter une option" })}
          min={2}
        />
        {optErr && <FieldError>{text({ en: "Fill in at least two answers.", fr: "Renseignez au moins deux réponses." })}</FieldError>}
      </Section>
      <Section labelledBy="sv-pts-h" title={text({ en: "Points setup", fr: "Points" })}>
        <Segmented
          name="sv-points"
          value={String(total)}
          onChange={(value) => onPatch({ total_points: value })}
          options={[
            { value: "100", title: "100 points" },
            { value: "10", title: "10 points" },
          ]}
        />
        <fieldset>
          <legend className="text-[13.5px] font-semibold text-[#0b1e4b]">{text({ en: "Trial allocation (checks your setup)", fr: "Répartition d’essai (vérifie votre réglage)" })}</legend>
          <div className="mt-2 grid gap-2">
            {filled.length === 0 && <p className="text-[13px] text-[#6d6d70]">{text({ en: "Fill in options to try the allocation.", fr: "Renseignez des options pour essayer." })}</p>}
            {filled.map((opt) => {
              const idx = options.indexOf(opt);
              return (
                <label key={`${opt}-${idx}`} className="flex items-center gap-3 rounded-xl border border-[#e8e8ec] px-3 py-2">
                  <span className="min-w-0 flex-1 truncate text-[13.5px] text-[#0b1e4b]">{opt}</span>
                  <input
                    type="number"
                    min={0}
                    max={total}
                    value={alloc[idx] ?? 0}
                    onChange={(e) => setAlloc(idx, Number(e.target.value))}
                    aria-label={text({ en: `Points for ${opt}`, fr: `Points pour ${opt}` })}
                    className="w-24 rounded-lg border border-[#d9d9df] px-3 py-2 text-[13.5px] focus:border-[#1d4ed8] focus:outline-none"
                  />
                </label>
              );
            })}
          </div>
        </fieldset>
        <p aria-live="polite" className={`rounded-xl px-4 py-3 text-[13px] font-semibold ${remaining === 0 ? "bg-[#eef4ff] text-[#0b1e4b]" : "bg-[#fef3f2] text-[#b42318]"}`}>
          {text({ en: `Allocated ${sum} of ${total} — ${remaining === 0 ? "balanced" : `${Math.abs(remaining)} ${remaining > 0 ? "left to assign" : "over the total"}`}.`, fr: `${sum} sur ${total} attribués — ${remaining === 0 ? "équilibré" : remaining > 0 ? `reste ${remaining}` : `${Math.abs(remaining)} en trop`}.` })}
        </p>
        {err === "sum-mismatch" && <FieldError>{text({ en: "The trial allocation must add up to the selected total.", fr: "La répartition d’essai doit égaler le total choisi." })}</FieldError>}
        {err === "negative-allocation" && <FieldError>{text({ en: "Allocations cannot be negative.", fr: "Les répartitions ne peuvent pas être négatives." })}</FieldError>}
      </Section>
      <Section labelledBy="sv-behav-h" title={text({ en: "Behaviour", fr: "Comportement" })}>
        <Toggle checked={required} onChange={(v) => onPatch({ require_answer: v })} label={text({ en: "Answer required", fr: "Réponse obligatoire" })} />
      </Section>
      <PreviewBox title={text({ en: "Participant preview", fr: "Aperçu participant" })}>
        <p className="text-[14px] font-semibold text-[#0b1e4b]">{question || text({ en: "Your question appears here.", fr: "Votre question apparaît ici." })}</p>
        <p className="mt-1 text-[12px] text-[#6d6d70]">{text({ en: `Split ${total} points.`, fr: `Répartissez ${total} points.` })}</p>
        <div className="mt-3 grid gap-2">
          {filled.map((opt, i) => (
            <div key={i} className="flex items-center gap-3 rounded-xl border border-[#e8e8ec] px-3 py-2">
              <span className="min-w-0 flex-1 truncate text-[13.5px] text-[#0b1e4b]">{opt}</span>
              <span className="w-24 rounded-lg bg-[#f7f9fc] px-3 py-2 text-right text-[13.5px] text-[#6d6d70]">0</span>
            </div>
          ))}
        </div>
      </PreviewBox>
    </div>
  );
}

export function SurveyBuilder(props: BuilderProps) {
  const kind = KIND[props.method] ?? KIND["survey.single"];
  void kind;
  switch (props.method) {
    case "survey.multi":
      return <MultiBody {...props} />;
    case "survey.rating":
      return <RatingBody {...props} />;
    case "survey.text":
      return <TextBody {...props} />;
    case "survey.ranking":
      return <RankingBody {...props} />;
    case "survey.constant_sum":
      return <ConstantSumBody {...props} />;
    case "survey.single":
    default:
      return <SingleBody {...props} />;
  }
}
