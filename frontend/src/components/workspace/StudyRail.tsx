import { useAuthLocale } from "@/components/auth/AuthLocale";

export type RailStep = "welcome" | "builder" | "thanks" | "recruit" | "publish";

const BUILD_STEPS: { value: "welcome" | "builder" | "thanks"; label: string }[] = [
  { value: "welcome", label: "Welcome page" },
  { value: "builder", label: "Test builder" },
  { value: "thanks", label: "Thank you" },
];

export function StudyRail({ active, onSelect }: { active: RailStep; onSelect: (step: RailStep) => void }) {
  const { text } = useAuthLocale();
  const buildActive = active === "welcome" || active === "builder" || active === "thanks";

  const number = (n: number, isActive: boolean) => (
    <span aria-hidden="true" className={`grid size-8 place-items-center rounded-full text-[15px] font-bold text-white ${isActive ? "bg-[#1d4ed8]" : "bg-[#d9d9df]"}`}>{n}</span>
  );

  return (
    <nav aria-label={text({ en: "Study steps", fr: "Étapes de l’étude" })}>
      <p className={`flex items-center gap-2 text-[17px] font-semibold ${buildActive ? "text-[#1d4ed8]" : "text-[#b9b9c0]"}`}>
        <span aria-hidden="true" className={`grid size-8 place-items-center rounded-full text-[15px] font-bold text-white ${buildActive ? "bg-[#1d4ed8]" : "bg-[#d9d9df]"}`}>1</span>
        {text({ en: "Build", fr: "Construire" })}
      </p>
      <div className="ml-4 mt-2 border-l border-[#e4e4e7] pl-5">
        {BUILD_STEPS.map((item) => {
          const isActive = active === item.value;
          return (
            <button key={item.value} type="button" onClick={() => onSelect(item.value)}
              aria-current={isActive ? "step" : undefined}
              className={`flex items-center gap-2 py-2.5 text-left text-[15px] ${isActive ? "font-bold text-black" : "text-[#b9b9c0] hover:text-[#6d6d70]"}`}>
              <span className={`size-2.5 rounded-full ${isActive ? "bg-black" : "bg-[#d9d9df]"}`} aria-hidden="true" />
              {text({ en: item.label, fr: item.label })}
            </button>
          );
        })}
      </div>
      <button type="button" onClick={() => onSelect("recruit")}
        aria-current={active === "recruit" ? "step" : undefined}
        className={`mt-6 flex items-center gap-2 text-[17px] font-semibold ${active === "recruit" ? "text-[#1d4ed8]" : "text-[#b9b9c0] hover:text-[#6d6d70]"}`}>
        {number(2, active === "recruit")}{text({ en: "Recruit", fr: "Recruter" })}
      </button>
      <button type="button" onClick={() => onSelect("publish")}
        aria-current={active === "publish" ? "step" : undefined}
        className={`mt-6 flex items-center gap-2 text-[17px] font-semibold ${active === "publish" ? "text-[#1d4ed8]" : "text-[#b9b9c0] hover:text-[#6d6d70]"}`}>
        {number(3, active === "publish")}{text({ en: "Publish", fr: "Publier" })}
      </button>
    </nav>
  );
}
