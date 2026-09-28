import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  ArrowLeft,
  ArrowRight,
  ChevronDown,
  CircleHelp,
  Info,
  Minus,
  Monitor,
  Plus,
  Search,
  Send,
  Smartphone,
  Trash2,
} from "lucide-react";
import { useAuthLocale } from "@/components/auth/AuthLocale";
import { useWorkspaceNav } from "@/components/workspace/WorkspaceShell";
import { apiFetch, backendAvailable, newIdempotencyKey } from "@/lib/api";
import { useWorkspace } from "@/components/workspace/WorkspaceContext";
import { Slider } from "@/components/ui/slider";
import { Checkbox } from "@/components/ui/checkbox";
import { panelCredits, panelSizeLabel } from "@/lib/pricing";

const PRESETS = [5, 25, 50, 200, 500, 1000];
const NATIONALITIES = ["Emirati", "Saudi Arabian", "East Asian", "Asian Expats", "Arab Expats", "Europeans"];
const EDUCATION_LEVELS = ["No formal education", "High school", "Diploma", "Bachelor's degree", "Master's degree", "Doctorate"];
const DEVICES = ["Smartphone", "Tablet", "Desktop"];
const APPS = ["Shopping", "Hobbies", "Social media", "News", "Gaming", "Chat", "Collaboration", "Banking & Finance", "Health", "Transportation", "Travel", "Office", "Mail", "Food delivery", "Content creation", "Learning", "Maintenance", "Streaming", "Messaging", "Fitness"];
const EMPLOYMENT = ["Employed full-time", "Employed part-time", "Self-employed", "Student", "Unemployed", "Retired"];
const INDUSTRIES = ["Technology", "Healthcare", "Education", "Finance", "Retail", "Government", "Other"];
const DEPARTMENTS = ["Engineering", "Design", "Marketing", "Sales", "Support", "Operations"];
const HOUSEHOLDS = ["1 person", "2 people", "3–4 people", "5+ people"];
const INCOMES = ["< $1,000", "$1,000 – $3,000", "$3,000 – $6,000", "$6,000+"];

type AccordionId = "age" | "residency" | "nationalities" | "education" | "tech" | "employment" | "household" | "extra";

function Section({ id, title, info, open, onToggle, count, children }: {
  id: AccordionId; title: string; info: string; open: boolean; onToggle: (id: AccordionId) => void; count?: number; children: ReactNode;
}) {
  return (
    <div className={`overflow-hidden rounded-2xl border bg-white transition-colors ${open ? "border-[#18181b]" : "border-[#e4e4e7]"}`}>
      <button type="button" onClick={() => onToggle(id)} aria-expanded={open} aria-controls={`recruit-panel-${id}`}
        className="flex w-full items-center gap-3 px-5 py-4 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[#0a84ff]">
        <span className="flex-1 text-[16px] font-semibold text-black">{title}</span>
        {typeof count === "number" && count > 0 && (
          <span className="grid min-w-6 place-items-center rounded-full bg-[#18181b] px-2 py-0.5 text-[12px] font-semibold text-white">{count}</span>
        )}
        <span className="group relative grid size-6 place-items-center text-[#6d6d70]">
          <Info className="size-[18px]" strokeWidth={1.6} aria-hidden="true" />
          <span role="tooltip" className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-2 hidden w-56 -translate-x-1/2 rounded-lg bg-black px-3 py-2 text-[12px] font-normal leading-relaxed text-white group-hover:block">{info}</span>
        </span>
        <span aria-hidden="true" className="grid size-6 place-items-center text-black">{open ? <Minus className="size-5" strokeWidth={1.6} /> : <Plus className="size-5" strokeWidth={1.6} />}</span>
      </button>
      {open && <div id={`recruit-panel-${id}`} className="border-t border-[#ececf0] px-5 py-5">{children}</div>}
    </div>
  );
}

