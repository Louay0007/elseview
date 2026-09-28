import { useEffect, useRef, useState } from "react";
import { ImagePlus, Timer, Trash2 } from "lucide-react";
import { FieldError, PreviewBox, Section, Toggle, areaCls, inputCls, type BuilderProps } from "./types";
import {
  IMAGE_TYPES,
  MB,
  formatBytes,
  isValidTarget,
  moveTarget,
  targetFromPoint,
  validateLocalFile,
  type NormTarget,
} from "./validation";

const IMAGE_MAX = 10 * MB;

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

function ImageField({ id, label, hint, file, error, onSelect, onClear, text }: {
  id: string;
  label: string;
  hint: string;
  file: File | null;
  error: string | null;
  onSelect: (file: File) => void;
  onClear: () => void;
  text: BuilderProps["text"];
}) {
  const url = useLocalUrl(file);
  return (
    <div>
      <p className="text-[13.5px] font-semibold text-[#0b1e4b]">{label}</p>
      <p className="mt-0.5 text-[12.5px] text-[#6d6d70]">{hint}</p>
      {file && url ? (
        <div className="mt-3 overflow-hidden rounded-xl border border-[#e8e8ec]">
          <img src={url} alt={text({ en: "Selected preview", fr: "Aperçu sélectionné" })} className="max-h-64 w-full object-contain bg-[#f7f9fc]" />
          <div className="flex flex-wrap items-center gap-2 px-4 py-3">
            <p className="min-w-0 flex-1 truncate text-[13px] font-medium text-[#0b1e4b]" title={file.name}>{file.name} <span className="font-normal text-[#6d6d70]">· {formatBytes(file.size)}</span></p>
            <label htmlFor={id} className="inline-flex min-h-[36px] cursor-pointer items-center rounded-full border border-[#d9d9df] px-4 text-[12.5px] font-semibold text-[#0b1e4b] hover:border-[#1d4ed8] hover:text-[#1d4ed8]">
              {text({ en: "Replace", fr: "Remplacer" })}
            </label>
            <button type="button" onClick={onClear} className="inline-flex min-h-[36px] items-center gap-1.5 rounded-full border border-[#e8e8ec] px-4 text-[12.5px] font-semibold text-[#6d6d70] hover:border-[#dc2626] hover:text-[#dc2626]">
              <Trash2 className="size-3.5" aria-hidden="true" /> {text({ en: "Remove", fr: "Supprimer" })}
            </button>
          </div>
        </div>
      ) : (
        <label htmlFor={id} className="mt-3 flex min-h-[120px] cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-[#d9d9df] bg-[#f7f9fc] px-4 text-center transition hover:border-[#1d4ed8]">
          <ImagePlus className="size-6 text-[#1d4ed8]" aria-hidden="true" />
          <span className="text-[13.5px] font-semibold text-[#0b1e4b]">{text({ en: "Drop an image here or click to browse", fr: "Déposez une image ou cliquez pour parcourir" })}</span>
          <span className="text-[12px] text-[#6d6d70]">PNG or JPG, {text({ en: "up to 10 MB", fr: "jusqu’à 10 Mo" })}</span>
        </label>
      )}
      <input
        id={id}
        type="file"
        accept="image/png,image/jpeg"
        className="sr-only"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) onSelect(f);
          e.target.value = "";
        }}
      />
      {error === "invalid-type" && <div className="mt-2"><FieldError>{text({ en: "That file type is not supported. Choose a PNG or JPG image.", fr: "Type non pris en charge. Choisissez une image PNG ou JPG." })}</FieldError></div>}
      {error === "too-large" && <div className="mt-2"><FieldError>{text({ en: "That file is over 10 MB. Compress it or pick a smaller image.", fr: "Fichier de plus de 10 Mo. Compressez-le ou choisissez une image plus légère." })}</FieldError></div>}
      <p className="mt-2 text-[12px] text-[#6d6d70]">{text({ en: "Kept in this browser for preview only — nothing is uploaded.", fr: "Conservé dans ce navigateur pour l’aperçu — rien n’est téléversé." })}</p>
    </div>
  );
}

