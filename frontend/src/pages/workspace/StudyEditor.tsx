import { useEffect, useState, type ReactNode } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { RecruitPanel } from "@/components/workspace/RecruitPanel";
import { StudyHeader } from "@/components/workspace/StudyHeader";
import { StudyRail, type RailStep } from "@/components/workspace/StudyRail";
import { studyQuery } from "@/components/workspace/studyNav";
import { builderFor } from "@/components/workspace/builders";
import { methodByKey } from "@/lib/methods";
import { AlignLeft, ArrowLeft, ArrowRight, BookOpenText, CircleDot, Columns3, ExternalLink, Figma, ImagePlus, Info, ListChecks, ListTodo, MessageSquare, Minus, Monitor, MonitorSmartphone, Pencil, Plus, Rows3, SlidersHorizontal, Smartphone, Star, GraduationCap, Target, Trash2, Type, X, Zap } from "lucide-react";
import { useAuthLocale } from "@/components/auth/AuthLocale";
import { BackToHome, WorkspaceShell, useWorkspaceNav } from "@/components/workspace/WorkspaceShell";
import { apiFetch, backendAvailable, newIdempotencyKey } from "@/lib/api";
import { useWorkspace } from "@/components/workspace/WorkspaceContext";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { routes, withQuery } from "@/lib/routes";

type Version = { id: string; study_id: string; number: number; revision: number; state: string; blocks_json?: { key?: string; prompt?: string }[] };
type Summary = { welcome_enabled: boolean; followup_count: number; screener_count: number; capacity: number | null; quota_capacity: number; fee_lines: { method: string; millimes: number }[]; design: string[] };
const blankBlock = (key: string) => ({ key, type: "survey.text", prompt: "" });

type PrototypeBuilderProps = {
  text: ReturnType<typeof useAuthLocale>["text"];
  nav: ReturnType<typeof useWorkspaceNav>;
};

function HeroArt({ mini }: { mini?: boolean }) {
  return (
      <svg viewBox="0 0 400 520" role="img" aria-label="Welcome illustration" className="h-full w-full">
      <rect x="0" y="0" width="400" height="520" rx="28" fill="#0e0e13" />
      <circle cx="60" cy="120" r="5" fill="#fff" opacity=".8" />
      <circle cx="330" cy="90" r="6" fill="#fff" opacity=".7" />
      <circle cx="360" cy="220" r="4" fill="#fff" opacity=".6" />
      <circle cx="40" cy="300" r="4" fill="#fff" opacity=".6" />
      <path d="M0 420 Q 90 360 150 420 T 400 400 V 520 H 0 Z" fill="#e8c98f" />
      <path d="M0 450 Q 120 400 220 450 T 400 440 V 520 H 0 Z" fill="#1d4ed8" opacity=".85" />
      <rect x="90" y="70" width="110" height="90" rx="8" fill="#1d4ed8" />
      <rect x="105" y="85" width="50" height="38" rx="4" fill="#eef4ff" />
      <path d="M105 85 l25 19 25 -19 M105 123 l18 -14 7 6 7 -6 18 14" stroke="#1d4ed8" strokeWidth="2" fill="none" />
      <rect x="165" y="92" width="28" height="8" rx="2" fill="#e8c98f" />
      <rect x="165" y="106" width="18" height="8" rx="2" fill="#e8688a" />
      <rect x="215" y="60" width="120" height="70" rx="8" fill="#f4e3c2" />
      <rect x="228" y="72" width="94" height="18" rx="3" fill="#fff" stroke="#9db4e8" strokeWidth="1.5" />
      <rect x="228" y="96" width="40" height="22" rx="3" fill="#e8a0bf" />
      <rect x="292" y="112" width="30" height="30" rx="4" fill="#e8688a" />
      <circle cx="290" cy="200" r="34" fill="#fff" />
      <path d="M272 200 l14 14 26 -30" stroke="#1d4ed8" strokeWidth="12" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="150" cy="52" r="16" fill="#1d4ed8" />
      <rect x="40" y="180" width="200" height="150" rx="10" fill="#c9d6f2" />
      <circle cx="58" cy="194" r="4" fill="#e8688a" />
      <circle cx="72" cy="194" r="4" fill="#e8a0bf" />
      <circle cx="86" cy="194" r="4" fill="#1d4ed8" />
      <rect x="58" y="212" width="12" height="12" fill="#e8688a" />
      <rect x="58" y="232" width="12" height="12" fill="#e8c98f" />
      <rect x="58" y="252" width="12" height="12" fill="#1d4ed8" />
      <rect x="80" y="214" width="90" height="4" rx="2" fill="#fff" opacity=".8" />
      <rect x="80" y="226" width="120" height="4" rx="2" fill="#fff" opacity=".6" />
      <rect x="80" y="238" width="70" height="4" rx="2" fill="#fff" opacity=".8" />
      <rect x="80" y="254" width="110" height="4" rx="2" fill="#fff" opacity=".6" />
      <rect x="80" y="270" width="90" height="4" rx="2" fill="#fff" opacity=".8" />
      <rect x="20" y="270" width="52" height="52" rx="8" fill="#e8a0bf" />
      <text x="46" y="308" textAnchor="middle" fontSize="32" fontWeight="800" fill="#18181b">A</text>
      <rect x="20" y="330" width="52" height="52" rx="8" fill="#eef4ff" />
      <text x="46" y="368" textAnchor="middle" fontSize="32" fontWeight="800" fill="#18181b">B</text>
      <rect x="120" y="392" width="110" height="34" rx="8" fill="#f0a13c" transform="rotate(-8 175 409)" />
      <rect x="140" y="400" width="70" height="52" rx="6" fill="#e8688a" transform="rotate(-8 175 426)" />
      <circle cx="238" cy="330" r="30" fill="#f2c9c4" />
      <path d="M205 330 q -8 -52 30 -56 q 44 -4 36 50 l 6 30 h -72 Z" fill="#23232b" />
      <path d="M196 420 q 10 -70 70 -74 q 66 -4 84 60 l 10 114 h -170 Z" fill="#1d4ed8" />
      <circle cx="330" cy="420" r="12" fill="#fff" />
      <circle cx="120" cy="470" r="7" fill="#1d4ed8" />
      {!mini && <circle cx="300" cy="160" r="16" fill="none" stroke="#fff" strokeWidth="3" opacity=".7" />}
      </svg>
  );
}


