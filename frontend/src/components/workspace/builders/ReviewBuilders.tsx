import { useEffect, useState } from "react";
import { FileAudio, FileVideo, Globe, Trash2 } from "lucide-react";
import { FieldError, PreviewBox, Section, Segmented, Toggle, areaCls, inputCls, type BuilderProps } from "./types";
import { AUDIO_TYPES, MB, VIDEO_TYPES, formatBytes, validateLocalFile } from "./validation";

const ISSUE_CATEGORIES = [
  { value: "vision", en: "Vision & contrast", fr: "Vision et contraste" },
  { value: "keyboard", en: "Keyboard", fr: "Clavier" },
  { value: "screen_reader", en: "Screen reader", fr: "Lecteur d’écran" },
  { value: "navigation", en: "Navigation", fr: "Navigation" },
  { value: "content", en: "Content & language", fr: "Contenu et langue" },
  { value: "other", en: "Other", fr: "Autre" },
] as const;

const REVIEW_FOCI = [
  { value: "clarity", en: "Clarity", fr: "Clarté" },
  { value: "tone", en: "Tone", fr: "Ton" },
  { value: "trust", en: "Trust", fr: "Confiance" },
  { value: "inclusivity", en: "Inclusivity", fr: "Inclusivité" },
  { value: "grammar", en: "Grammar & translation", fr: "Grammaire et traduction" },
] as const;

const LOCALES = [
  { value: "fr", title: "Français" },
  { value: "ar", title: "العربية" },
  { value: "en", title: "English" },
] as const;

function useLocalUrl(file: File | null): string | null {
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    if (!file) {
      setUrl(null);
      return;
    }
    const next = URL.createObjectURL(file);
    setUrl(next);
    return () => URL.revokeObjectURL(next);
  }, [file]);
  return url;
}