export function FiveSecondBuilder({ text, custom, onPatch }: BuilderProps) {
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const recall = (custom.recall_question as boolean) ?? true;
  const recallText = (custom.recall_text as string) ?? "";
  const [stage, setStage] = useState<"exposure" | "recall">("exposure");
  const url = useLocalUrl(file);

  const select = (f: File) => {
    const err = validateLocalFile(f, IMAGE_TYPES, IMAGE_MAX);
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
        labelledBy="fs-asset-h"
        title={text({ en: "Show one image for 5 seconds", fr: "Montrez une image pendant 5 s" })}
        hint={text({ en: "Testers see it once, then it disappears.", fr: "Les testeurs la voient une fois, puis elle disparaît." })}
      >
        <p className="flex items-center gap-2 rounded-xl bg-[#eef4ff] px-4 py-3 text-[13px] font-semibold text-[#0b1e4b]">
          <Timer className="size-4 shrink-0 text-[#1d4ed8]" aria-hidden="true" />
          {text({ en: "Exposure is fixed at 5 seconds — it cannot be changed.", fr: "L’exposition est fixée à 5 secondes — non modifiable." })}
        </p>
        <ImageField
          id="fs-file"
          label={text({ en: "Image to show (5s)", fr: "Image à montrer (5 s)" })}
          hint={text({ en: "A single screen, poster or headline.", fr: "Un seul écran, affiche ou titre." })}
          file={file}
          error={fileError}
          onSelect={select}
          onClear={clear}
          text={text}
        />
      </Section>

      <Section
        labelledBy="fs-recall-h"
        title={text({ en: "Recall question", fr: "Question de mémoire" })}
        hint={text({ en: "Asked right after the image disappears.", fr: "Posée juste après la disparition de l’image." })}
      >
        <Toggle checked={recall} onChange={(v) => onPatch({ recall_question: v })} label={text({ en: "Ask what they remember", fr: "Demander ce qu’ils retiennent" })} />
        {recall && (
          <>
            <label className="grid gap-1.5 text-[13.5px] font-semibold text-[#0b1e4b]" htmlFor="fs-recall-text">
              {text({ en: "Recall prompt", fr: "Question de mémoire" })}
            </label>
            <textarea
              id="fs-recall-text"
              value={recallText}
              onChange={(e) => onPatch({ recall_text: e.target.value })}
              placeholder={text({ en: "What do you remember from what you just saw?", fr: "Que retenez-vous de ce que vous venez de voir ?" })}
              rows={2}
              aria-label={text({ en: "Recall prompt", fr: "Question de mémoire" })}
              className={areaCls}
            />
            {!recallText.trim() && <FieldError>{text({ en: "Add a recall question, or turn the recall step off.", fr: "Ajoutez une question, ou désactivez l’étape de mémoire." })}</FieldError>}
          </>
        )}
      </Section>

      <PreviewBox title={text({ en: "Participant preview", fr: "Aperçu participant" })}>
        <div className="flex gap-2" role="tablist" aria-label={text({ en: "Preview stage", fr: "Étape d’aperçu" })}>
          {(["exposure", "recall"] as const).map((s) => (
            <button
              key={s}
              type="button"
              role="tab"
              aria-selected={stage === s}
              onClick={() => setStage(s)}
              className={`min-h-[36px] rounded-full px-4 text-[12.5px] font-semibold ${stage === s ? "bg-[#1d4ed8] text-white" : "border border-[#d9d9df] text-[#0b1e4b] hover:border-[#1d4ed8]"}`}
            >
              {s === "exposure" ? text({ en: "Timed image (5s)", fr: "Image chronométrée (5 s)" }) : text({ en: "Recall", fr: "Mémoire" })}
            </button>
          ))}
        </div>
        {stage === "exposure" ? (
          <div className="mt-3">
            {url ? (
              <>
                <img src={url} alt={text({ en: "Timed preview", fr: "Aperçu chronométré" })} className="max-h-56 w-full rounded-lg object-contain bg-[#f7f9fc]" />
                <p className="mt-2 flex items-center gap-1.5 text-[12px] font-semibold text-[#0b1e4b]"><Timer className="size-3.5 text-[#1d4ed8]" aria-hidden="true" /> 0:05</p>
              </>
            ) : (
              <p className="rounded-lg bg-[#f7f9fc] px-4 py-8 text-center text-[13px] text-[#6d6d70]">{text({ en: "Upload an image to preview the 5-second exposure.", fr: "Téléversez une image pour prévisualiser l’exposition de 5 secondes." })}</p>
            )}
          </div>
        ) : (
          <div className="mt-3">
            <p className="text-[14px] font-semibold text-[#0b1e4b]">{recallText || text({ en: "Your recall question appears here.", fr: "Votre question apparaît ici." })}</p>
            <textarea aria-label={text({ en: "Participant recall answer", fr: "Réponse du participant" })} placeholder={text({ en: "Type what you remember…", fr: "Écrivez ce dont vous vous souvenez…" })} rows={3} className={`${areaCls} mt-2`} readOnly={false} />
          </div>
        )}
      </PreviewBox>
    </div>
  );
}

