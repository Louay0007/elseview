import type { ReactNode } from "react";

export type TextFn = (s: { en: string; fr: string }) => string;

export type BuilderProps = {
  text: TextFn;
  method: string;
  custom: Record<string, unknown>;
  onPatch: (patch: Record<string, unknown>) => void;
};

export const inputCls =
  "min-h-[48px] w-full rounded-xl border border-[#d9d9df] bg-white px-4 text-[14px] focus:border-[#1d4ed8] focus:outline-none focus:ring-2 focus:ring-[#1d4ed8]/25";

export const areaCls =
  "w-full rounded-xl border border-[#d9d9df] bg-white px-4 py-3 text-[14px] leading-6 focus:border-[#1d4ed8] focus:outline-none focus:ring-2 focus:ring-[#1d4ed8]/25";

export function Section({ title, hint, children, labelledBy }: { title: ReactNode; hint?: ReactNode; children: ReactNode; labelledBy?: string }) {
  return (
    <section className="rounded-2xl border border-[#e8e8ec] bg-white" aria-labelledby={labelledBy}>
      <p id={labelledBy} className="border-b border-[#f0f0f3] px-5 py-4 text-[14px] font-bold text-[#0b1e4b]">
        {title}
        {hint && <span className="mt-0.5 block text-[12.5px] font-normal text-[#6d6d70]">{hint}</span>}
      </p>
      <div className="grid gap-3 p-5">{children}</div>
    </section>
  );
}

export function ListEditor({ items, onChange, placeholder, addLabel, min = 0 }: {
  items: string[];
  onChange: (items: string[]) => void;
  placeholder: string;
  addLabel: string;
  min?: number;
}) {
  return (
    <div className="grid gap-2">
      {items.map((value, i) => (
        <div key={i} className="flex items-center gap-2">
          <input
            value={value}
            onChange={(e) => onChange(items.map((v, j) => (j === i ? e.target.value : v)))}
            placeholder={`${placeholder} ${i + 1}`}
            aria-label={`${placeholder} ${i + 1}`}
            className={inputCls}
          />
          {items.length > min && (
            <button
              type="button"
              onClick={() => onChange(items.filter((_, j) => j !== i))}
              aria-label={`Remove ${placeholder} ${i + 1}`}
              className="grid size-10 shrink-0 place-items-center rounded-xl border border-[#e8e8ec] text-[#6d6d70] hover:border-[#dc2626] hover:text-[#dc2626]"
            >
              ×
            </button>
          )}
        </div>
      ))}
      <div>
        <button
          type="button"
          onClick={() => onChange([...items, ""])}
          className="inline-flex min-h-[44px] items-center gap-2 rounded-full border border-[#d9d9df] px-5 text-[13.5px] font-semibold text-[#0b1e4b] hover:border-[#1d4ed8] hover:text-[#1d4ed8]"
        >
          + {addLabel}
        </button>
      </div>
    </div>
  );
}

export function Segmented<T extends string>({ options, value, onChange, name }: {
  options: { value: T; title: string; body?: string }[];
  value: T | null;
  onChange: (value: T) => void;
  name: string;
}) {
  return (
    <div className="grid gap-3">
      {options.map((item) => (
        <label
          key={item.value}
          className={`flex cursor-pointer items-start gap-3 rounded-xl border p-4 transition ${value === item.value ? "border-[#1d4ed8] bg-[#eef4ff]" : "border-[#e8e8ec] hover:border-[#1d4ed8]/50"}`}
        >
          <input type="radio" checked={value === item.value} onChange={() => onChange(item.value)} name={name} className="mt-1 size-4 accent-[#1d4ed8]" />
          <span>
            <span className="block text-[14px] font-semibold text-[#0b1e4b]">{item.title}</span>
            {item.body && <span className="mt-1 block text-[13px] leading-5 text-[#6d6d70]">{item.body}</span>}
          </span>
        </label>
      ))}
    </div>
  );
}

export function Toggle({ checked, onChange, label, hint }: { checked: boolean; onChange: (v: boolean) => void; label: string; hint?: string }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className="flex w-full items-center justify-between gap-4 rounded-xl border border-[#e8e8ec] px-4 py-3 text-left hover:border-[#1d4ed8]/50"
    >
      <span>
        <span className="block text-[14px] font-semibold text-[#0b1e4b]">{label}</span>
        {hint && <span className="mt-0.5 block text-[12.5px] text-[#6d6d70]">{hint}</span>}
      </span>
      <span aria-hidden="true" className={`relative h-6 w-11 shrink-0 rounded-full transition ${checked ? "bg-[#1d4ed8]" : "bg-[#d9d9df]"}`}>
        <span className={`absolute top-0.5 size-5 rounded-full bg-white shadow transition-all ${checked ? "left-[22px]" : "left-0.5"}`} />
      </span>
    </button>
  );
}

