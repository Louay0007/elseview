import { useState } from "react";
import { useAuthLocale } from "@/components/auth/AuthLocale";
import { Checkbox } from "@/components/ui/checkbox";
import { ChevronDown, X } from "lucide-react";
import { cn } from "@/lib/utils";
import type { AboutOption } from "@/pages/auth/testerAbout";

/** A string with an English and French variant, as produced by `authWords`. */
type Localized = { en: string; fr: string };

export const fieldLabelClass = "flex items-center gap-1.5 text-[13px] font-semibold text-[#0F1E3D]";

/** Small star glyph marking a field the platform requires. */
export function RequiredMark() {
  return (
    <span aria-hidden="true" className="text-[13px] leading-none text-[#1E3A8A]">✳</span>
  );
}

export function FormField({ label, required, hint, error, children, className, htmlFor }: {
  label?: Localized;
  required?: boolean;
  hint?: Localized;
  error?: Localized;
  children: React.ReactNode;
  className?: string;
  htmlFor?: string;
}) {
  const { text } = useAuthLocale();
  return (
    <div className={cn("min-w-0", className)}>
      {label && <label htmlFor={htmlFor} className={fieldLabelClass}>{required ? <RequiredMark /> : null}{text(label)}</label>}
      <div className="mt-1.5">{children}</div>
      {hint && !error && <p className="mt-1.5 text-[12.5px] text-[#5A6B87]">{text(hint)}</p>}
      {error && <p role="alert" className="mt-1.5 text-[12.5px] text-[#d92d20]">{text(error)}</p>}
    </div>
  );
}

export const controlClass =
  "h-11 w-full rounded-lg border border-[#CDD9EC] bg-white px-3 text-[14.5px] text-[#0F1E3D] shadow-none outline-none transition placeholder:text-[#6E8098] hover:border-[#9FB2D0] focus:border-[#1E3A8A] focus:ring-2 focus:ring-[#1E3A8A]/25 disabled:cursor-not-allowed disabled:bg-[#F2F5FA] disabled:text-[#6E8098] disabled:hover:border-[#CDD9EC]";

/**
 * Single-answer dropdown. The visible label doubles as the disabled placeholder,
 * matching the mock, while the accessible name stays stable for screen readers.
 */