function TargetEditor({ imageUrl, fileName, target, onTarget, text }: {
  imageUrl: string | null;
  fileName: string;
  target: NormTarget | null;
  onTarget: (t: NormTarget | null) => void;
  text: BuilderProps["text"];
}) {
  const boxRef = useRef<HTMLDivElement>(null);
  const dragging = useRef(false);

  const pointFromEvent = (clientX: number, clientY: number): { x: number; y: number } | null => {
    const el = boxRef.current;
    if (!el) return null;
    const rect = el.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return null;
    const x = (clientX - rect.left) / rect.width;
    const y = (clientY - rect.top) / rect.height;
    if (x < 0 || x > 1 || y < 0 || y > 1) return null;
    return { x, y };
  };

  const place = (clientX: number, clientY: number) => {
    const p = pointFromEvent(clientX, clientY);
    if (!p) return;
    onTarget(targetFromPoint(p.x, p.y, target?.w ?? 0.24, target?.h ?? 0.18));
  };

  const nudge = (dx: number, dy: number) => {
    if (!target) return;
    onTarget(moveTarget(target, dx, dy));
  };

  if (!imageUrl) {
    return (
      <div className="grid place-items-center rounded-xl bg-[#f7f9fc] px-4 py-10 text-center">
        <p className="max-w-[40ch] text-[13.5px] leading-6 text-[#6d6d70]">
          {text({ en: "Upload a screenshot first — the clickable target area is drawn on it.", fr: "Téléversez d’abord une capture — la zone cliquable se dessine dessus." })}
        </p>
      </div>
    );
  }

  return (
    <div>
      <div
        ref={boxRef}
        role="application"
        aria-label={text({ en: "Click or drag on the screenshot to set the target area", fr: "Cliquez ou glissez sur la capture pour définir la zone cible" })}
        tabIndex={0}
        onKeyDown={(e) => {
          const step = e.shiftKey ? 0.05 : 0.01;
          if (e.key === "ArrowLeft") { e.preventDefault(); nudge(-step, 0); }
          else if (e.key === "ArrowRight") { e.preventDefault(); nudge(step, 0); }
          else if (e.key === "ArrowUp") { e.preventDefault(); nudge(0, -step); }
          else if (e.key === "ArrowDown") { e.preventDefault(); nudge(0, step); }
        }}
        onPointerDown={(e) => {
          (e.target as HTMLElement).setPointerCapture?.(e.pointerId);
          dragging.current = true;
          place(e.clientX, e.clientY);
        }}
        onPointerMove={(e) => {
          if (dragging.current) place(e.clientX, e.clientY);
        }}
        onPointerUp={() => { dragging.current = false; }}
        onPointerCancel={() => { dragging.current = false; }}
        className="relative cursor-crosshair touch-none overflow-hidden rounded-xl border border-[#e8e8ec] bg-[#f7f9fc] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1d4ed8]"
      >
        <img src={imageUrl} alt={fileName || text({ en: "Screenshot under test", fr: "Capture testée" })} className="max-h-80 w-full object-contain" draggable={false} />
        {target && (
          <div
            aria-hidden="true"
            className="pointer-events-none absolute rounded-md border-2 border-[#1d4ed8] bg-[#1d4ed8]/15 shadow-[0_0_0_2px_rgba(255,255,255,.7)]"
            style={{ left: `${target.x * 100}%`, top: `${target.y * 100}%`, width: `${target.w * 100}%`, height: `${target.h * 100}%` }}
          />
        )}
      </div>
      {target ? (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className="grid grid-cols-3 gap-1" role="group" aria-label={text({ en: "Nudge target", fr: "Ajuster la cible" })}>
            <span />
            <button type="button" onClick={() => nudge(0, -0.02)} aria-label={text({ en: "Move target up", fr: "Monter la cible" })} className="grid size-9 place-items-center rounded-lg border border-[#d9d9df] text-[#0b1e4b] hover:border-[#1d4ed8]">↑</button>
            <span />
            <button type="button" onClick={() => nudge(-0.02, 0)} aria-label={text({ en: "Move target left", fr: "Déplacer à gauche" })} className="grid size-9 place-items-center rounded-lg border border-[#d9d9df] text-[#0b1e4b] hover:border-[#1d4ed8]">←</button>
            <button type="button" onClick={() => nudge(0, 0.02)} aria-label={text({ en: "Move target down", fr: "Descendre la cible" })} className="grid size-9 place-items-center rounded-lg border border-[#d9d9df] text-[#0b1e4b] hover:border-[#1d4ed8]">↓</button>
            <button type="button" onClick={() => nudge(0.02, 0)} aria-label={text({ en: "Move target right", fr: "Déplacer à droite" })} className="grid size-9 place-items-center rounded-lg border border-[#d9d9df] text-[#0b1e4b] hover:border-[#1d4ed8]">→</button>
          </span>
          <label className="grid gap-1 text-[12px] font-semibold text-[#0b1e4b]">
            {text({ en: "Width %", fr: "Largeur %" })}
            <input type="number" min={5} max={100} value={Math.round(target.w * 100)} onChange={(e) => onTarget({ ...target, w: Math.min(1 - target.x, Math.max(0.05, Number(e.target.value) / 100)) })} className="w-20 rounded-lg border border-[#d9d9df] px-2 py-1.5 text-[13px]" />
          </label>
          <label className="grid gap-1 text-[12px] font-semibold text-[#0b1e4b]">
            {text({ en: "Height %", fr: "Hauteur %" })}
            <input type="number" min={5} max={100} value={Math.round(target.h * 100)} onChange={(e) => onTarget({ ...target, h: Math.min(1 - target.y, Math.max(0.05, Number(e.target.value) / 100)) })} className="w-20 rounded-lg border border-[#d9d9df] px-2 py-1.5 text-[13px]" />
          </label>
          <button type="button" onClick={() => onTarget(null)} className="inline-flex min-h-[36px] items-center gap-1.5 rounded-full border border-[#e8e8ec] px-4 text-[12.5px] font-semibold text-[#6d6d70] hover:border-[#dc2626] hover:text-[#dc2626]">
            <Trash2 className="size-3.5" aria-hidden="true" /> {text({ en: "Clear target", fr: "Effacer la cible" })}
          </button>
        </div>
      ) : (
        <p className="mt-2 text-[12.5px] text-[#6d6d70]">{text({ en: "Click on the screenshot to place the expected target area.", fr: "Cliquez sur la capture pour placer la zone cible attendue." })}</p>
      )}
    </div>
  );
}