function Chip({ active, children, onClick, label }: { active: boolean; children: ReactNode; onClick: () => void; label: string }) {
  return (
    <button type="button" aria-pressed={active} aria-label={label} onClick={onClick}
      className={`flex min-h-[44px] cursor-pointer items-center gap-2 rounded-full border px-4 py-2 text-[14px] font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff] ${active ? "border-[#18181b] bg-[#18181b] text-white" : "border-[#d9d9df] bg-white text-[#18181b] hover:border-[#18181b]"}`}>
      {children}
    </button>
  );
}

function CheckRow({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <label className="flex cursor-pointer items-center gap-3 rounded-xl border border-[#e4e4e7] px-4 py-3 text-[14.5px] text-[#18181b] hover:border-[#a1a1aa] has-[:checked]:border-[#18181b] has-[:checked]:bg-[#f7f7f8]">
      <Checkbox checked={checked} onCheckedChange={(v) => onChange(v === true)} aria-label={label} />
      <span>{label}</span>
    </label>
  );
}

export type RecruitSummary = { credits: number; panelLabel: string; speed: number; participants: number };

export function RecruitPanel({ variant = "standalone", onSummary, footer, study }: {
  variant?: "standalone" | "embedded";
  onSummary?: (summary: RecruitSummary) => void;
  footer?: ReactNode;
  study?: { method: string; name: string; lang: string; project: string };
}) {
  const { text } = useAuthLocale();
  const nav = useWorkspaceNav();
  const { workspaceId } = useWorkspace();

  const [count, setCount] = useState(61);
  const [demographics, setDemographics] = useState(true);
  const [screening, setScreening] = useState(false);
  const [open, setOpen] = useState<Record<AccordionId, boolean>>({ age: false, residency: false, nationalities: false, education: false, tech: false, employment: false, household: false, extra: false });
  const [gender, setGender] = useState<"any" | "male" | "female">("any");
  const [ageRange, setAgeRange] = useState<[number, number]>([18, 90]);
  const [residency, setResidency] = useState<string[]>([]);
  const [countryQuery, setCountryQuery] = useState("");
  const [otherCountries, setOtherCountries] = useState<string[]>([]);
  const [nationality, setNationality] = useState<string[]>([]);
  const [natQuery, setNatQuery] = useState("");
  const [education, setEducation] = useState("");
  const [eduOpen, setEduOpen] = useState(false);
  const [hoursOnline, setHoursOnline] = useState<[number, number]>([1, 8]);
  const [favDevices, setFavDevices] = useState<string[]>([]);
  const [apps, setApps] = useState<string[]>([]);
  const [jobs, setJobs] = useState<string[]>([]);
  const [industries, setIndustries] = useState<string[]>([]);
  const [departments, setDepartments] = useState<string[]>([]);
  const [household, setHousehold] = useState<string[]>([]);
  const [incomes, setIncomes] = useState<string[]>([]);
  const [extraText, setExtraText] = useState("");
  const [screeners, setScreeners] = useState<{ q: string; a: string }[]>([{ q: "", a: "" }]);
  const [customSent, setCustomSent] = useState(false);
  const [launchId, setLaunchId] = useState("");
  const [contact, setContact] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const toggle = (id: AccordionId) => setOpen((c) => ({ ...c, [id]: !c[id] }));
  const toggleIn = (list: string[], v: string, set: (v: string[]) => void) =>
    set(list.includes(v) ? list.filter((x) => x !== v) : [...list, v]);

  const clearAll = () => {
    setCount(5); setGender("any"); setAgeRange([18, 90]); setResidency([]); setOtherCountries([]);
    setNationality([]); setEducation(""); setHoursOnline([1, 8]); setFavDevices([]); setApps([]);
    setJobs([]); setIndustries([]); setDepartments([]); setHousehold([]); setIncomes([]);
    setExtraText(""); setScreeners([{ q: "", a: "" }]); setDemographics(false); setScreening(false);
    setOpen({ age: false, residency: false, nationalities: false, education: false, tech: false, employment: false, household: false, extra: false });
  };

  const credits = panelCredits(count);
  const panelSize = useMemo(() => {
    let size = 29700;
    if (gender !== "any") size *= 0.52;
    const span = ageRange[1] - ageRange[0];
    size *= Math.max(0.15, span / 72);
    if (residency.length > 0 || otherCountries.length > 0) size *= 0.6;
    if (nationality.length > 0) size *= 0.7;
    return size;
  }, [gender, ageRange, residency, otherCountries, nationality]);
  const panelLabel = panelSizeLabel(panelSize);
  const speed = panelSize > 15000 ? 82 : panelSize > 6000 ? 55 : 28;

  const checkAvailability = async () => {
    setError(null); setNotice(null);
    try {
      if (!backendAvailable() || !workspaceId || !launchId) throw new Error("signin");
      const r = await apiFetch<{ count: number | null; suppressed: boolean }>(
        `/workspaces/${workspaceId}/recruiting/estimate`,
        { method: "POST", body: { launch_id: launchId, count } },
      );
      setNotice(r.suppressed ? text({ en: "Too small to show.", fr: "Groupe trop petit." }) : `${r.count ?? 0} ${text({ en: "people match.", fr: "personnes." })}`);
    } catch { setError(text({ en: "Try again.", fr: "Impossible. Réessayez." })); }
  };

  const sendInvite = async () => {
    setError(null); setNotice(null);
    try {
      if (!backendAvailable() || !workspaceId || !launchId) throw new Error("signin");
      await apiFetch(`/workspaces/${workspaceId}/recruiting/launches/${launchId}/invitations`, {
        method: "POST", idempotencyKey: newIdempotencyKey(),
        body: { source_kind: "private", source_id: contact || undefined, delivery: "manual", expires_seconds: 86400 },
      });
      setNotice(text({ en: "Invite sent.", fr: "Invitation envoyée." }));
    } catch { setError(text({ en: "Try again.", fr: "Impossible. Réessayez." })); }
  };

  const natFiltered = NATIONALITIES.filter((n) => n.toLowerCase().includes(natQuery.trim().toLowerCase()));
  const activeFilters = (residency.length + otherCountries.length + nationality.length + jobs.length + industries.length + departments.length + household.length + incomes.length + apps.length + favDevices.length) + (education ? 1 : 0) + (gender !== "any" ? 1 : 0);

  
  const embedded = variant === "embedded";
  const { goWithParams } = useWorkspaceNav();
  const studyQs = study
    ? `method=${study.method}&name=${encodeURIComponent(study.name)}&lang=${study.lang}&project=${encodeURIComponent(study.project)}&participants=${count}`
    : "";

  useEffect(() => {
    onSummary?.({ credits, panelLabel, speed, participants: count });
  }, [credits, panelLabel, speed, count, onSummary]);

  return (
    <div className="min-w-0">
      {error && <p role="alert" className="mb-4 rounded-lg bg-[#fff2ef] px-4 py-3 text-sm text-[#9c2d20]">{error}</p>}
      {notice && <p role="status" className="mb-4 rounded-lg bg-[#eef6ee] px-4 py-3 text-sm text-[#1d5c1d]">{notice}</p>}

          <div className="flex flex-wrap items-start justify-between gap-3">
            <h1 className="text-[24px] font-bold tracking-tight text-black">{text({ en: "Recruit from Elseview panel", fr: "Recruter via le panel Elseview" })}</h1>
            <button type="button" onClick={clearAll} className="flex items-center gap-1.5 rounded-full border border-[#e4e4e7] px-4 py-2 text-[13.5px] font-medium text-[#18181b] hover:bg-[#f7f7f8] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff]">
              <Trash2 className="size-4" strokeWidth={1.6} aria-hidden="true" />{text({ en: "Clear selections", fr: "Tout effacer" })}
            </button>
          </div>
          <p className="mt-2 max-w-[70ch] text-[14.5px] leading-relaxed text-[#3a3a3c]">
            {text({ en: "Get results from our extensive panel in minutes, complete with demographic data! Choose the number of participants and segmentation required.", fr: "Obtenez des résultats en quelques minutes avec données démographiques. Choisissez le nombre de participants et la segmentation." })}{" "}
            <button type="button" className="font-semibold text-[#1d4ed8] underline underline-offset-2 hover:no-underline">{text({ en: "Switch to share only with your participants", fr: "Partager uniquement avec vos participants" })}</button>
          </p>

          <section aria-labelledby="recruit-count" className="mt-6 rounded-2xl border border-[#e4e4e7] bg-white p-5">
            <h2 id="recruit-count" className="text-[16px] font-semibold text-black">{text({ en: "How many participants do you want to recruit?", fr: "Combien de participants recruter ?" })}</h2>
            <div className="mt-4 flex items-center gap-3">
              <div className="flex flex-1 flex-wrap items-center gap-2" role="group" aria-label={text({ en: "Quick amounts", fr: "Montants rapides" })}>
                {PRESETS.map((p) => (
                  <button key={p} type="button" onClick={() => setCount(p)} aria-pressed={count === p}
                    className={`min-h-[40px] rounded-full px-4 text-[14px] font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff] ${count === p ? "bg-[#18181b] text-white" : "bg-[#f4f4f5] text-[#18181b] hover:bg-[#e8e8ea]"}`}>{p}</button>
                ))}
              </div>
              <div className="flex items-center gap-1 rounded-full border border-[#d9d9df] px-1 py-1">
                <button type="button" aria-label={text({ en: "Decrease", fr: "Diminuer" })} onClick={() => setCount((c) => Math.max(1, c - 1))} className="grid size-8 place-items-center rounded-full hover:bg-[#f4f4f5]"><Minus className="size-4" strokeWidth={1.8} /></button>
                <input value={count} inputMode="numeric" aria-label={text({ en: "Participants", fr: "Participants" })} onChange={(e) => setCount(Math.max(1, Math.min(1000, Number(e.target.value) || 1)))} className="w-14 bg-transparent text-center text-[15px] font-bold text-black outline-none" />
                <button type="button" aria-label={text({ en: "Increase", fr: "Augmenter" })} onClick={() => setCount((c) => Math.min(1000, c + 1))} className="grid size-8 place-items-center rounded-full hover:bg-[#f4f4f5]"><Plus className="size-4" strokeWidth={1.8} /></button>
              </div>
            </div>
            <div className="mt-4">
              <Slider value={[count]} min={5} max={1000} step={1} onValueChange={(v) => setCount(v[0] ?? count)} aria-label={text({ en: "Participants", fr: "Participants" })} />
              <div className="mt-1 flex justify-between text-[11px] font-medium text-[#8e8e93]">{PRESETS.map((p) => <span key={p}>{p}</span>)}</div>
            </div>
          </section>

          <div className="mt-4 flex items-center gap-3 rounded-2xl border border-[#e4e4e7] bg-white px-5 py-4">
            <Checkbox id="recruit-demographics" checked={demographics} onCheckedChange={(v) => setDemographics(v === true)} aria-label="Demographics" />
            <label htmlFor="recruit-demographics" className="cursor-pointer text-[15.5px] font-semibold text-black">Demographics</label>
            {activeFilters > 0 && <span className="ml-auto rounded-full bg-[#eef4ff] px-2.5 py-1 text-[12px] font-semibold text-[#1d4ed8]">{activeFilters} selected</span>}
          </div>

          {demographics && (
            <div className="mt-3 grid gap-3">
              <Section id="age" title="Age and gender" info="Move the bar to change the target group age range and the tab to select a specific gender" open={open.age} onToggle={toggle} count={(gender !== "any" ? 1 : 0) + ((ageRange[0] !== 18 || ageRange[1] !== 90) ? 1 : 0)}>
                <p className="text-[14px] text-[#3a3a3c]">Move the bar to change the target group age range and the tab to select a specific gender</p>
                <div className="mt-4 grid gap-1 text-[14px]"><p>Gender: <strong>{gender === "any" ? "Any" : gender === "male" ? "Male" : "Female"}</strong></p>
                  <p>Age range: <strong>{ageRange[0]} to {ageRange[1]}</strong></p></div>
                <div className="mt-3 flex gap-2" role="group" aria-label="Gender">
                  {(["any", "male", "female"] as const).map((g) => (
                    <button key={g} type="button" onClick={() => setGender(g)} aria-pressed={gender === g}
                      className={`min-h-[40px] flex-1 rounded-full text-[14px] font-semibold capitalize transition-colors ${gender === g ? "bg-[#18181b] text-white" : "bg-[#f4f4f5] text-[#18181b] hover:bg-[#e8e8ea]"}`}>{g === "any" ? "Any" : g === "male" ? "Male" : "Female"}</button>
                  ))}
                </div>
                <div className="mt-5 px-1">
                  <Slider value={ageRange} min={18} max={90} step={1} onValueChange={(v) => setAgeRange([v[0] ?? 18, v[1] ?? 90])} aria-label="Age range" />
                  <div className="mt-2 flex justify-between text-[13px] font-medium text-[#3a3a3c]"><span>{ageRange[0]} years</span><span>{ageRange[1]} years</span></div>
                </div>
              </Section>

              <Section id="residency" title="Residency" info="Choose participants from certain countries." open={open.residency} onToggle={toggle} count={residency.length + otherCountries.length}>
                <p className="text-[14px] text-[#3a3a3c]">Choose participants from certain countries.</p>
                <div className="mt-4 grid gap-2 sm:grid-cols-2">
                  {["UAE Residents", "Saudi Arabia Residents"].map((r) => (
                    <CheckRow key={r} label={r} checked={residency.includes(r)} onChange={() => toggleIn(residency, r, setResidency)} />
                  ))}
                </div>
                <p className="mt-4 text-[14px] font-semibold text-black">Other countries</p>
                <div className="relative mt-2">
                  <Search aria-hidden="true" className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-[#8e8e93]" />
                  <input value={countryQuery} onChange={(e) => setCountryQuery(e.target.value)} placeholder="Search"
                    aria-label="Search countries" className="min-h-[46px] w-full rounded-xl border border-[#d9d9df] bg-white pl-9 pr-3 text-[14px] outline-none focus:border-[#18181b]" />
                </div>
                {countryQuery.trim() && (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {[countryQuery.trim()].filter((c) => !otherCountries.includes(c)).map((c) => (
                      <Chip key={c} label={`Add ${c}`} active={false} onClick={() => { setOtherCountries((l) => [...l, c]); setCountryQuery(""); }}>+ {c}</Chip>
                    ))}
                  </div>
                )}
                {otherCountries.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {otherCountries.map((c) => <Chip key={c} label={`Remove ${c}`} active onClick={() => toggleIn(otherCountries, c, setOtherCountries)}>{c} ×</Chip>)}
                  </div>
                )}
              </Section>

              <Section id="nationalities" title="Nationalities" info="We have a diverse panel of participants. Choose the nationalities you would like to target." open={open.nationalities} onToggle={toggle} count={nationality.length}>
                <p className="text-[14px] text-[#3a3a3c]">We have a diverse panel of participants. Choose the nationalities you would like to target.</p>
                <div className="relative mt-3">
                  <Search aria-hidden="true" className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-[#8e8e93]" />
                  <input value={natQuery} onChange={(e) => setNatQuery(e.target.value)} placeholder="Search nationalities"
                    aria-label="Search nationalities" className="min-h-[46px] w-full rounded-xl border border-[#d9d9df] bg-white pl-9 pr-3 text-[14px] outline-none focus:border-[#18181b]" />
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {(natQuery.trim() ? natFiltered : NATIONALITIES).map((n) => (
                    <Chip key={n} label={n} active={nationality.includes(n)} onClick={() => toggleIn(nationality, n, setNationality)}>{n}</Chip>
                  ))}
                  {natQuery.trim() && natFiltered.length === 0 && <span className="text-[13px] text-[#6d6d70]">No match — press Enter to add “{natQuery.trim()}”.</span>}
                </div>
              </Section>

              <Section id="education" title="Minimum level of education" info="Select the minimum education level you require for your participants." open={open.education} onToggle={toggle} count={education ? 1 : 0}>
                <p className="text-[14px] text-[#3a3a3c]">Select the minimum education level you require for your participants.</p>
                <div className="relative mt-3">
                  <button type="button" aria-expanded={eduOpen} onClick={() => setEduOpen((v) => !v)}
                    className="flex min-h-[50px] w-full items-center justify-between rounded-xl border border-[#d9d9df] px-4 text-left text-[14.5px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff]">
                    <span className={education ? "text-black" : "text-[#8e8e93]"}>{education || "Select education level"}</span>
                    <ChevronDown aria-hidden="true" className={`size-4 text-[#6d6d70] transition-transform ${eduOpen ? "rotate-180" : ""}`} />
                  </button>
                  {eduOpen && (
                    <div role="listbox" aria-label="Education level" className="absolute inset-x-0 top-[calc(100%+6px)] z-10 overflow-hidden rounded-xl border border-[#e4e4e7] bg-white shadow-[0_18px_50px_-20px_rgba(0,0,0,.35)]">
                      {EDUCATION_LEVELS.map((level) => (
                        <button key={level} type="button" role="option" aria-selected={education === level}
                          onClick={() => { setEducation(level); setEduOpen(false); }}
                          className={`flex w-full items-center justify-between px-4 py-3 text-left text-[14.5px] hover:bg-[#f4f4f5] ${education === level ? "font-semibold text-black" : "text-[#3a3a3c]"}`}>{level}{education === level && <span aria-hidden="true">✓</span>}</button>
                      ))}
                    </div>
                  )}
                </div>
              </Section>

              <Section id="tech" title="Confidence with technology" info="Choose participants with different technical competencies." open={open.tech} onToggle={toggle} count={favDevices.length + apps.length + (hoursOnline[0] !== 1 || hoursOnline[1] !== 8 ? 1 : 0)}>
                <p className="text-[14px] text-[#3a3a3c]">Choose participants with different technical competencies.</p>
                <p className="mt-4 text-[14px] font-semibold text-black">Daily hours spent online</p>
                <p className="mt-0.5 text-[13px] text-[#6d6d70]">{hoursOnline[0]}–{hoursOnline[1]}h per day</p>
                <div className="mt-2 px-1">
                  <Slider value={hoursOnline} min={0} max={16} step={1} onValueChange={(v) => setHoursOnline([v[0] ?? 0, v[1] ?? 16])} aria-label="Daily hours spent online" />
                </div>
                <p className="mt-4 text-[14px] font-semibold text-black">Select user&apos;s favorite devices</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {DEVICES.map((d) => (
                    <Chip key={d} label={d} active={favDevices.includes(d)} onClick={() => toggleIn(favDevices, d, setFavDevices)}>
                      {d === "Smartphone" ? <Smartphone className="size-4" strokeWidth={1.6} aria-hidden="true" /> : d === "Desktop" ? <Monitor className="size-4" strokeWidth={1.6} aria-hidden="true" /> : null}{d}
                    </Chip>
                  ))}
                </div>
                <p className="mt-4 text-[14px] font-semibold text-black">Most used apps</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {APPS.map((a) => <Chip key={a} label={a} active={apps.includes(a)} onClick={() => toggleIn(apps, a, setApps)}>{a}</Chip>)}
                </div>
              </Section>

              <Section id="employment" title="Employment status" info="Choose different employment types for your participants." open={open.employment} onToggle={toggle} count={jobs.length + industries.length + departments.length}>
                <p className="text-[14px] text-[#3a3a3c]">Choose different employment types for your participants.</p>
                <p className="mt-4 text-[14px] font-semibold text-black">Current employment status</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {EMPLOYMENT.map((j) => <Chip key={j} label={j} active={jobs.includes(j)} onClick={() => toggleIn(jobs, j, setJobs)}>{j}</Chip>)}
                </div>
                <p className="mt-4 text-[14px] font-semibold text-black">Industry</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {INDUSTRIES.map((i) => <Chip key={i} label={i} active={industries.includes(i)} onClick={() => toggleIn(industries, i, setIndustries)}>{i}</Chip>)}
                </div>
                <p className="mt-4 text-[14px] font-semibold text-black">Department</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {DEPARTMENTS.map((d) => <Chip key={d} label={d} active={departments.includes(d)} onClick={() => toggleIn(departments, d, setDepartments)}>{d}</Chip>)}
                </div>
              </Section>

              <Section id="household" title="Household and earnings" info="Choose from participants with specific household numbers and income levels." open={open.household} onToggle={toggle} count={household.length + incomes.length}>
                <p className="text-[14px] text-[#3a3a3c]">Choose from participants with specific household numbers and income levels.</p>
                <p className="mt-4 text-[14px] font-semibold text-black">Household</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {HOUSEHOLDS.map((h) => <Chip key={h} label={h} active={household.includes(h)} onClick={() => toggleIn(household, h, setHousehold)}>{h}</Chip>)}
                </div>
                <p className="mt-4 text-[14px] font-semibold text-black">Household income $ per month</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {INCOMES.map((i) => <Chip key={i} label={i} active={incomes.includes(i)} onClick={() => toggleIn(incomes, i, setIncomes)}>{i}</Chip>)}
                </div>
              </Section>

              <Section id="extra" title="Additional requirements" info="Tell us your project audience and demographic requirements and we will source the right participants for you." open={open.extra} onToggle={toggle} count={extraText.trim() ? 1 : 0}>
                <p className="text-[14px] text-[#3a3a3c]">Tell us your project audience and demographic requirements and we&apos;ll source the right participants for you.</p>
                <textarea value={extraText} onChange={(e) => setExtraText(e.target.value)} rows={3} placeholder="e.g. Parents in Dubai who shop online weekly…"
                  aria-label="Additional requirements" className="mt-3 min-h-[90px] w-full rounded-xl border border-[#d9d9df] px-4 py-3 text-[14px] outline-none focus:border-[#18181b]" />
                <button type="button" onClick={() => setCustomSent(true)} disabled={!extraText.trim()}
                  className="mt-3 inline-flex min-h-[44px] items-center gap-2 rounded-full bg-[#18181b] px-5 text-[14px] font-medium text-white disabled:cursor-not-allowed disabled:opacity-40">
                  <Send className="size-4" strokeWidth={1.8} aria-hidden="true" />{customSent ? "Request sent" : "Send request"}
                </button>
              </Section>
            </div>
          )}

          <div className="mt-3 flex items-center gap-3 rounded-2xl border border-[#e4e4e7] bg-white px-5 py-4">
            <Checkbox id="recruit-screening" checked={screening} onCheckedChange={(v) => setScreening(v === true)} aria-label="Screening questions" />
            <label htmlFor="recruit-screening" className="cursor-pointer text-[15.5px] font-semibold text-black">Screening questions</label>
            <CircleHelp className="size-[18px] text-[#8e8e93]" strokeWidth={1.6} aria-hidden="true" />
          </div>
          {screening && (
            <div className="mt-3 rounded-2xl border border-[#e4e4e7] bg-white p-5">
              <p className="text-[14px] text-[#3a3a3c]">Add up to 5 knockout questions. Participants who fail are replaced for free.</p>
              <div className="mt-3 grid gap-3">
                {screeners.map((s, i) => (
                  <div key={i} className="grid gap-2 rounded-xl bg-[#f7f7f8] p-3 sm:grid-cols-2">
                    <input value={s.q} onChange={(e) => setScreeners((l) => l.map((x, j) => (j === i ? { ...x, q: e.target.value } : x)))} placeholder={`Question ${i + 1}`} aria-label={`Screening question ${i + 1}`} className="min-h-[44px] rounded-lg border border-[#d9d9df] bg-white px-3 text-[14px] outline-none focus:border-[#18181b]" />
                    <div className="flex gap-2">
                      <input value={s.a} onChange={(e) => setScreeners((l) => l.map((x, j) => (j === i ? { ...x, a: e.target.value } : x)))} placeholder="Accepted answer" aria-label={`Accepted answer ${i + 1}`} className="min-h-[44px] flex-1 rounded-lg border border-[#d9d9df] bg-white px-3 text-[14px] outline-none focus:border-[#18181b]" />
                      <button type="button" aria-label={`Remove question ${i + 1}`} onClick={() => setScreeners((l) => l.filter((_, j) => j !== i))} className="grid size-11 shrink-0 place-items-center rounded-lg border border-[#e4e4e7] hover:bg-white"><Trash2 className="size-4" strokeWidth={1.6} /></button>
                    </div>
                  </div>
                ))}
              </div>
              {screeners.length < 5 && (
                <button type="button" onClick={() => setScreeners((l) => [...l, { q: "", a: "" }])} className="mt-3 inline-flex min-h-[42px] items-center gap-2 rounded-full border border-[#18181b] px-4 text-[13.5px] font-medium"><Plus className="size-4" strokeWidth={1.8} />Add question</button>
              )}
            </div>
          )}

          <section aria-labelledby="recruit-custom" className="mt-4 overflow-hidden rounded-2xl bg-[#101828] p-6 text-white">
            <h2 id="recruit-custom" className="text-[18px] font-bold">Custom recruitment for your study</h2>
            <p className="mt-2 max-w-[60ch] text-[14px] leading-relaxed text-white/80">With prices starting at $10 per response, we can recruit participants tailored to your needs to complete any Elseview study.</p>
            <button type="button" onClick={() => setCustomSent(true)} className="mt-4 inline-flex min-h-[44px] items-center gap-2 rounded-full bg-white px-5 text-[14px] font-semibold text-black hover:bg-[#ececf0]">
              <Send className="size-4" strokeWidth={1.8} aria-hidden="true" />{customSent ? "Request sent — we reply shortly" : "Send a request"}
            </button>
          </section>

          <section aria-labelledby="recruit-private" className="mt-4 rounded-2xl border border-dashed border-[#c9c9cf] bg-white p-5">
            <h2 id="recruit-private" className="text-[15px] font-semibold text-black">{text({ en: "Already have a launch? Check availability or invite by hand.", fr: "Déjà un lancement ? Vérifiez ou invitez." })}</h2>
            <div className="mt-3 grid gap-2 sm:grid-cols-[1fr_1fr]">
              <input value={launchId} onChange={(e) => setLaunchId(e.target.value)} placeholder={text({ en: "Launch ID", fr: "ID de lancement" })} aria-label={text({ en: "Launch ID", fr: "ID de lancement" })} className="min-h-[44px] rounded-lg border border-[#e4e4e7] px-3 text-sm" />
              <input value={contact} onChange={(e) => setContact(e.target.value)} placeholder={text({ en: "Contact (optional)", fr: "Contact (facultatif)" })} aria-label={text({ en: "Contact", fr: "Contact" })} className="min-h-[44px] rounded-lg border border-[#e4e4e7] px-3 text-sm" />
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <button type="button" onClick={() => void checkAvailability()} className="rounded-full bg-[#18181b] px-5 py-2.5 text-sm font-medium text-white">{text({ en: "Check availability", fr: "Vérifier" })}</button>
              <button type="button" onClick={() => void sendInvite()} className="rounded-full border border-[#e4e4e7] px-5 py-2.5 text-sm font-medium">{text({ en: "Send invite", fr: "Envoyer" })}</button>
            </div>
          </section>

          
      {footer ?? (!embedded ? (
        <div className="mt-6 flex items-center justify-between gap-3">
            <button type="button" onClick={() => goWithParams(studyQs ? `/studies/create?${studyQs}` : "/studies/create")} className="inline-flex min-h-[48px] items-center gap-2 rounded-full border border-[#18181b] px-6 text-[14.5px] font-medium text-black hover:bg-[#f7f7f8]">
              <ArrowLeft className="size-4" strokeWidth={1.8} aria-hidden="true" />Previous
            </button>
            <button type="button" onClick={() => goWithParams(studyQs ? `/publish?${studyQs}` : "/publish")} className="inline-flex min-h-[48px] items-center gap-2 rounded-full bg-[#18181b] px-8 text-[14.5px] font-semibold text-white hover:bg-black">
              Next<ArrowRight className="size-4" strokeWidth={1.8} aria-hidden="true" />
            </button>
          </div>
      ) : null)}
    </div>
  );
}