const QB_BLUE = "#1d4ed8";
const QB_NAVY = "#0b1e4b";

function QMini({ kind }: { kind: string }) {
  const bar = "#c9cdd6";
  const soft = "#eef1f6";
  if (kind === "free") return (
      <svg viewBox="0 0 120 78" className="h-[78px] w-full" aria-hidden="true">
      <rect x="6" y="4" width="108" height="12" rx="3" fill="#fff" stroke="#d9d9df" />
      <rect x="6" y="22" width="108" height="50" rx="4" fill="#eef4ff" stroke={QB_BLUE} strokeDasharray="4 3" />
      </svg>
  );
  if (kind === "single") return (
      <svg viewBox="0 0 120 78" className="h-[78px] w-full" aria-hidden="true">
      <rect x="6" y="4" width="108" height="10" rx="3" fill="#fff" stroke="#d9d9df" />
      {[0, 1, 2].map((i) => (
      <g key={i}>
      <rect x="18" y={22 + i * 18} width="96" height="12" rx="3" fill={i === 1 ? "#dbe5fb" : soft} />
      <circle cx="10" cy={28 + i * 18} r="4.5" fill={i === 1 ? QB_BLUE : "#fff"} stroke={i === 1 ? QB_BLUE : bar} strokeWidth="1.6" />
          {i === 1 && <circle cx="10" cy={28 + i * 18} r="1.8" fill="#fff" />}
      </g>
      ))}
      </svg>
  );
  if (kind === "multi") return (
      <svg viewBox="0 0 120 78" className="h-[78px] w-full" aria-hidden="true">
      <rect x="6" y="4" width="108" height="10" rx="3" fill="#fff" stroke="#d9d9df" />
      {[0, 1, 2].map((i) => (
      <g key={i}>
      <rect x="18" y={22 + i * 18} width="96" height="12" rx="3" fill={i < 2 ? "#fdeccd" : soft} />
      <rect x="5" y={23 + i * 18} width="9" height="9" rx="2" fill={i < 2 ? QB_BLUE : "#fff"} stroke={i < 2 ? QB_BLUE : bar} strokeWidth="1.6" />
      </g>
      ))}
      </svg>
  );
  if (kind === "likert") return (
      <svg viewBox="0 0 120 78" className="h-[78px] w-full" aria-hidden="true">
      <rect x="6" y="4" width="108" height="10" rx="3" fill="#fff" stroke="#d9d9df" />
      <g>{[0, 1, 2, 3, 4, 5].map((i) => (<circle key={i} cx={16 + i * 17} cy={34} r="5" fill={i === 0 ? QB_BLUE : "#fff"} stroke={i === 0 ? QB_BLUE : bar} strokeWidth="1.6" />))}</g>
      <rect x="6" y="50" width="108" height="8" rx="3" fill={soft} />
      <rect x="6" y="62" width="108" height="8" rx="3" fill={soft} />
      </svg>
  );
  if (kind === "matrix") return (
      <svg viewBox="0 0 120 78" className="h-[78px] w-full" aria-hidden="true">
      <rect x="6" y="4" width="108" height="10" rx="3" fill="#fff" stroke="#d9d9df" />
      {[0, 1, 2].map((r) => (
      <g key={r}>
      <rect x="6" y={20 + r * 18} width="26" height="10" rx="3" fill={soft} />
          {[0, 1, 2, 3, 4].map((c) => (<circle key={c} cx={44 + c * 15} cy={25 + r * 18} r="4.5" fill={r === c - 1 ? QB_BLUE : "#fff"} stroke={r === c - 1 ? QB_BLUE : bar} strokeWidth="1.5" />))}
      </g>
      ))}
      </svg>
  );
  if (kind === "rating") return (
      <svg viewBox="0 0 120 78" className="h-[78px] w-full" aria-hidden="true">
      <rect x="6" y="4" width="108" height="10" rx="3" fill="#fff" stroke="#d9d9df" />
      <g fontSize="9" fill="#6d6d70" textAnchor="middle">{[1, 2, 3, 4, 5].map((n, i) => (<text key={n} x={22 + i * 19} y={30}>{n}</text>))}</g>
      <g>{[0, 1, 2, 3, 4].map((i) => (<circle key={i} cx={22 + i * 19} cy={46} r="7" fill={i === 3 ? "#eef4ff" : "#fff"} stroke={i === 3 ? QB_BLUE : bar} strokeWidth="1.5" />))}</g>
      <rect x="6" y="60" width="108" height="8" rx="3" fill={soft} />
      </svg>
  );
  return (
      <svg viewBox="0 0 120 78" className="h-[78px] w-full" aria-hidden="true">
      <rect x="6" y="4" width="108" height="10" rx="3" fill="#fff" stroke="#d9d9df" />
      {[0, 1, 2].map((i) => (
      <g key={i}>
      <text x={10} y={30 + i * 16} fontSize="8" fill="#6d6d70">:{i + 1}</text>
      <rect x="22" y={22 + i * 16} width={92 - i * 14} height="10" rx="3" fill={i === 0 ? "#dbe5fb" : soft} />
      </g>
      ))}
      </svg>
  );
}

const QUESTION_TYPES = [
  { key: "free", label: "Free Text", Icon: AlignLeft },
  { key: "single", label: "Single choice", Icon: CircleDot },
  { key: "multi", label: "Multiple-choice", Icon: ListChecks },
  { key: "likert", label: "Likert scale", Icon: SlidersHorizontal },
  { key: "matrix", label: "Likert matrix", Icon: Columns3 },
  { key: "rating", label: "Rating scale", Icon: Star },
  { key: "ranking", label: "Ranking scale", Icon: Rows3 },
] as const;