export function FirstClickBuilder({ text, custom, onPatch }: BuilderProps) {
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const instruction = (custom.task_instruction as string) ?? "";
  const rawTarget = custom.target_area as unknown;
  const target = isValidTarget(rawTarget) ? rawTarget : null;
  const url = useLocalUrl(file);

  const select = (f: File) => {
    const err = validateLocalFile(f, IMAGE_TYPES, IMAGE_MAX);
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
    onPatch({ asset_note: "", asset_size: 0, asset_type: "", target_area: null });
  };

  return (
    <div className="grid min-w-0 gap-5">
      <Section
        labelledBy="fc-task-h"
        title={text({ en: "Write the task", fr: "Écrivez la tâche" })}
        hint={text({ en: "Testers click once on your screenshot. First click only.", fr: "Un seul clic sur votre capture. Premier clic uniquement." })}
      >
        <label className="grid gap-1.5 text-[13.5px] font-semibold text-[#0b1e4b]" htmlFor="fc-instruction">
          {text({ en: "Task prompt", fr: "Consigne" })}
        </label>
        <textarea
          id="fc-instruction"
          value={instruction}
          onChange={(e) => onPatch({ task_instruction: e.target.value })}
          placeholder={text({ en: "Where would you click to track your order?", fr: "Où cliqueriez-vous pour suivre votre commande ?" })}
          aria-label={text({ en: "Task prompt", fr: "Consigne" })}
          rows={3}
          className={areaCls}
        />
        {!instruction.trim() && <FieldError>{text({ en: "Add a task prompt before continuing.", fr: "Ajoutez une consigne pour continuer." })}</FieldError>}
      </Section>

      <Section labelledBy="fc-asset-h" title={text({ en: "Upload the screenshot", fr: "Téléversez la capture" })}>
        <ImageField
          id="fc-file"
          label={text({ en: "Screenshot to test", fr: "Capture à tester" })}
          hint={text({ en: "Full page at desktop or mobile size.", fr: "Page complète, taille bureau ou mobile." })}
          file={file}
          error={fileError}
          onSelect={select}
          onClear={clear}
          text={text}
        />
      </Section>

      <Section
        labelledBy="fc-target-h"
        title={text({ en: "Mark the expected target", fr: "Marquez la zone attendue" })}
        hint={text({ en: "Stored as relative positions, so it stays aligned when the image resizes.", fr: "Positions relatives : reste aligné quand l’image change de taille." })}
      >
        <TargetEditor
          imageUrl={url}
          fileName={file?.name ?? ""}
          target={target}
          onTarget={(t) => onPatch({ target_area: t })}
          text={text}
        />
        {url && !target && <div className="mt-2"><FieldError>{text({ en: "Place a target area to score first clicks.", fr: "Placez une zone cible pour noter les premiers clics." })}</FieldError></div>}
      </Section>

      <PreviewBox title={text({ en: "Participant preview", fr: "Aperçu participant" })}>
        {url ? (
          <>
            <p className="text-[14px] font-semibold text-[#0b1e4b]">{instruction || text({ en: "Your task appears here.", fr: "Votre consigne apparaît ici." })}</p>
            <div className="relative mt-3 overflow-hidden rounded-lg border border-[#e8e8ec]">
              <img src={url} alt={text({ en: "Screenshot preview", fr: "Aperçu de la capture" })} className="max-h-56 w-full object-contain bg-[#f7f9fc]" />
              {target && (
                <div
                  aria-hidden="true"
                  className="pointer-events-none absolute rounded-md border-2 border-[#1d4ed8] bg-[#1d4ed8]/15"
                  style={{ left: `${target.x * 100}%`, top: `${target.y * 100}%`, width: `${target.w * 100}%`, height: `${target.h * 100}%` }}
                />
              )}
            </div>
            <input aria-label={text({ en: "Follow-up note (optional)", fr: "Note de suivi (facultative)" })} placeholder={text({ en: "Why did you click there? (optional)", fr: "Pourquoi avez-vous cliqué là ? (facultatif)" })} className={`${inputCls} mt-3 font-normal`} />
          </>
        ) : (
          <p className="rounded-lg bg-[#f7f9fc] px-4 py-8 text-center text-[13px] text-[#6d6d70]">{text({ en: "Upload a screenshot to preview the first-click task.", fr: "Téléversez une capture pour prévisualiser la tâche." })}</p>
        )}
      </PreviewBox>
    </div>
  );
}
