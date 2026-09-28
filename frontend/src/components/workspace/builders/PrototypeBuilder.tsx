import { Figma, ListTodo, Monitor, MonitorSmartphone, Plus, Smartphone, Trash2, Zap } from "lucide-react";
import { inputCls, type BuilderProps } from "./types";

const DEVICES = [
  { value: "all", label: "All devices", Icon: MonitorSmartphone },
  { value: "mobile", label: "Mobile only", Icon: Smartphone },
  { value: "desktop", label: "Desktop only", Icon: Monitor },
] as const;

export function PrototypeBuilder({ text, custom, onPatch }: BuilderProps) {
  const device = (custom.device as string) ?? "all";
  const tasks = (custom.tasks as string[]) ?? [""];

  return (
    <div className="grid min-w-0 gap-5">
      <section className="rounded-2xl border border-[#e8e8ec] bg-white p-5" aria-label={text({ en: "Prototype setup", fr: "Configuration du prototype" })}>
        <p className="text-[14px] font-bold text-[#0b1e4b]">{text({ en: "Prototype setup", fr: "Configuration du prototype" })}</p>
        <p className="mt-1 text-[12.5px] text-[#6d6d70]">{text({ en: "People try your design.", fr: "Les participants testent votre design." })}</p>
        <label className="mt-4 block text-[13px] font-semibold text-[#0b1e4b]" htmlFor="prototype-link">{text({ en: "Prototype link", fr: "Lien du prototype" })}</label>
        <p className="mt-1 text-[12.5px] text-[#6d6d70]">{text({ en: "Paste an https link testers can open.", fr: "Collez un lien https accessible aux testeurs." })}</p>
        <input id="prototype-link" value={(custom.prototype_link as string) ?? ""} onChange={(e) => onPatch({ prototype_link: e.target.value })} placeholder="https://…" className={`${inputCls} mt-3`} />
      </section>

      <section className="rounded-2xl border border-[#e8e8ec] bg-white p-5" aria-label={text({ en: "Devices", fr: "Appareils" })}>
        <p className="flex items-center gap-2 text-[14px] font-bold text-[#0b1e4b]"><MonitorSmartphone className="size-4 text-[#1d4ed8]" strokeWidth={1.8} aria-hidden="true" /> {text({ en: "Allow testers to participate on", fr: "Appareils autorisés" })}</p>
        <div className="mt-4 grid grid-cols-3 gap-3" role="radiogroup" aria-label="Devices">
          {DEVICES.map((item) => (
            <label key={item.value} className={`flex min-h-[64px] cursor-pointer flex-col items-center justify-center gap-1.5 rounded-xl border text-[12.5px] font-semibold transition ${device === item.value ? "border-[#1d4ed8] bg-[#eef4ff] text-[#0b1e4b]" : "border-[#e8e8ec] text-[#52525b] hover:border-[#1d4ed8]/50"}`}>
              <input type="radio" className="sr-only" checked={device === item.value} onChange={() => onPatch({ device: item.value })} name="pb-device" />
              <item.Icon className={`size-5 ${device === item.value ? "text-[#1d4ed8]" : "text-[#52525b]"}`} strokeWidth={1.8} aria-hidden="true" />{item.label}
            </label>
          ))}
        </div>
      </section>

      {tasks.map((link, i) => (
        <section key={i} className="rounded-2xl border border-[#e8e8ec] bg-white" aria-label={`Task ${i + 1}`}>
          <p className="flex items-center gap-2 border-b border-[#f0f0f3] px-5 py-4 text-[14px] font-bold text-[#0b1e4b]"><ListTodo className="size-4 text-[#1d4ed8]" strokeWidth={1.8} aria-hidden="true" /> Task {i + 1}
            {tasks.length > 1 && (<button type="button" onClick={() => onPatch({ tasks: tasks.filter((_, j) => j !== i) })} className="ml-auto inline-flex items-center gap-1 text-[12.5px] font-medium text-[#6d6d70] hover:text-[#0b1e4b]"><Trash2 className="size-4" aria-hidden="true" /> Remove</button>)}
          </p>
          <div className="bg-[#f7f9fc] px-5 py-4">
            <p className="flex items-center gap-2 text-[13.5px] font-bold text-[#0b1e4b]"><Figma className="size-4 text-[#1d4ed8]" strokeWidth={1.8} aria-hidden="true" /> Figma prototype
              <a href="#" onClick={(e) => e.preventDefault()} className="ml-auto inline-flex items-center gap-1 text-[12px] font-medium text-[#1d4ed8] hover:underline">Learn more about Figma prototype criteria</a>
            </p>
            <p className="mt-1 text-[12.5px] text-[#6d6d70]">Insert your Figma prototype link for this particular task</p>
            <input value={link} onChange={(e) => onPatch({ tasks: tasks.map((v, j) => (j === i ? e.target.value : v)) })} placeholder="Your figma prototype link" aria-label={`Figma link for task ${i + 1}`}
              className={`${inputCls} mt-3`} />
            <button type="button" disabled={!link.trim()} className="mt-3 inline-flex min-h-[40px] items-center gap-1.5 rounded-full border border-[#d9d9df] px-4 text-[13px] font-medium text-[#0b1e4b] disabled:opacity-40"><Zap className="size-4 text-[#1d4ed8]" aria-hidden="true" /> Sync</button>
          </div>
        </section>
      ))}
      <div>
        <p className="mb-2 text-[13px] text-[#6d6d70]">{text({ en: "Tasks", fr: "Tâches" })} <span className="font-semibold text-[#0b1e4b]">{tasks.length}</span></p>
        <button type="button" onClick={() => onPatch({ tasks: [...tasks, ""] })} className="inline-flex min-h-[48px] items-center gap-2 rounded-full bg-[#e3e3e6] px-6 text-[14px] font-semibold text-white transition hover:bg-[#1d4ed8]"><Plus className="size-4" aria-hidden="true" /> Add new task</button>
      </div>
    </div>
  );
}