export function SelectField({ id, label, value, options, onChange, disabled, required, invalid, placeholder, className }: {
  id: string;
  label: Localized;
  value: string;
  options: AboutOption[];
  onChange: (value: string) => void;
  disabled?: boolean;
  required?: boolean;
  invalid?: boolean;
  placeholder?: Localized;
  className?: string;
}) {
  const { text } = useAuthLocale();
  // A stored value with no matching option means the option list changed since
  // the tester answered. Showing the raw slug would read as a bug, so fall back
  // to the field label and let them re-pick.
  const matched = options.find((o) => o.value === value);
  const display = matched ? text(matched.label) : value === "" ? text(placeholder ?? label) : text(placeholder ?? label);
  return (
    <FormField label={label} required={required} htmlFor={id} className={className}>
      <div className="relative">
        <select
          id={id}
          name={id}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          disabled={disabled}
          required={required}
          aria-invalid={invalid || undefined}
          // The select's own option text is hidden so it cannot render on top
          // of the label overlay below; the overlay carries the visible value.
          className={cn(controlClass, "appearance-none pr-9 text-left text-transparent", invalid && "border-[#d92d20]")}
        >
          <option value="" disabled>{text(placeholder ?? label)}</option>
          {options.map((option) => (
            <option key={option.value} value={option.value} className="text-[#0F1E3D]">{text(option.label)}</option>
          ))}
        </select>
        <span
          className={cn(
            "pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 truncate pr-1 text-[14.5px]",
            disabled ? "text-[#6E8098]" : value === "" ? "text-[#6E8098]" : "text-[#0F1E3D]",
          )}
          aria-hidden="true"
        >
          {display}
        </span>
        <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 size-4 -translate-y-1/2 text-[#64748B]" aria-hidden="true" />
      </div>
    </FormField>
  );
}

/** A removable value chip, in the same light blue as the section surfaces. */
function Chip({ label, onRemove }: { label: string; onRemove: () => void }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-[#E3EBFA] py-1 pl-2.5 pr-1 text-[13px] text-[#0F1E3D]">
      <span className="max-w-[180px] truncate">{label}</span>
      <button
        type="button"
        onClick={onRemove}
        className="grid size-5 place-items-center rounded-full bg-[#1E3A8A] text-white transition hover:bg-[#0F1E3D] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1E3A8A] focus-visible:ring-offset-1"
      >
        <X className="size-3" strokeWidth={2.6} aria-hidden="true" />
        <span className="sr-only">Remove {label}</span>
      </button>
    </span>
  );
}

/**
 * Multi-select rendered as removable chips above a dropdown that adds new values,
 * so the current selection is always visible without opening anything.
 */
export function ChipMultiSelect({ id, label, options, selected, onChange, required, disabled, className }: {
  id: string;
  label: Localized;
  options: AboutOption[];
  selected: string[];
  onChange: (values: string[]) => void;
  required?: boolean;
  disabled?: boolean;
  className?: string;
}) {
  const { text } = useAuthLocale();
  const [pending, setPending] = useState("");
  const chosen = options.filter((option) => selected.includes(option.value));
  const remaining = options.filter((option) => !selected.includes(option.value));

  const add = (value: string) => {
    if (value) onChange([...selected, value]);
    setPending("");
  };

  return (
    <FormField label={label} required={required} htmlFor={id} className={className}>
      {chosen.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-1.5">
          {chosen.map((option) => (
            <Chip key={option.value} label={text(option.label)} onRemove={() => onChange(selected.filter((v) => v !== option.value))} />
          ))}
        </div>
      )}
      <div className="relative">
        <select
          id={id}
          name={id}
          value={pending}
          onChange={(event) => add(event.target.value)}
          disabled={disabled || remaining.length === 0}
          className={cn(controlClass, "appearance-none pr-9 text-left text-transparent", disabled && "text-transparent")}
        >
          <option value="" disabled>{remaining.length === 0 ? text({ en: "All added", fr: "Tous ajoutés" }) : text({ en: "Add…", fr: "Ajouter…" })}</option>
          {remaining.map((option) => (
            <option key={option.value} value={option.value} className="text-[#0F1E3D]">{text(option.label)}</option>
          ))}
        </select>
        <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 truncate pr-1 text-[14.5px] text-[#6E8098]" aria-hidden="true">
          {remaining.length === 0 ? text({ en: "All added", fr: "Tous ajoutés" }) : text({ en: "Add…", fr: "Ajouter…" })}
        </span>
        <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 size-4 -translate-y-1/2 text-[#64748B]" aria-hidden="true" />
      </div>
    </FormField>
  );
}

// Kept local so this module only depends on React's useState.
export function CheckboxField({ id, label, checked, onChange, className }: {
  id: string;
  label: Localized;
  checked: boolean;
  onChange: (checked: boolean) => void;
  className?: string;
}) {
  const { text } = useAuthLocale();
  return (
    <label className={cn("inline-flex min-h-11 cursor-pointer items-center gap-2.5 text-[14.5px] text-[#0F1E3D]", className)}>
      <Checkbox
        id={id}
        checked={checked}
        onCheckedChange={(value) => onChange(value === true)}
        className="size-[18px] shrink-0 rounded-[5px] border-2 border-[#C4C9D1] bg-white data-[state=checked]:border-[#1E3A8A] data-[state=checked]:bg-[#1E3A8A] data-[state=checked]:text-white [&_svg]:size-3"
      />
      {text(label)}
    </label>
  );
}

export function RadioGroup({ legend, options, value, onChange, className }: {
  legend: Localized;
  options: { value: string; label: Localized }[];
  value: string;
  onChange: (value: string) => void;
  className?: string;
}) {
  const { text } = useAuthLocale();
  return (
    <fieldset className={className}>
      <legend className="text-[15px] font-bold text-[#0F1E3D]">{text(legend)}</legend>
      <div className="mt-2.5 flex flex-wrap items-center gap-6">
        {options.map((option) => (
          <label key={option.value} className="inline-flex min-h-11 cursor-pointer items-center gap-2.5 rounded-md text-[14.5px] text-[#0F1E3D] focus-within:ring-2 focus-within:ring-[#1E3A8A] focus-within:ring-offset-2">
            <input
              type="radio"
              id={`${legend.en}-${option.value}`}
              name={legend.en}
              value={option.value}
              checked={value === option.value}
              onChange={() => onChange(option.value)}
              className="sr-only"
            />
            <span aria-hidden="true" className={cn("grid size-[18px] place-items-center rounded-full border-2 transition", value === option.value ? "border-[#1E3A8A]" : "border-[#C4C9D1]")}>
              <span className={cn("size-2 rounded-full", value === option.value ? "bg-[#1E3A8A]" : "bg-transparent")} />
            </span>
            {text(option.label)}
          </label>
        ))}
      </div>
    </fieldset>
  );
}

export function SectionHeading({ children }: { children: Localized }) {
  const { text } = useAuthLocale();
  return (
    <h2 className="flex items-center gap-2.5 text-[15px] font-bold text-[#0F1E3D]">
      <span aria-hidden="true" className="h-4 w-1 rounded-full bg-[#1E3A8A]" />
      {text(children)}
    </h2>
  );
}