export function NumberField({ label, value, onChange, min, max }: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
}) {
  return (
    <label className="grid gap-1.5 text-[13.5px] font-semibold text-[#0b1e4b]">
      {label}
      <input
        type="number"
        value={value}
        min={min}
        max={max}
        onChange={(e) => onChange(Number(e.target.value))}
        className={inputCls}
      />
    </label>
  );
}

export function FieldError({ children }: { children: ReactNode }) {
  return (
    <p role="alert" className="text-[12.5px] font-medium leading-5 text-[#b42318]">
      {children}
    </p>
  );
}

export function PreviewBox({ title, children, rtl }: { title: ReactNode; children: ReactNode; rtl?: boolean }) {
  return (
    <div className="rounded-xl border border-[#e8e8ec] bg-[#f7f9fc] p-4">
      <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-[#6d6d70]">{title}</p>
      <div className="mt-3 rounded-lg bg-white p-4 shadow-[0_14px_35px_-28px_rgba(11,30,75,.4)]" dir={rtl ? "rtl" : undefined}>
        {children}
      </div>
    </div>
  );
}

export function OrderedOptions({ items, onChange, itemLabel, addLabel, min = 0 }: {
  items: string[];
  onChange: (items: string[]) => void;
  itemLabel: string;
  addLabel: string;
  min?: number;
}) {
  const move = (index: number, dir: -1 | 1) => {
    const next = index + dir;
    if (next < 0 || next >= items.length) return;
    const copy = [...items];
    [copy[index], copy[next]] = [copy[next], copy[index]];
    onChange(copy);
  };
  return (
    <div className="grid gap-2">
      {items.map((value, i) => (
        <div key={i} className="flex items-center gap-1.5">
          <span className="grid size-10 shrink-0 place-items-center gap-0" role="group" aria-label={`${itemLabel} ${i + 1} order`}>
            <span className="flex flex-col">
              <button
                type="button"
                onClick={() => move(i, -1)}
                disabled={i === 0}
                aria-label={`Move ${itemLabel} ${i + 1} up`}
                className="grid size-5 place-items-center rounded text-[#6d6d70] hover:bg-[#f4f4f5] hover:text-[#0b1e4b] disabled:opacity-30"
              >
                <svg viewBox="0 0 12 12" className="size-3" aria-hidden="true"><path d="M6 2l4 4H2z" fill="currentColor" /></svg>
              </button>
              <button
                type="button"
                onClick={() => move(i, 1)}
                disabled={i === items.length - 1}
                aria-label={`Move ${itemLabel} ${i + 1} down`}
                className="grid size-5 place-items-center rounded text-[#6d6d70] hover:bg-[#f4f4f5] hover:text-[#0b1e4b] disabled:opacity-30"
              >
                <svg viewBox="0 0 12 12" className="size-3" aria-hidden="true"><path d="M6 10L2 6h8z" fill="currentColor" /></svg>
              </button>
            </span>
          </span>
          <input
            value={value}
            onChange={(e) => onChange(items.map((v, j) => (j === i ? e.target.value : v)))}
            placeholder={`${itemLabel} ${i + 1}`}
            aria-label={`${itemLabel} ${i + 1}`}
            className={inputCls}
          />
          {items.length > min && (
            <button
              type="button"
              onClick={() => onChange(items.filter((_, j) => j !== i))}
              aria-label={`Remove ${itemLabel} ${i + 1}`}
              className="grid size-10 shrink-0 place-items-center rounded-xl border border-[#e8e8ec] text-[#6d6d70] hover:border-[#dc2626] hover:text-[#dc2626]"
            >
              ×
            </button>
          )}
        </div>
      ))}
      <div>
        <button
          type="button"
          onClick={() => onChange([...items, ""])}
          className="inline-flex min-h-[44px] items-center gap-2 rounded-full border border-[#d9d9df] px-5 text-[13.5px] font-semibold text-[#0b1e4b] hover:border-[#1d4ed8] hover:text-[#1d4ed8]"
        >
          + {addLabel}
        </button>
      </div>
    </div>
  );
}