function QuestionGrid({ picked, preview, onPick }: { picked: string[]; preview: string | null; onPick: (key: string) => void }) {
  return (
      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
      {QUESTION_TYPES.map((q) => {
        const active = preview === q.key;
        const count = picked.filter((k) => k === q.key).length;
        return (
      <button key={q.key} type="button" onClick={() => onPick(q.key)}
            aria-pressed={active}
            className={`rounded-xl border bg-white p-3 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1d4ed8] ${active ? "border-[#1d4ed8] ring-2 ring-[#1d4ed8]/25" : "border-[#e8e8ec] hover:border-[#1d4ed8]/60"}`}>
      <QMini kind={q.key} />
      <span className="mt-2 flex items-center gap-1.5 text-[13px] font-semibold text-[#0b1e4b]">
      <q.Icon className="size-4 text-[#1d4ed8]" strokeWidth={1.8} aria-hidden="true" />{q.label}
              {count > 0 && <span className="ml-auto grid size-5 place-items-center rounded-full bg-[#1d4ed8] text-[11px] font-bold text-white">{count}</span>}
      </span>
      </button>
        );
      })}
      </div>
  );
}

function BriefingPreview({ label, preview }: { label: string; preview: string | null }) {
  const name = QUESTION_TYPES.find((q) => q.key === preview)?.label;
  return (
      <div className="rounded-xl border border-[#e8e8ec] bg-white p-4 shadow-[0_14px_35px_-28px_rgba(11,30,75,.4)]">
      <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-[#6d6d70]">{label}</p>
      <div className="mt-3 rounded-lg bg-[#f7f9fc] p-3">
        {name ? (<><QMini kind={preview as string} /><p className="mt-2 text-center text-[13px] font-medium text-[#0b1e4b]">{name}</p></>)
        : (<p className="py-8 text-center text-[13.5px] leading-6 text-[#6d6d70]">Choose a briefing question<br />to preview</p>)}
      </div>
      </div>
  );
}

function ThanksArt({ mini }: { mini?: boolean }) {
  return (
      <svg viewBox="0 0 400 520" role="img" aria-label="Thank you illustration" className="h-full w-full">
      <rect x="0" y="0" width="400" height="520" rx="28" fill="#101018" />
      <circle cx="52" cy="150" r="4" fill="#fff" opacity=".7" />
      <circle cx="238" cy="36" r="8" fill="#fff" opacity=".9" />
      <circle cx="356" cy="240" r="5" fill="#fff" opacity=".6" />
      <circle cx="36" cy="330" r="4" fill="#fff" opacity=".5" />
      <path d="M0 430 Q 90 370 160 430 T 400 410 V 520 H 0 Z" fill="#e8c98f" />
      <path d="M0 462 Q 120 410 220 462 T 400 452 V 520 H 0 Z" fill="#1d4ed8" opacity=".9" />
      <circle cx="262" cy="52" r="26" fill="#1d4ed8" />
      <rect x="118" y="78" width="112" height="86" rx="8" fill="#1d4ed8" />
      <rect x="132" y="94" width="46" height="40" rx="4" fill="#eef4ff" />
      <path d="M132 94 l23 17 23 -17 M132 134 l16 -12 7 5 7 -5 16 12" stroke="#1d4ed8" strokeWidth="2" fill="none" />
      <rect x="184" y="100" width="34" height="10" rx="2" fill="#e8c98f" />
      <rect x="184" y="116" width="22" height="10" rx="2" fill="#f0a13c" />
      <rect x="242" y="74" width="118" height="70" rx="8" fill="#f4e3c2" />
      <rect x="254" y="86" width="94" height="18" rx="3" fill="#fff" stroke="#9db4e8" strokeWidth="1.5" />
      <rect x="254" y="110" width="38" height="20" rx="3" fill="#e8a0bf" />
      <rect x="314" y="126" width="28" height="28" rx="4" fill="#e8688a" />
      <circle cx="290" cy="196" r="34" fill="#fff" />
      <path d="M272 196 l14 14 26 -30" stroke="#1d4ed8" strokeWidth="12" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      <rect x="52" y="196" width="196" height="158" rx="10" fill="#c9d6f2" />
      <circle cx="70" cy="210" r="4" fill="#e8688a" />
      <circle cx="84" cy="210" r="4" fill="#f0a13c" />
      <circle cx="98" cy="210" r="4" fill="#1d4ed8" />
      <rect x="70" y="228" width="12" height="12" fill="#e8688a" />
      <rect x="70" y="248" width="12" height="12" fill="#f0a13c" />
      <rect x="70" y="268" width="12" height="12" fill="#1d4ed8" />
      <rect x="92" y="230" width="88" height="4" rx="2" fill="#fff" opacity=".85" />
      <rect x="92" y="242" width="120" height="4" rx="2" fill="#fff" opacity=".6" />
      <rect x="92" y="254" width="70" height="4" rx="2" fill="#fff" opacity=".85" />
      <rect x="92" y="270" width="108" height="4" rx="2" fill="#fff" opacity=".6" />
      <rect x="92" y="286" width="88" height="4" rx="2" fill="#fff" opacity=".85" />
      <rect x="34" y="286" width="50" height="50" rx="8" fill="#f0a13c" />
      <text x="59" y="322" textAnchor="middle" fontSize="30" fontWeight="800" fill="#18181b">A</text>
      <rect x="34" y="344" width="50" height="50" rx="8" fill="#eef4ff" />
      <text x="59" y="380" textAnchor="middle" fontSize="30" fontWeight="800" fill="#18181b">B</text>
      <circle cx="248" cy="330" r="30" fill="#f2c9c4" />
      <path d="M215 330 q -8 -52 30 -56 q 44 -4 36 50 l 6 30 h -72 Z" fill="#23232b" />
      <path d="M206 420 q 10 -70 70 -74 q 66 -4 84 60 l 10 114 h -170 Z" fill="#1d4ed8" />
      <rect x="150" y="392" width="90" height="52" rx="6" fill="#e8688a" transform="rotate(-8 195 418)" />
      <rect x="132" y="384" width="104" height="14" rx="7" fill="#f0a13c" transform="rotate(-8 184 391)" />
      {!mini && <circle cx="310" cy="150" r="16" fill="none" stroke="#fff" strokeWidth="3" opacity=".7" />}
      </svg>
  );
}

function PrototypeBuilder({ text, nav }: PrototypeBuilderProps) {
  const [params] = useSearchParams();
  const studyMethod = params.get("method") ?? "prototype.task";
  const studyName = params.get("name")?.trim() || "Prototype 2";
  const studyProject = params.get("project")?.trim() || "hey";
  const studyLang = params.get("lang") === "ar" ? "ar" : "en";
  const [step, setStep] = useState<"welcome" | "builder" | "thanks" | "recruit">("welcome");
  const [title, setTitle] = useState("Welcome to this test");
  const [message, setMessage] = useState("Thank you for taking part. Please read any instructions carefully, so you can complete the test without any interruption.");
  const [thanksTitle, setThanksTitle] = useState("Thank you for participating.");
  const [thanksMessage, setThanksMessage] = useState("Your insights are extremely valuable to us and make our products better for everyone.");
  const [photo, setPhoto] = useState(true);
  const [custom, setCustom] = useState<Record<string, unknown>>(() => {
    try {
      const raw = params.get("custom");
      const parsed = raw ? JSON.parse(raw) : {};
      return typeof parsed === "object" && parsed !== null ? parsed : {};
    } catch {
      return {};
    }
  });
  const patchCustom = (patch: Record<string, unknown>) => setCustom((c) => ({ ...c, ...patch }));
  const methodInfo = methodByKey(studyMethod);
  const methodTitle = methodInfo ? text(methodInfo.title) : studyName;
  const Builder = builderFor(studyMethod);
  const [introPicked, setIntroPicked] = useState<string[]>([]);
  const [conclPicked, setConclPicked] = useState<string[]>([]);
  const [introPreview, setIntroPreview] = useState<string | null>(null);
  const [conclPreview, setConclPreview] = useState<string | null>(null);
  const [introOpen, setIntroOpen] = useState(false);
  const [testOpen, setTestOpen] = useState(false);
  const [conclOpen, setConclOpen] = useState(false);

  const studyQueryString = studyQuery({ method: studyMethod, name: studyName, lang: studyLang, project: studyProject });

  const handleRailSelect = (next: RailStep) => {
    if (next === "publish") nav.goWithParams(withQuery(routes.publish, studyQueryString));
    else setStep(next);
  };

  const rail = <StudyRail active={step} onSelect={handleRailSelect} />;

  const previewCard = (heading: string, body: string, art?: ReactNode) => (
      <div className="rounded-[18px] bg-white p-5 shadow-[0_18px_45px_-30px_rgba(24,24,27,.35)]">
      <div className="flex gap-4">
      <div className="min-w-0 flex-1">
      <p className="truncate text-[17px] font-bold text-black">{heading || text({ en: "Welcome to this…", fr: "Bienvenue…" })}</p>
      <p className="mt-2 line-clamp-4 text-[13.5px] leading-6 text-[#6d6d70]">{body}</p>
      </div>
        {photo && <div className="w-[92px] shrink-0 overflow-hidden rounded-xl">{art ?? <HeroArt mini />}</div>}
      </div>
      <button type="button" tabIndex={-1} className="mt-4 inline-flex items-center gap-1.5 rounded-full bg-[#1d4ed8] px-5 py-2.5 text-[13px] font-semibold text-white hover:bg-[#1e40af]">{text({ en: "Get Started", fr: "Commencer" })} <ArrowRight className="size-4" strokeWidth={1.8} aria-hidden="true" /></button>
      </div>
  );

  return (
      <WorkspaceShell fluid>
      <div className="-mx-6 -mt-8 border-b border-[#e8e8ec] bg-[#fafafa] px-6 py-3">
      <StudyHeader studyName={studyName} project={studyProject} lang={studyLang} method={studyMethod} onPublish={() => nav.goWithParams(withQuery(routes.publish, studyQueryString))} />
      </div>

      <div className={`mt-8 grid gap-10 ${step === "recruit" ? "lg:grid-cols-[200px_minmax(0,1fr)]" : "lg:grid-cols-[200px_minmax(0,1fr)_300px]"}`}>

      <aside>{rail}</aside>

      <main className="min-w-0">
          {step === "welcome" && (
      <div className="grid gap-8 xl:grid-cols-2">
      <div>
      <h1 className="text-[26px] font-bold text-black">{text({ en: "Welcome page", fr: "Page d’accueil" })}</h1>
      <p className="mt-3 text-[15.5px] leading-7 text-[#6d6d70]">{text({ en: "To help participants, personalise your welcome page with a title, image and a custom message.", fr: "Aidez les participants : titre, image et message personnalisé." })}</p>
      <div className="relative mt-8">
      <label htmlFor="pb-title" className="absolute -top-2.5 left-4 flex items-center gap-1 bg-white px-1.5 text-[13px] text-[#1d4ed8]"><Type className="size-3.5" strokeWidth={1.8} aria-hidden="true" /> Page title</label>
      <input id="pb-title" value={title} maxLength={45} onChange={(e) => setTitle(e.target.value)} className="min-h-[56px] w-full rounded-2xl border border-[#a1a1aa] bg-white px-4 text-[16px] text-black focus:border-[#1d4ed8] focus:outline-none focus:ring-2 focus:ring-[#1d4ed8]/25" />
      </div>
      <p className="mt-1.5 text-[13px] text-[#6d6d70]">{title.length}/45</p>
      <div className="relative mt-6">
      <label htmlFor="pb-msg" className="absolute -top-2.5 left-4 flex items-center gap-1 bg-white px-1.5 text-[13px] text-[#1d4ed8]"><MessageSquare className="size-3.5" strokeWidth={1.8} aria-hidden="true" /> Welcome message</label>
      <textarea id="pb-msg" value={message} maxLength={300} rows={6} onChange={(e) => setMessage(e.target.value)} className="w-full resize-none rounded-2xl border border-[#a1a1aa] bg-white px-4 py-4 text-[16px] leading-7 text-black focus:border-[#1d4ed8] focus:outline-none focus:ring-2 focus:ring-[#1d4ed8]/25" />
      </div>
      <p className="mt-1.5 text-[13px] text-[#6d6d70]">{message.length}/300</p>
      </div>
      <div>
      <div className="overflow-hidden rounded-[26px]">
                  {photo ? <HeroArt /> : <div className="grid aspect-[4/5] place-items-center rounded-[26px] bg-[#f4f4f5] text-sm text-[#a1a1aa]">No photo</div>}
      </div>
      <div className="mt-4 flex items-center justify-center gap-10 text-[14.5px] font-medium text-black">
      <button type="button" onClick={() => setPhoto(true)} className="inline-flex items-center gap-1.5 hover:underline"><ImagePlus className="size-4 text-[#1d4ed8]" strokeWidth={1.8} aria-hidden="true" /> Change Photo</button>
      <button type="button" onClick={() => setPhoto(false)} className="inline-flex items-center gap-1.5 hover:underline"><Trash2 className="size-4 text-[#1d4ed8]" strokeWidth={1.8} aria-hidden="true" /> Remove Photo</button>
      </div>
      </div>
      </div>
          )}

          {step === "builder" && (
      <div>
      <div className="flex items-center justify-between gap-4">
      <h2 className="flex items-center gap-2 text-[17px] font-bold text-[#0b1e4b]"><BookOpenText className="size-5 text-[#1d4ed8]" strokeWidth={1.8} aria-hidden="true" /> {text({ en: "Introduction questions", fr: "Questions d’introduction" })} <span className="text-[13px] font-medium text-[#6d6d70]">(Optional)</span></h2>
      <span className="flex items-center gap-2">
      <span className="grid min-w-7 place-items-center rounded-md bg-[#fdeccd] px-1.5 py-1 text-[12px] font-bold text-[#0b1e4b]" aria-label={`${introPicked.length} selected`}>{introPicked.length}</span>
      <button type="button" onClick={() => setIntroOpen((v) => !v)} aria-expanded={introOpen} aria-label={introOpen ? "Collapse" : "Expand"} className="grid size-8 place-items-center rounded-lg text-[#52525b] hover:bg-[#f4f4f5]">{introOpen ? <Minus className="size-4" /> : <Plus className="size-4" />}</button>
      </span>
      </div>
              {introOpen && (<>
      <p className="mt-2 text-[13.5px] leading-6 text-[#6d6d70]">{text({ en: "Ask your testers pre-test questions to gain deeper insights. You can add a maximum of 5 questions.", fr: "Posez jusqu’à 5 questions avant le test." })}</p>
      <div className="mt-4">
      <QuestionGrid picked={introPicked} preview={introPreview} onPick={(key) => { setIntroPreview(key); if (introPicked.length < 5) setIntroPicked((c) => [...c, key]); }} />
      </div>
      </>)}

      <div className="mt-10 border-t border-[#e8e8ec] pt-8">
      <div className="flex items-center justify-between gap-4">
      <h2 className="flex items-center gap-2 text-[17px] font-bold text-[#0b1e4b]"><Target className="size-5 text-[#1d4ed8]" strokeWidth={1.8} aria-hidden="true" /> {methodTitle}</h2>
      <button type="button" onClick={() => setTestOpen((v) => !v)} aria-expanded={testOpen} aria-label={testOpen ? "Collapse" : "Expand"} className="grid size-8 place-items-center rounded-lg text-[#52525b] hover:bg-[#f4f4f5]">{testOpen ? <Minus className="size-4" /> : <Plus className="size-4" />}</button>
      </div>
                {testOpen && (
      <div className="mt-4">
      <Builder text={text} method={studyMethod} custom={custom} onPatch={patchCustom} />
      </div>
                )}
      </div>

      <div className="mt-10 border-t border-[#e8e8ec] pt-8">
      <div className="flex items-center justify-between gap-4">
      <h2 className="flex items-center gap-2 text-[17px] font-bold text-[#0b1e4b]"><GraduationCap className="size-5 text-[#1d4ed8]" strokeWidth={1.8} aria-hidden="true" /> {text({ en: "Conclusion questions", fr: "Questions de fin" })} <span className="text-[13px] font-medium text-[#6d6d70]">(Optional)</span></h2>
      <span className="flex items-center gap-2">
      <span className="grid min-w-7 place-items-center rounded-md bg-[#fdeccd] px-1.5 py-1 text-[12px] font-bold text-[#0b1e4b]" aria-label={`${conclPicked.length} selected`}>{conclPicked.length}</span>
      <button type="button" onClick={() => setConclOpen((v) => !v)} aria-expanded={conclOpen} aria-label={conclOpen ? "Collapse" : "Expand"} className="grid size-8 place-items-center rounded-lg text-[#52525b] hover:bg-[#f4f4f5]">{conclOpen ? <Minus className="size-4" /> : <Plus className="size-4" />}</button>
      </span>
      </div>
                {conclOpen && (<>
      <p className="mt-2 text-[13.5px] leading-6 text-[#6d6d70]">{text({ en: "Ask your testers post-test questions to gain deeper insights. You can add a maximum of 5 questions.", fr: "Posez jusqu’à 5 questions après le test." })}</p>
      <div className="mt-4">
      <QuestionGrid picked={conclPicked} preview={conclPreview} onPick={(key) => { setConclPreview(key); if (conclPicked.length < 5) setConclPicked((c) => [...c, key]); }} />
      </div>
      </>)}
      </div>

      <div className="mt-10 flex items-center justify-between border-t border-[#e8e8ec] pt-6">
      <button type="button" onClick={() => setStep("welcome")} className="inline-flex min-h-[44px] items-center gap-2 text-[15px] font-semibold text-[#0b1e4b] hover:underline"><ArrowLeft className="size-4 text-[#1d4ed8]" strokeWidth={1.8} aria-hidden="true" /> Previous</button>
      <button type="button" onClick={() => setStep("thanks")} disabled={false} className="inline-flex min-h-[48px] items-center gap-2 rounded-full bg-[#1d4ed8] px-8 text-[15px] font-semibold text-white shadow-[0_16px_35px_-18px_rgba(29,78,216,.8)] hover:bg-[#1e40af] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1d4ed8] focus-visible:ring-offset-2">Next <ArrowRight className="size-4" strokeWidth={1.8} aria-hidden="true" /></button>
      </div>
      </div>
          )}

          {step === "thanks" && (
      <div className="grid gap-8 xl:grid-cols-2">
      <div>
      <h1 className="text-[26px] font-bold text-black">{text({ en: "Thank you page", fr: "Page de remerciement" })}</h1>
      <p className="mt-3 text-[15.5px] leading-7 text-[#6d6d70]">{text({ en: "You can create a customised message to thank your participants.", fr: "Créez un message pour remercier vos participants." })}</p>
      <div className="relative mt-8">
      <label htmlFor="pb-thanks" className="absolute -top-2.5 left-4 flex items-center gap-1 bg-white px-1.5 text-[13px] text-[#1d4ed8]"><Type className="size-3.5" strokeWidth={1.8} aria-hidden="true" /> Page title</label>
      <input id="pb-thanks" value={thanksTitle} maxLength={45} onChange={(e) => setThanksTitle(e.target.value)} className="min-h-[56px] w-full rounded-2xl border border-[#a1a1aa] bg-white px-4 text-[16px] text-black focus:border-[#1d4ed8] focus:outline-none focus:ring-2 focus:ring-[#1d4ed8]/25" />
      </div>
      <p className="mt-1.5 text-[13px] text-[#6d6d70]">{thanksTitle.length}/45</p>
      <div className="relative mt-6">
      <label htmlFor="pb-thanks-msg" className="absolute -top-2.5 left-4 flex items-center gap-1 bg-white px-1.5 text-[13px] text-[#1d4ed8]"><MessageSquare className="size-3.5" strokeWidth={1.8} aria-hidden="true" /> Thank you message</label>
      <textarea id="pb-thanks-msg" value={thanksMessage} maxLength={300} rows={6} onChange={(e) => setThanksMessage(e.target.value)} className="w-full resize-none rounded-2xl border border-[#a1a1aa] bg-white px-4 py-4 text-[16px] leading-7 text-black focus:border-[#1d4ed8] focus:outline-none focus:ring-2 focus:ring-[#1d4ed8]/25" />
      </div>
      <p className="mt-1.5 text-[13px] text-[#6d6d70]">{thanksMessage.length}/300</p>
      </div>
      <div>
      <div className="overflow-hidden rounded-[26px]">
                  {photo ? <ThanksArt /> : <div className="grid aspect-[4/5] place-items-center rounded-[26px] bg-[#f4f4f5] text-sm text-[#a1a1aa]">No photo</div>}
      </div>
      <div className="mt-4 flex items-center justify-center gap-10 text-[14.5px] font-medium text-black">
      <button type="button" onClick={() => setPhoto(true)} className="inline-flex items-center gap-1.5 hover:underline"><ImagePlus className="size-4 text-[#1d4ed8]" strokeWidth={1.8} aria-hidden="true" /> Change Photo</button>
      <button type="button" onClick={() => setPhoto(false)} className="inline-flex items-center gap-1.5 hover:underline"><Trash2 className="size-4 text-[#1d4ed8]" strokeWidth={1.8} aria-hidden="true" /> Remove Photo</button>
      </div>
      </div>
      </div>
          )}

          {step === "thanks" && (
      <div className="mt-12 flex items-center justify-between">
      <button type="button" onClick={() => setStep("builder")} className="inline-flex min-h-[44px] items-center gap-2 text-[15px] font-semibold text-[#0b1e4b] hover:underline"><ArrowLeft className="size-4 text-[#1d4ed8]" strokeWidth={1.8} aria-hidden="true" /> Previous</button>
      <button type="button" onClick={() => setStep("recruit")} className="inline-flex min-h-[56px] items-center gap-2 rounded-full bg-[#1d4ed8] px-8 text-[16px] font-semibold text-white shadow-[0_16px_35px_-18px_rgba(29,78,216,.8)] hover:bg-[#1e40af] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1d4ed8] focus-visible:ring-offset-2">Next <ArrowRight className="size-5" strokeWidth={1.8} aria-hidden="true" /></button>
      </div>
          )}

          {step === "recruit" && (
      <div>
      <h1 className="text-[30px] font-bold tracking-[-0.02em] text-black">{text({ en: "Get participants for this study", fr: "Trouvez des participants" })}</h1>
      <p className="mt-3 max-w-[70ch] text-[16px] leading-7 text-[#6d6d70]">{text({ en: "You can either choose to recruit from the Elseview panel or share the link with your own participants.", fr: "Recrutez depuis le panel Elseview ou partagez le lien avec vos participants." })}</p>
      <div className="mt-8">
      <RecruitPanel variant="embedded" footer={
      <div className="mt-12 flex items-center justify-between border-t border-[#e8e8ec] pt-8">
      <button type="button" onClick={() => setStep("thanks")} className="inline-flex min-h-[44px] items-center gap-2 text-[15px] font-semibold text-[#0b1e4b] hover:underline"><ArrowLeft className="size-4 text-[#1d4ed8]" strokeWidth={1.8} aria-hidden="true" /> Previous</button>
      <button type="button" onClick={() => nav.goWithParams(withQuery(routes.publish, studyQueryString))} className="inline-flex min-h-[56px] items-center gap-2 rounded-full bg-[#1d4ed8] px-8 text-[16px] font-semibold text-white shadow-[0_16px_35px_-18px_rgba(29,78,216,.8)] hover:bg-[#1e40af] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1d4ed8] focus-visible:ring-offset-2">{text({ en: "Publish", fr: "Publier" })} <ArrowRight className="size-5" strokeWidth={1.8} aria-hidden="true" /></button>
      </div>
                } />
      </div>
      </div>
          )}

          {step !== "builder" && step !== "recruit" && step !== "thanks" && (
      <div className="mt-12 flex items-center justify-between">
      <button type="button" onClick={() => nav.goWithParams(routes.dashboard)} className="inline-flex items-center gap-2 text-[16px] font-medium text-[#0b1e4b] hover:underline"><ArrowLeft className="size-5 text-[#1d4ed8]" strokeWidth={1.8} aria-hidden="true" /> {text({ en: "Back to dashboard", fr: "Retour au tableau" })}</button>
      <button type="button" onClick={() => setStep("builder")} className="inline-flex min-h-[56px] items-center gap-2 rounded-full bg-[#1d4ed8] px-8 text-[16px] font-semibold text-white shadow-[0_16px_35px_-18px_rgba(29,78,216,.8)] hover:bg-[#1e40af] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1d4ed8] focus-visible:ring-offset-2">{text({ en: "Next", fr: "Suivant" })} <ArrowRight className="size-5" strokeWidth={1.8} aria-hidden="true" /></button>
      </div>)}
      </main>

        {step !== "recruit" && (
      <aside className="hidden lg:block">
      <p className="text-[13px] font-bold uppercase tracking-[0.12em] text-black">{text({ en: "Preview", fr: "Aperçu" })}</p>
          {step === "builder" ? (
      <div className="mt-4 grid gap-4">
              {introPreview && <BriefingPreview label="Introduction" preview={introPreview} />}
      <>
      <div className="rounded-xl border border-[#e8e8ec] bg-white p-4 shadow-[0_14px_35px_-28px_rgba(11,30,75,.4)]">
      <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-[#6d6d70]">{methodTitle}</p>
      <svg viewBox="0 0 200 120" className="mt-3 w-full rounded-lg bg-[#f7f9fc]" aria-hidden="true">
      <rect x="10" y="10" width="52" height="100" rx="6" fill="#fff" stroke="#d9d9df" />
      <rect x="18" y="20" width="36" height="22" rx="4" fill="#eef4ff" stroke="#1d4ed8" />
      <rect x="18" y="50" width="36" height="10" rx="2" fill="#fff" stroke="#1d4ed8" />
      <rect x="18" y="64" width="36" height="10" rx="2" fill="#eef4ff" stroke="#1d4ed8" />
      <rect x="72" y="10" width="58" height="100" rx="6" fill="#dfe5ef" />
      <rect x="138" y="10" width="52" height="100" rx="6" fill="#dfe5ef" />
      <path d="M62 70 C 90 70 90 78 130 60" stroke="#52525b" fill="none" strokeWidth="1.5" markerEnd="url(#pbRailArrow)" />
      <defs><marker id="pbRailArrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6" fill="none" stroke="#52525b" strokeWidth="1.2" /></marker></defs>
      </svg>
      </div>
      <a href="#" onClick={(e) => e.preventDefault()} className="flex items-center justify-between rounded-xl border border-[#e8e8ec] bg-white px-4 py-3.5 text-[13.5px] font-semibold text-[#0b1e4b] hover:border-[#1d4ed8]/60">{text({ en: `How to create a ${methodTitle.toLowerCase()} test`, fr: `Créer un test ${methodTitle.toLowerCase()}` })} <ExternalLink className="size-4 text-[#1d4ed8]" aria-hidden="true" /></a>
      </>
              {conclPreview && <BriefingPreview label="Conclusion" preview={conclPreview} />}
      </div>
          ) : (
      <div className="mt-4">{step === "thanks" ? previewCard(thanksTitle, thanksMessage, <ThanksArt mini />) : previewCard(title, message)}</div>
          )}
      </aside>
        )}
      </div>
      </WorkspaceShell>
  );
}

function StudyEditorForm() {
  const { text } = useAuthLocale();
  const { studyId } = useParams();
  const [searchParams] = useSearchParams();
  const nav = useWorkspaceNav();
  const { workspaceId } = useWorkspace();
  const [version, setVersion] = useState<Version | null>(null);
  const [blocks, setBlocks] = useState<{ key: string; prompt: string }[]>([{ key: "q1", prompt: "" }]);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const method = searchParams.get("method");

  useEffect(() => {
    if (!backendAvailable() || !workspaceId || !studyId) return;
    apiFetch<{ items?: Version[] } | Version[]>(`/workspaces/${workspaceId}/studies/${studyId}/versions`)
      .then((r) => {
        const list = Array.isArray(r) ? r : (r as { items?: Version[] }).items ?? [];
        const v = list[0] ?? null;
        if (v) { setVersion(v); if (v.blocks_json?.length) setBlocks(v.blocks_json.map((b, i) => ({ key: b.key ?? `q${i + 1}`, prompt: b.prompt ?? "" }))); }
      }).catch(() => {});
  }, [workspaceId, studyId]);

  const save = async () => {
    if (!workspaceId || !studyId || !version) return;
    setBusy(true); setErr(null); setMsg(null);
    try {
      const payload = blocks.length ? blocks : [blankBlock("q1")];
      const updated = await apiFetch<Version>(`/workspaces/${workspaceId}/studies/${studyId}/versions/${version.id}`, {
        method: "PUT", body: { blocks_json: payload, expected_revision: version.revision },
      });
      setVersion(updated);
      setMsg(text({ en: "Saved.", fr: "Enregistré." }));
    } catch { setErr(text({ en: "Save failed. Try again.", fr: "Échec. Réessayez." })); } finally { setBusy(false); }
  };
  const validate = async () => {
    if (!workspaceId || !studyId || !version) return;
    setBusy(true); setErr(null); setMsg(null);
    try {
      const r = await apiFetch<{ errors?: { message: string }[] }>(`/workspaces/${workspaceId}/studies/${studyId}/versions/${version.id}/validate`, { method: "POST", body: {} });
      setMsg(!r.errors?.length ? text({ en: "Ready to publish.", fr: "Prêt à publier." }) : r.errors.map((e) => e.message).join(" "));
    } catch { setErr(text({ en: "Check failed. Try again.", fr: "Vérification impossible." })); } finally { setBusy(false); }
  };
  const publish = async () => {
    if (!workspaceId || !studyId || !version) return;
    setBusy(true); setErr(null);
    try {
      await apiFetch(`/workspaces/${workspaceId}/studies/${studyId}/versions/${version.id}/publish`, { method: "POST", idempotencyKey: newIdempotencyKey(), body: {} });
      setMsg(text({ en: "Published. New replies can come in.", fr: "Publié. Les réponses peuvent arriver." }));
    } catch { setErr(text({ en: "Publish failed.", fr: "Publication impossible." })); } finally { setBusy(false); }
  };
  const openPublishSummary = async () => {
    if (!workspaceId || !studyId || !version) return;
    setBusy(true); setErr(null);
    try {
      setSummary(await apiFetch<Summary>(`/workspaces/${workspaceId}/studies/${studyId}/versions/${version.id}/summary`));
    } catch { setErr(text({ en: "Summary unavailable.", fr: "Résumé indisponible." })); } finally { setBusy(false); }
  };
  const preview = async () => {
    if (!workspaceId || !studyId || !version) return;
    try {
      const r = await apiFetch<{ token: string }>(`/workspaces/${workspaceId}/studies/${studyId}/versions/${version.id}/preview`, { method: "POST", body: {} });
      const url = `${window.location.origin}${routes.preview}#preview=${r.token}`;
      setPreviewUrl(r.token);
      window.open(url.replace(/#preview=.*$/, ""), "_blank");
      history.replaceState(null, "", window.location.pathname + window.location.search);
    } catch { setErr(text({ en: "No preview now.", fr: "Pas d’aperçu pour l’instant." })); }
  };

  const studyName = searchParams.get("name")?.trim() || "Study";
  const studyProject = searchParams.get("project")?.trim() || "";
  const studyLang = searchParams.get("lang") === "ar" ? "ar" : "en";
  const studyQueryString = studyQuery({ method: method ?? "", name: studyName, lang: studyLang, project: studyProject });

  return (
    <WorkspaceShell fluid>
      <div className="-mx-6 -mt-8 border-b border-[#e8e8ec] bg-[#fafafa] px-6 py-3">
        <StudyHeader
          studyName={studyName}
          project={studyProject}
          lang={studyLang}
          method={method ?? ""}
          onPublish={() => nav.goWithParams(withQuery(routes.publish, studyQueryString))}
        />
      </div>

      <div className="mt-8 grid gap-10 lg:grid-cols-[200px_minmax(0,1fr)_300px]">
        <aside>
          <StudyRail
            active="builder"
            onSelect={(next) => {
              if (next === "recruit") nav.goWithParams(withQuery(routes.recruit, studyQueryString));
              else if (next === "publish") nav.goWithParams(withQuery(routes.publish, studyQueryString));
              else nav.goWithParams(withQuery(routes.newStudy, studyQueryString));
            }}
          />
        </aside>

        <main className="min-w-0">
          <h1 className="text-[26px] font-bold text-black">{text({ en: "Edit study", fr: "Modifier l'étude" })}</h1>

          {err && <p role="alert" className="mt-4 rounded-lg bg-[#fff2ef] px-4 py-3 text-sm text-[#9c2d20]">{err}</p>}
          {msg && <p role="status" className="mt-4 rounded-lg bg-[#eef6ee] px-4 py-3 text-sm text-[#1d5c1d]">{msg}</p>}

          {!version && !busy && (
            <p className="mt-4 text-sm text-[#6d6d70]">
              {text({ en: "No version loaded. Open a study you own.", fr: "Aucune version chargée. Ouvrez une étude que vous possédez." })}
            </p>
          )}

          {version && (
            <>
              <p className="mt-2 text-[13px] text-[#6d6d70]">
                {text({ en: "Revision", fr: "Révision" })} {version.revision}
              </p>

              <div className="mt-6 space-y-4">
                {blocks.map((block, index) => (
                  <div key={block.key} className="grid gap-2 sm:grid-cols-[10rem_minmax(0,1fr)] sm:items-start">
                    <label htmlFor={`block-${block.key}`} className="pt-3 text-[13px] text-[#6d6d70]">
                      {text({ en: "Question", fr: "Question" })} {index + 1}
                    </label>
                    <input
                      id={`block-${block.key}`}
                      value={block.prompt}
                      onChange={(event) => {
                        const next = [...blocks];
                        next[index] = { ...next[index], prompt: event.target.value };
                        setBlocks(next);
                      }}
                      className="min-h-[52px] w-full rounded-2xl border border-[#a1a1aa] bg-white px-4 text-[16px] text-black focus:border-[#1d4ed8] focus:outline-none focus:ring-2 focus:ring-[#1d4ed8]/25"
                    />
                  </div>
                ))}
              </div>

              <div className="mt-6 flex flex-wrap gap-3">
                <button type="button" onClick={() => setBlocks([...blocks, { key: `q${blocks.length + 1}`, prompt: "" }])} className="min-h-[44px] rounded-full border border-[#e4e4e7] px-5 text-[14px] font-medium text-black hover:bg-[#f7f8fa]">
                  {text({ en: "Add question", fr: "Ajouter une question" })}
                </button>
              </div>

              <div className="mt-8 flex flex-wrap gap-3">
                <button type="button" disabled={busy} onClick={save} className="min-h-[48px] rounded-full bg-[#1d4ed8] px-6 text-[15px] font-semibold text-white disabled:opacity-60">
                  {text({ en: "Save", fr: "Enregistrer" })}
                </button>
                <button type="button" disabled={busy} onClick={validate} className="min-h-[48px] rounded-full border border-[#e4e4e7] px-6 text-[15px] font-medium text-black disabled:opacity-60">
                  {text({ en: "Check", fr: "Vérifier" })}
                </button>
                <button type="button" disabled={busy} onClick={preview} className="min-h-[48px] rounded-full border border-[#e4e4e7] px-6 text-[15px] font-medium text-black disabled:opacity-60">
                  {text({ en: "Preview", fr: "Aperçu" })}
                </button>
                <button type="button" disabled={busy} onClick={openPublishSummary} className="min-h-[48px] rounded-full bg-black px-6 text-[15px] font-semibold text-white disabled:opacity-60">
                  {text({ en: "Continue to publish", fr: "Continuer vers la publication" })}
                </button>
              </div>
            </>
          )}

          {summary && (
            <Card className="mt-8 rounded-[22px]">
              <CardHeader>
                <CardTitle>{text({ en: "Ready to publish", fr: "Prêt à publier" })}</CardTitle>
              </CardHeader>
              <CardContent>
                <Button onClick={publish} disabled={busy}>
                  {text({ en: "Publish now", fr: "Publier" })}
                </Button>
              </CardContent>
            </Card>
          )}
        </main>
      </div>
    </WorkspaceShell>
  );
}

export default function StudyEditor() {
  const { text } = useAuthLocale();
  const { studyId } = useParams();
  const [searchParams] = useSearchParams();
  const nav = useWorkspaceNav();
  
  if (!studyId && searchParams.get("method")) {
    return <PrototypeBuilder text={text} nav={nav} />;
  }
  
  return <StudyEditorForm />;
}