function CheckList({ legend, options, selected, onToggle, text }: {
  legend: string;
  options: readonly { value: string; en: string; fr: string }[];
  selected: string[];
  onToggle: (value: string) => void;
  text: BuilderProps["text"];
}) {
  return (
    <fieldset>
      <legend className="text-[13.5px] font-semibold text-[#0b1e4b]">{legend}</legend>
      <div className="mt-2 flex flex-wrap gap-2">
        {options.map((opt) => {
          const active = selected.includes(opt.value);
          return (
            <label
              key={opt.value}
              className={`inline-flex min-h-[44px] cursor-pointer items-center gap-2 rounded-full border px-4 text-[13px] font-semibold transition ${active ? "border-[#1d4ed8] bg-[#eef4ff] text-[#0b1e4b]" : "border-[#d9d9df] text-[#52525b] hover:border-[#1d4ed8]/60"}`}
            >
              <input
                type="checkbox"
                checked={active}
                onChange={() => onToggle(opt.value)}
                className="size-4 accent-[#1d4ed8]"
              />
              {text({ en: opt.en, fr: opt.fr })}
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}

export function AccessibilityBuilder({ text, custom, onPatch }: BuilderProps) {
  const task = (custom.task_instruction as string) ?? "";
  const pageUrl = (custom.page_url as string) ?? "";
  const categories = Array.isArray(custom.issue_categories) ? (custom.issue_categories as string[]) : [];
  const severity = (custom.severity as string | null) ?? null;
  const allowScreenshot = (custom.include_screenshot as boolean) ?? false;
  const urlInvalid = pageUrl.trim().length > 0 && !/^https?:\/\/.+\..+/.test(pageUrl.trim());

  const toggleCategory = (value: string) => {
    onPatch({ issue_categories: categories.includes(value) ? categories.filter((c) => c !== value) : [...categories, value] });
  };

  return (
    <div className="grid min-w-0 gap-5">
      <Section
        labelledBy="ax-task-h"
        title={text({ en: "Task & instructions", fr: "Tâche et consignes" })}
        hint={text({ en: "People describe what blocks them in their own words. This is not an automated audit.", fr: "Les gens décrivent ce qui les bloque avec leurs mots. Ceci n’est pas un audit automatisé." })}
      >
        <label className="grid gap-1.5 text-[13.5px] font-semibold text-[#0b1e4b]" htmlFor="ax-task">
          {text({ en: "What should testers try to do?", fr: "Qu’est-ce que les testeurs doivent essayer ?" })}
        </label>
        <textarea
          id="ax-task"
          value={task}
          onChange={(e) => onPatch({ task_instruction: e.target.value })}
          placeholder={text({ en: "e.g. Complete checkout using only your keyboard, and report anything that blocks you.", fr: "ex. Finalisez l’achat uniquement au clavier, et signalez tout ce qui vous bloque." })}
          rows={3}
          className={areaCls}
        />
        {!task.trim() && <FieldError>{text({ en: "Add clear instructions before continuing.", fr: "Ajoutez des consignes claires pour continuer." })}</FieldError>}
        <label className="grid gap-1.5 text-[13.5px] font-semibold text-[#0b1e4b]" htmlFor="ax-url">
          {text({ en: "Page URL (optional)", fr: "URL de la page (facultatif)" })}
        </label>
        <input
          id="ax-url"
          value={pageUrl}
          onChange={(e) => onPatch({ page_url: e.target.value })}
          placeholder="https://…"
          inputMode="url"
          aria-invalid={urlInvalid ? true : undefined}
          className={`${inputCls} font-normal`}
        />
        {urlInvalid && <FieldError>{text({ en: "Enter a full URL starting with http(s)://, or leave it empty.", fr: "Saisissez une URL complète en http(s)://, ou laissez vide." })}</FieldError>}
      </Section>

      <Section
        labelledBy="ax-cat-h"
        title={text({ en: "Issue categories", fr: "Catégories de problèmes" })}
        hint={text({ en: "Testers pick what fits what they hit.", fr: "Les testeurs choisissent ce qui correspond à leur blocage." })}
      >
        <CheckList
          legend={text({ en: "Which kinds of problems can testers report?", fr: "Quels types de problèmes peuvent être signalés ?" })}
          options={ISSUE_CATEGORIES}
          selected={categories}
          onToggle={toggleCategory}
          text={text}
        />
        {categories.length === 0 && <FieldError>{text({ en: "Select at least one category.", fr: "Sélectionnez au moins une catégorie." })}</FieldError>}
      </Section>

      <Section labelledBy="ax-sev-h" title={text({ en: "Severity & evidence", fr: "Gravité et preuves" })}>
        <fieldset>
          <legend className="text-[13.5px] font-semibold text-[#0b1e4b]">{text({ en: "Severity scale (testers choose one)", fr: "Échelle de gravité (les testeurs en choisissent une)" })}</legend>
          <div className="mt-2 grid gap-2 sm:grid-cols-2" role="radiogroup" aria-label={text({ en: "Severity", fr: "Gravité" })}>
            {[
              { value: "blocks", en: "Blocks me", fr: "Me bloque" },
              { value: "major", en: "Major friction", fr: "Gêne importante" },
              { value: "minor", en: "Minor annoyance", fr: "Gêne mineure" },
              { value: "suggestion", en: "Suggestion", fr: "Suggestion" },
            ].map((opt) => (
              <label key={opt.value} className={`flex min-h-[48px] cursor-pointer items-center gap-2.5 rounded-xl border px-3 text-[13.5px] transition ${severity === opt.value ? "border-[#1d4ed8] bg-[#eef4ff] font-semibold text-[#0b1e4b]" : "border-[#e8e8ec] text-[#52525b] hover:border-[#1d4ed8]/50"}`}>
                <input type="radio" name="ax-severity" checked={severity === opt.value} onChange={() => onPatch({ severity: opt.value })} className="size-4 accent-[#1d4ed8]" />
                {text({ en: opt.en, fr: opt.fr })}
              </label>
            ))}
          </div>
          {severity && (
            <button type="button" onClick={() => onPatch({ severity: null })} className="mt-2 text-[12.5px] font-medium text-[#1d4ed8] hover:underline">
              {text({ en: "Clear default severity", fr: "Effacer la gravité par défaut" })}
            </button>
          )}
        </fieldset>
        <Toggle
          checked={allowScreenshot}
          onChange={(v) => onPatch({ include_screenshot: v })}
          label={text({ en: "Allow screenshot attachments", fr: "Autoriser les captures jointes" })}
          hint={text({ en: "Testers can attach what blocks them.", fr: "Les testeurs joignent ce qui bloque." })}
        />
      </Section>

      <PreviewBox title={text({ en: "Participant preview", fr: "Aperçu participant" })}>
        <p className="text-[14px] font-semibold text-[#0b1e4b]">{task || text({ en: "Your instructions appear here.", fr: "Vos consignes apparaissent ici." })}</p>
        {pageUrl.trim() && !urlInvalid && <p className="mt-1 break-all text-[12.5px] text-[#1d4ed8]">{pageUrl.trim()}</p>}
        <fieldset className="mt-3">
          <legend className="text-[12.5px] font-semibold text-[#0b1e4b]">{text({ en: "What blocked you?", fr: "Qu’est-ce qui vous a bloqué ?" })}</legend>
          <div className="mt-2 flex flex-wrap gap-2">
            {(categories.length > 0 ? ISSUE_CATEGORIES.filter((c) => categories.includes(c.value)) : ISSUE_CATEGORIES).map((c) => (
              <label key={c.value} className="inline-flex min-h-[40px] cursor-pointer items-center gap-2 rounded-full border border-[#d9d9df] px-3.5 text-[12.5px] text-[#0b1e4b] hover:border-[#1d4ed8]">
                <input type="checkbox" className="size-4 accent-[#1d4ed8]" />
                {text({ en: c.en, fr: c.fr })}
              </label>
            ))}
          </div>
        </fieldset>
        <textarea aria-label={text({ en: "Describe the problem", fr: "Décrivez le problème" })} placeholder={text({ en: "Describe what happened…", fr: "Décrivez ce qui s’est passé…" })} rows={3} className={`${areaCls} mt-3`} />
        {allowScreenshot && (
          <p className="mt-2 rounded-lg bg-[#f7f9fc] px-3 py-2 text-[12px] text-[#6d6d70]">{text({ en: "Testers may attach a screenshot of the blocker.", fr: "Les testeurs peuvent joindre une capture du blocage." })}</p>
        )}
      </PreviewBox>
    </div>
  );
}

export function LanguageBuilder({ text, custom, onPatch }: BuilderProps) {
  const source = (custom.source_text as string) ?? "";
  const locale = (custom.target_locale as string | null) ?? null;
  const foci = Array.isArray(custom.review_focus) ? (custom.review_focus as string[]) : [];
  const audience = (custom.audience_context as string) ?? "";

  const toggleFocus = (value: string) => {
    onPatch({ review_focus: foci.includes(value) ? foci.filter((f) => f !== value) : [...foci, value] });
  };

  return (
    <div className="grid min-w-0 gap-5">
      <Section
        labelledBy="lg-src-h"
        title={text({ en: "Paste the exact text", fr: "Collez le texte exact" })}
        hint={text({ en: "Reviewers see this wording character for character.", fr: "Les relecteurs voient ce texte à la lettre près." })}
      >
        <p className="flex items-center gap-2 text-[12.5px] text-[#6d6d70]"><Globe className="size-4 shrink-0 text-[#1d4ed8]" aria-hidden="true" />{text({ en: "Keep formatting and line breaks identical to production.", fr: "Gardez la mise en forme identique à la production." })}</p>
        <label className="grid gap-1.5 text-[13.5px] font-semibold text-[#0b1e4b]" htmlFor="lg-source">
          {text({ en: "Source text", fr: "Texte source" })}
        </label>
        <textarea
          id="lg-source"
          value={source}
          onChange={(e) => onPatch({ source_text: e.target.value })}
          rows={5}
          placeholder={text({ en: "Paste the exact text…", fr: "Collez le texte exact…" })}
          aria-label={text({ en: "Source text", fr: "Texte source" })}
          className={areaCls}
        />
        {!source.trim() && <FieldError>{text({ en: "Paste the text to review before continuing.", fr: "Collez le texte à relire pour continuer." })}</FieldError>}
      </Section>

      <Section labelledBy="lg-lang-h" title={text({ en: "Review language", fr: "Langue relue" })}>
        <div className="grid gap-2 sm:grid-cols-3" role="radiogroup" aria-label={text({ en: "Review language", fr: "Langue relue" })}>
          {LOCALES.map((opt) => (
            <label key={opt.value} className={`flex min-h-[48px] cursor-pointer items-center justify-center gap-2 rounded-xl border px-3 text-[13.5px] transition ${locale === opt.value ? "border-[#1d4ed8] bg-[#eef4ff] font-semibold text-[#0b1e4b]" : "border-[#e8e8ec] text-[#52525b] hover:border-[#1d4ed8]/50"}`}>
              <input type="radio" name="lg-locale" checked={locale === opt.value} onChange={() => onPatch({ target_locale: opt.value })} className="size-4 accent-[#1d4ed8]" />
              <span lang={opt.value}>{opt.title}</span>
            </label>
          ))}
        </div>
        {!locale && <FieldError>{text({ en: "Choose the language under review.", fr: "Choisissez la langue à relire." })}</FieldError>}
        <CheckList
          legend={text({ en: "Review focus (optional)", fr: "Axes de relecture (facultatif)" })}
          options={REVIEW_FOCI}
          selected={foci}
          onToggle={toggleFocus}
          text={text}
        />
        <label className="grid gap-1.5 text-[13.5px] font-semibold text-[#0b1e4b]" htmlFor="lg-audience">
          {text({ en: "Audience / context (optional)", fr: "Public / contexte (facultatif)" })}
        </label>
        <input
          id="lg-audience"
          value={audience}
          onChange={(e) => onPatch({ audience_context: e.target.value })}
          placeholder={text({ en: "e.g. New customers on the pricing page", fr: "ex. Nouveaux clients sur la page tarifs" })}
          maxLength={140}
          className={`${inputCls} font-normal`}
        />
      </Section>

      <PreviewBox title={text({ en: "Participant preview", fr: "Aperçu participant" })} rtl={locale === "ar"}>
        {source.trim() ? (
          <blockquote lang={locale ?? undefined} className="whitespace-pre-wrap border-l-2 border-[#1d4ed8] pl-3 text-[14px] leading-7 text-[#0b1e4b]">
            {source}
          </blockquote>
        ) : (
          <p className="text-[13px] text-[#6d6d70]">{text({ en: "Your exact copy appears here, line breaks preserved.", fr: "Votre texte exact apparaît ici, sauts de ligne conservés." })}</p>
        )}
        {foci.length > 0 && (
          <p className="mt-3 text-[12px] text-[#6d6d70]">
            {text({ en: "Focus: ", fr: "Axes : " })}
            {foci.map((f) => REVIEW_FOCI.find((r) => r.value === f)).filter(Boolean).map((f) => text({ en: f!.en, fr: f!.fr })).join(" · ")}
          </p>
        )}
        <div className="mt-3 flex flex-wrap gap-2">
          {[text({ en: "Clear", fr: "Clair" }), text({ en: "Confusing", fr: "Confus" }), text({ en: "Trustworthy", fr: "Fiable" })].map((label) => (
            <button key={label} type="button" className="min-h-[40px] rounded-full border border-[#d9d9df] px-4 text-[12.5px] font-semibold text-[#0b1e4b] hover:border-[#1d4ed8]">{label}</button>
          ))}
        </div>
        <textarea aria-label={text({ en: "Wording feedback", fr: "Commentaire sur le texte" })} placeholder={text({ en: "What would you change and why?", fr: "Que changeriez-vous et pourquoi ?" })} rows={2} className={`${areaCls} mt-3`} />
      </PreviewBox>
    </div>
  );
}

export function MediaBuilder({ text, custom, onPatch }: BuilderProps) {
  const mediaKind = (custom.media_kind as "audio" | "video" | null) ?? null;
  const followUp = (custom.followup_prompt as string) ?? "";
  const replays = typeof custom.replay_limit === "number" && Number.isFinite(custom.replay_limit)
    ? Math.min(10, Math.max(1, Math.floor(custom.replay_limit)))
    : 2;
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const url = useLocalUrl(file);

  const accepted = mediaKind === "audio" ? AUDIO_TYPES : mediaKind === "video" ? VIDEO_TYPES : [...VIDEO_TYPES, ...AUDIO_TYPES];
  const acceptAttr = mediaKind === "audio" ? "audio/mpeg,audio/wav,audio/mp4" : mediaKind === "video" ? "video/mp4,video/webm" : "video/mp4,video/webm,audio/mpeg,audio/wav,audio/mp4";
  const maxBytes = 200 * MB;
  const isAudio = mediaKind === "audio" || (file != null && file.type.startsWith("audio"));

  const select = (f: File) => {
    const err = validateLocalFile(f, accepted, maxBytes);
    if (err) {
      setFileError(err);
      return;
    }
    setFileError(null);
    setFile(f);
    onPatch({ asset_note: f.name, asset_size: f.size, asset_type: f.type });
  };
  const clear = () => {
    setFile(null);
    setFileError(null);
    onPatch({ asset_note: "", asset_size: 0, asset_type: "" });
  };

  return (
    <div className="grid min-w-0 gap-5">
      <Section
        labelledBy="md-type-h"
        title={text({ en: "What will testers watch or hear?", fr: "Que verront ou entendront les testeurs ?" })}
      >
        <Segmented
          name="md-kind"
          value={mediaKind}
          onChange={(value) => {
            setFile(null);
            setFileError(null);
            onPatch({ media_kind: value, asset_note: "", asset_size: 0, asset_type: "" });
          }}
          options={[
            { value: "video", title: text({ en: "Video", fr: "Vidéo" }), body: "MP4, WebM" },
            { value: "audio", title: text({ en: "Audio", fr: "Audio" }), body: "MP3, WAV, M4A" },
          ]}
        />
        {!mediaKind && <FieldError>{text({ en: "Choose audio or video first.", fr: "Choisissez d’abord audio ou vidéo." })}</FieldError>}
      </Section>

      <Section
        labelledBy="md-file-h"
        title={text({ en: "Media file", fr: "Fichier média" })}
        hint={mediaKind
          ? text({ en: mediaKind === "audio" ? "MP3, WAV or M4A, up to 200 MB." : "MP4 or WebM, up to 200 MB.", fr: mediaKind === "audio" ? "MP3, WAV ou M4A, jusqu’à 200 Mo." : "MP4 ou WebM, jusqu’à 200 Mo." })
          : text({ en: "Pick a media kind above to see accepted formats.", fr: "Choisissez un type ci-dessus pour voir les formats." })}
      >
        {file && url ? (
          <div className="overflow-hidden rounded-xl border border-[#e8e8ec]">
            {isAudio ? (
              <audio src={url} controls className="w-full" aria-label={text({ en: "Audio preview", fr: "Aperçu audio" })} />
            ) : (
              <video src={url} controls playsInline className="max-h-64 w-full bg-black" aria-label={text({ en: "Video preview", fr: "Aperçu vidéo" })} />
            )}
            <div className="flex flex-wrap items-center gap-2 px-4 py-3">
              <p className="min-w-0 flex-1 truncate text-[13px] font-medium text-[#0b1e4b]" title={file.name}>{file.name} <span className="font-normal text-[#6d6d70]">· {formatBytes(file.size)}</span></p>
              <label htmlFor="md-file" className="inline-flex min-h-[36px] cursor-pointer items-center rounded-full border border-[#d9d9df] px-4 text-[12.5px] font-semibold text-[#0b1e4b] hover:border-[#1d4ed8] hover:text-[#1d4ed8]">
                {text({ en: "Replace", fr: "Remplacer" })}
              </label>
              <button type="button" onClick={clear} className="inline-flex min-h-[36px] items-center gap-1.5 rounded-full border border-[#e8e8ec] px-4 text-[12.5px] font-semibold text-[#6d6d70] hover:border-[#dc2626] hover:text-[#dc2626]">
                <Trash2 className="size-3.5" aria-hidden="true" /> {text({ en: "Remove", fr: "Supprimer" })}
              </button>
            </div>
          </div>
        ) : (
          <label htmlFor="md-file" className={`flex min-h-[120px] flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-[#d9d9df] bg-[#f7f9fc] px-4 text-center transition ${mediaKind ? "cursor-pointer hover:border-[#1d4ed8]" : "cursor-not-allowed opacity-50"}`}>
            {isAudio || mediaKind === "audio"
              ? <FileAudio className="size-6 text-[#1d4ed8]" aria-hidden="true" />
              : <FileVideo className="size-6 text-[#1d4ed8]" aria-hidden="true" />}
            <span className="text-[13.5px] font-semibold text-[#0b1e4b]">{text({ en: "Drop your file here or click to browse", fr: "Déposez votre fichier ou cliquez pour parcourir" })}</span>
            <span className="text-[12px] text-[#6d6d70]">{mediaKind ? (mediaKind === "audio" ? "MP3, WAV, M4A · ≤ 200 MB" : "MP4, WebM · ≤ 200 MB") : text({ en: "Choose audio or video above", fr: "Choisissez audio ou vidéo ci-dessus" })}</span>
          </label>
        )}
        <input
          id="md-file"
          type="file"
          accept={acceptAttr}
          disabled={!mediaKind}
          className="sr-only"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) {
              if (!mediaKind) { setFileError("invalid-type"); }
              else select(f);
            }
            e.target.value = "";
          }}
        />
        {fileError === "invalid-type" && <div className="mt-2"><FieldError>{text({ en: "That file type is not accepted for this media kind. Pick a listed format.", fr: "Type non accepté pour ce média. Choisissez un format listé." })}</FieldError></div>}
        {fileError === "too-large" && <div className="mt-2"><FieldError>{text({ en: "That file is over 200 MB. Compress it or pick a shorter clip.", fr: "Fichier de plus de 200 Mo. Compressez-le ou choisissez un extrait plus court." })}</FieldError></div>}
        <p className="mt-2 text-[12px] text-[#6d6d70]">{text({ en: "Kept in this browser for preview only — nothing is uploaded.", fr: "Conservé dans ce navigateur pour l’aperçu — rien n’est téléversé." })}</p>
      </Section>

      <Section labelledBy="md-play-h" title={text({ en: "Playback & follow-up", fr: "Lecture et suivi" })}>
        <label className="grid gap-1.5 text-[13.5px] font-semibold text-[#0b1e4b]" htmlFor="md-replays">
          {text({ en: "Replays allowed (1–10)", fr: "Relectures autorisées (1–10)" })}
        </label>
        <input
          id="md-replays"
          type="number"
          min={1}
          max={10}
          value={replays}
          onChange={(e) => onPatch({ replay_limit: Math.min(10, Math.max(1, Math.floor(Number(e.target.value) || 1))) })}
          className={inputCls}
        />
        <label className="grid gap-1.5 text-[13.5px] font-semibold text-[#0b1e4b]" htmlFor="md-followup">
          {text({ en: "Follow-up prompt", fr: "Question de suivi" })}
        </label>
        <textarea
          id="md-followup"
          value={followUp}
          onChange={(e) => onPatch({ followup_prompt: e.target.value })}
          placeholder={text({ en: "e.g. What stood out most, and why?", fr: "ex. Qu’est-ce qui vous a le plus marqué, et pourquoi ?" })}
          rows={2}
          className={areaCls}
        />
        {!followUp.trim() && <FieldError>{text({ en: "Add a short follow-up prompt for after playback.", fr: "Ajoutez une courte question pour après la lecture." })}</FieldError>}
      </Section>

      <PreviewBox title={text({ en: "Participant preview", fr: "Aperçu participant" })}>
        {url ? (
          isAudio
            ? <audio src={url} controls className="w-full" aria-label={text({ en: "Participant audio", fr: "Audio du participant" })} />
            : <video src={url} controls playsInline className="max-h-56 w-full rounded-lg bg-black" aria-label={text({ en: "Participant video", fr: "Vidéo du participant" })} />
        ) : (
          <p className="rounded-lg bg-[#f7f9fc] px-4 py-8 text-center text-[13px] text-[#6d6d70]">{text({ en: "Choose a media kind and file to preview playback here.", fr: "Choisissez un type et un fichier pour prévisualiser la lecture." })}</p>
        )}
        <p className="mt-1 text-[12px] text-[#6d6d70]">{text({ en: `Up to ${replays} ${replays === 1 ? "replay" : "replays"}.`, fr: `Jusqu’à ${replays} relecture(s).` })}</p>
        <p className="mt-3 text-[14px] font-semibold text-[#0b1e4b]">{followUp || text({ en: "Your follow-up prompt appears here.", fr: "Votre question apparaît ici." })}</p>
        <textarea aria-label={text({ en: "Participant response", fr: "Réponse du participant" })} placeholder={text({ en: "Type your response…", fr: "Écrivez votre réponse…" })} rows={2} className={`${areaCls} mt-2`} />
      </PreviewBox>
    </div>
  );
}
