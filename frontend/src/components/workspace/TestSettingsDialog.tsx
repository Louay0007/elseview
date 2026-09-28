import { useEffect, useState } from "react";
import { Check, ChevronDown, Folder, Monitor, Smartphone, TabletSmartphone, X } from "lucide-react";
import { useAuthLocale } from "@/components/auth/AuthLocale";
import { customFieldsFor, type CustomField } from "./testSettingsConfig";

type TestType = { method: string; title: { en: string; fr: string }; body?: { en: string; fr: string } };

type Props = { open: boolean; test: TestType | null; onClose: () => void; onCreate: (settings: { name: string; language: "en" | "ar"; project: string; device: "all" | "mobile" | "desktop"; custom: Record<string, string | number | boolean> }) => void };

export function TestSettingsDialog({ open, test, onClose, onCreate }: Props) {
  const { text } = useAuthLocale();
  const [language, setLanguage] = useState<"en" | "ar">("en");
  const [name, setName] = useState("");
  const [project, setProject] = useState("");
  const [projectOpen, setProjectOpen] = useState(false);
  const [device, setDevice] = useState<"all" | "mobile" | "desktop">("all");
  const [custom, setCustom] = useState<Record<string, string | number | boolean>>({});

  const customConfig = test ? customFieldsFor(test.method) : null;

  useEffect(() => {
    if (open && test) {
      setName(`${test.title.en} 2`.slice(0, 45));
      setLanguage("en");
      setProject("");
      setProjectOpen(false);
      setDevice("all");
      const seed: Record<string, string | number | boolean> = {};
      for (const field of customFieldsFor(test.method)?.fields ?? []) {
        if (field.type === "number") seed[field.key] = field.defaultValue ?? field.min ?? 0;
        else if (field.type === "switch") seed[field.key] = field.defaultValue ?? false;
        else if (field.type === "select") seed[field.key] = field.defaultValue ?? field.options[0]?.value ?? "";
        else seed[field.key] = "";
      }
      setCustom(seed);
    }
  }, [open, test]);

  if (!open || !test) return null;
  const valid = name.trim().length > 0 && name.trim().length <= 45;

  const setField = (key: string, value: string | number | boolean) =>
    setCustom((current) => ({ ...current, [key]: value }));

  const renderField = (field: CustomField) => {
    const value = custom[field.key];
    if (field.type === "switch") {
      return (
        <button key={field.key} type="button" role="switch" aria-checked={value === true} onClick={() => setField(field.key, !(value === true))}
          className="flex w-full items-center justify-between gap-3 rounded-xl border border-[#e4e4e7] px-4 py-3 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff]">
          <span><span className="block text-[14px] font-medium text-[#18181b]">{text(field.label)}</span>
            {field.hint && <span className="mt-0.5 block text-[13px] text-[#6d6d70]">{text(field.hint)}</span>}</span>
          <span aria-hidden="true" className={`relative h-6 w-11 shrink-0 rounded-full transition-colors ${value === true ? "bg-[#18181b]" : "bg-[#d9d9df]"}`}>
            <span className={`absolute top-0.5 size-5 rounded-full bg-white shadow transition-all ${value === true ? "left-[20px]" : "left-0.5"}`} />
          </span>
        </button>
      );
    }
    if (field.type === "select") {
      return (
        <label key={field.key} className="grid gap-1.5 text-[14px] font-medium text-[#18181b]">{text(field.label)}
          <span className="relative block">
            <select value={String(value ?? "")} onChange={(event) => setField(field.key, event.target.value)}
              className="min-h-[48px] w-full appearance-none rounded-xl border border-[#d9d9df] bg-white px-4 pr-10 text-[14px] font-normal outline-none focus:border-[#18181b]">
              {field.options.map((option) => <option key={option.value} value={option.value}>{text(option.label)}</option>)}
            </select>
            <ChevronDown aria-hidden="true" className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-[#6d6d70]" />
          </span>
          {field.hint && <span className="text-[13px] font-normal text-[#6d6d70]">{text(field.hint)}</span>}
        </label>
      );
    }
    if (field.type === "number") {
      return (
        <label key={field.key} className="grid gap-1.5 text-[14px] font-medium text-[#18181b]">{text(field.label)}
          <input type="number" value={Number(value ?? 0)} min={field.min} max={field.max}
            onChange={(event) => setField(field.key, Number(event.target.value))}
            className="min-h-[48px] w-full rounded-xl border border-[#d9d9df] px-4 text-[14px] font-normal outline-none focus:border-[#18181b]" />
          {field.hint && <span className="text-[13px] font-normal text-[#6d6d70]">{text(field.hint)}</span>}
        </label>
      );
    }
    if (field.type === "textarea") {
      return (
        <label key={field.key} className="grid gap-1.5 text-[14px] font-medium text-[#18181b]">{text(field.label)}
          <textarea value={String(value ?? "")} onChange={(event) => setField(field.key, event.target.value)} rows={3}
            placeholder={field.placeholder ? text(field.placeholder) : undefined}
            className="min-h-[84px] w-full rounded-xl border border-[#d9d9df] px-4 py-3 text-[14px] font-normal outline-none focus:border-[#18181b]" />
          {field.hint && <span className="text-[13px] font-normal text-[#6d6d70]">{text(field.hint)}</span>}
        </label>
      );
    }
    return (
      <label key={field.key} className="grid gap-1.5 text-[14px] font-medium text-[#18181b]">{text(field.label)}
        <input value={String(value ?? "")} onChange={(event) => setField(field.key, event.target.value)}
          placeholder={field.placeholder ? text(field.placeholder) : undefined}
          className="min-h-[48px] w-full rounded-xl border border-[#d9d9df] px-4 text-[14px] font-normal outline-none focus:border-[#18181b]" />
        {field.hint && <span className="text-[13px] font-normal text-[#6d6d70]">{text(field.hint)}</span>}
      </label>
    );
  };

  const devices = [
    { value: "all" as const, icon: TabletSmartphone, label: { en: "All devices", fr: "Tous appareils" } },
    { value: "mobile" as const, icon: Smartphone, label: { en: "Mobile only", fr: "Mobile uniquement" } },
    { value: "desktop" as const, icon: Monitor, label: { en: "Desktop only", fr: "Bureau uniquement" } },
  ];

  return (
    <div className="fixed inset-0 z-[60] grid place-items-center overflow-y-auto bg-[#07172f]/55 p-4 backdrop-blur-[3px]" role="dialog" aria-modal="true" aria-labelledby="test-settings-title">
      <div className="my-6 max-h-[calc(100vh-48px)] w-full max-w-[680px] overflow-y-auto rounded-[26px] bg-white shadow-[0_28px_90px_rgba(0,23,70,.28)]">
        <div className="flex items-start justify-between gap-4 px-7 pt-7 sm:px-9">
          <h2 id="test-settings-title" className="text-[32px] font-bold tracking-[-.03em] text-black">{text({ en: "Test settings", fr: "Paramètres du test" })}</h2>
          <button type="button" onClick={onClose} aria-label={text({ en: "Close", fr: "Fermer" })} className="grid size-10 shrink-0 place-items-center rounded-lg border border-[#e4e4e7] text-[#18181b] hover:bg-[#f4f4f5] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff]"><X className="size-5" strokeWidth={1.6} /></button>
        </div>
        <div className="space-y-7 px-7 py-7 sm:px-9">
          <section aria-labelledby="ts-language">
            <p id="ts-language" className="text-[19px] font-bold text-black">{text({ en: "Test language", fr: "Langue du test" })}</p>
            <p className="mt-2 text-[16px] leading-[1.7] text-[#6d6d70]">{text({ en: "The test language will be what the participants see. Remember to write questions in the language you want your participants to see.", fr: "La langue du test sera celle que les participants voient. Écrivez les questions dans cette langue." })}</p>
            <div role="radiogroup" aria-label={text({ en: "Test language", fr: "Langue du test" })} className="mt-5 grid gap-6 sm:grid-cols-2">
              {([{ value: "en" as const, label: "English" }, { value: "ar" as const, label: "Arabic (عرب)" }]).map((option) => {
                const active = language === option.value;
                return (
                  <label key={option.value} className="flex cursor-pointer items-center gap-3">
                    <input type="radio" name="test-language" value={option.value} checked={active} onChange={() => setLanguage(option.value)} className="sr-only" />
                    <span aria-hidden="true" className={`grid size-7 place-items-center rounded-full border-2 transition-colors ${active ? "border-black" : "border-[#c9c9cf]"}`}>
                      {active && <span className="size-3.5 rounded-full bg-black" />}
                    </span>
                    <span className={`text-[19px] ${active ? "font-semibold text-black" : "font-normal text-black"}`}>{option.label}</span>
                  </label>
                );
              })}
            </div>
          </section>
          <section>
            <label htmlFor="test-name" className="text-[19px] font-bold text-black">{text({ en: "Give your test a name", fr: "Donnez un nom à votre test" })}</label>
            <p className="mt-2 text-[16px] text-[#6d6d70]">{text({ en: "This title will be visible to participants", fr: "Ce titre sera visible par les participants" })}</p>
            <div className="relative mt-4">
              <span className="pointer-events-none absolute left-4 top-0 -translate-y-1/2 bg-white px-1 text-[13px] text-[#6d6d70]">{text({ en: "Test name", fr: "Nom du test" })}</span>
              <input id="test-name" value={name} maxLength={45} onChange={(event) => setName(event.target.value)}
                className="min-h-[60px] w-full rounded-xl border border-[#8e8e93] px-4 pt-1 text-[18px] text-black outline-none focus:border-black" placeholder={text({ en: "Test name", fr: "Nom du test" })} />
            </div>
            <p aria-live="polite" className="mt-2 text-[14px] text-[#6d6d70]">{name.trim().length}/45</p>
          </section>
          <section>
            <p className="text-[19px] font-bold text-black">{text({ en: "Project", fr: "Projet" })}</p>
            <p className="mt-2 text-[16px] text-[#6d6d70]">{text({ en: "Select or create a new folder by creating below", fr: "Sélectionnez ou créez un nouveau dossier ci-dessous" })}</p>
            <div className="relative mt-4">
              <button type="button" aria-expanded={projectOpen} onClick={() => setProjectOpen((open) => !open)}
                className="flex min-h-[60px] w-full items-center gap-3 rounded-xl border border-[#d9d9df] px-4 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff]">
                <Folder aria-hidden="true" className="size-6 shrink-0 text-[#a1a1aa]" strokeWidth={1.4} />
                <span className={`flex-1 truncate text-[17px] ${project ? "text-black" : "text-[#a1a1aa]"}`}>{project || text({ en: "Select or create new project folder", fr: "Sélectionner ou créer un dossier" })}</span>
                <ChevronDown aria-hidden="true" className={`size-5 shrink-0 text-[#a1a1aa] transition-transform ${projectOpen ? "rotate-180" : ""}`} />
              </button>
              {projectOpen && (
                <div className="absolute inset-x-0 top-[calc(100%+8px)] z-10 rounded-xl border border-[#e4e4e7] bg-white p-2 shadow-[0_18px_50px_-20px_rgba(0,0,0,.35)]">
                  <label className="grid gap-1 px-2 pb-2 pt-1 text-[13px] font-medium text-[#6d6d70]">{text({ en: "New folder name", fr: "Nom du nouveau dossier" })}
                    <input value={project} onChange={(event) => setProject(event.target.value.slice(0, 60))} placeholder={text({ en: "e.g. Checkout Q4", fr: "ex. Panier T4" })}
                      className="min-h-[46px] rounded-lg border border-[#d9d9df] px-3 text-[15px] font-normal text-black outline-none focus:border-black" />
                  </label>
                  <button type="button" onClick={() => setProjectOpen(false)} className="flex w-full items-center justify-between rounded-lg px-3 py-2.5 text-left text-[15px] hover:bg-[#f4f4f5]">
                    <span>{project ? `${text({ en: "Use", fr: "Utiliser" })} “${project}”` : text({ en: "Continue without a folder", fr: "Continuer sans dossier" })}</span>
                    <Check aria-hidden="true" className="size-4 text-[#1d4ed8]" />
                  </button>
                </div>
              )}
            </div>
          </section>
          {customConfig && (
            <section aria-labelledby="ts-custom" className="rounded-2xl border border-[#ececf0] bg-[#fafafa] p-5">
              <p id="ts-custom" className="text-[17px] font-bold text-black">{text(customConfig.title)}</p>
              <p className="mt-1 text-[14px] text-[#6d6d70]">{text(test.body ?? { en: "Only for this test type.", fr: "Uniquement pour ce type de test." })}</p>
              <div className="mt-4 grid gap-3">{customConfig.fields.map(renderField)}</div>
            </section>
          )}
          <section aria-labelledby="ts-devices">
            <p id="ts-devices" className="text-[19px] font-bold text-black">{text({ en: "Allow testers to participate on", fr: "Appareils autorisés" })}</p>
            <div role="radiogroup" aria-label={text({ en: "Allow testers to participate on", fr: "Appareils autorisés" })} className="mt-4 grid gap-3 sm:grid-cols-3">
              {devices.map((option) => {
                const active = device === option.value;
                return (
                  <label key={option.value} className={`flex cursor-pointer items-center gap-3 rounded-xl border px-4 py-4 transition-colors ${active ? "border-[#7c3aed] bg-[#f3eaff]" : "border-[#e4e4e7] bg-white hover:border-[#c9c9cf]"}`}>
                    <input type="radio" name="test-device" value={option.value} checked={active} onChange={() => setDevice(option.value)} className="sr-only" />
                    <option.icon aria-hidden="true" className={`size-9 shrink-0 ${active ? "text-black" : "text-black"}`} strokeWidth={1.3} />
                    <span className={`text-[16px] ${active ? "font-semibold text-black" : "font-medium text-[#6d6d70]"}`}>{text(option.label)}</span>
                  </label>
                );
              })}
            </div>
          </section>
          <button type="button" disabled={!valid} onClick={() => onCreate({ name: name.trim(), language, project: project.trim(), device, custom })}
            className="min-h-[60px] w-full rounded-full bg-[#18181b] text-[19px] font-medium text-white transition-opacity disabled:cursor-not-allowed disabled:bg-[#d9d9df] disabled:text-white enabled:hover:bg-black focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff] focus-visible:ring-offset-2">
            {text({ en: "Create", fr: "Créer" })}
          </button>
        </div>
      </div>
    </div>
  );
}
