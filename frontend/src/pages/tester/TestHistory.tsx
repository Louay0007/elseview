import { useMemo } from "react";
import { CheckCircle2, Clock, Flag, MinusCircle } from "lucide-react";
import { useAuthLocale } from "@/components/auth/AuthLocale";
import { TesterAccountLayout } from "@/components/tester/TesterAccountHeader";
import { TesterShell } from "@/components/tester/TesterShell";
import { authWords as words } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { readTesterProfile } from "./testerProfileStore";
import { mockTestHistory } from "./testerMocks";

const copy = {
  intro: words("Every test you have taken, newest first.", "Tous les tests que vous avez passés, du plus récent au plus ancien."),
  totalTests: words("Total number of tests", "Nombre total de tests"),
  completed: words("Completed", "Terminés"),
  abandoned: words("Abandoned", "Abandonnés"),
  reported: words("Reported", "Signalés"),
  avgTime: words("Average time", "Temps moyen"),
  completionRate: words("Completion rate", "Taux de complétion"),
  min: words("min", "min"),
};

/** A count that pads to two digits so the column of totals stays visually aligned. */
const count = (value: number) => String(value).padStart(2, "0");

export default function TesterTestHistory() {
  const { text } = useAuthLocale();
  const firstName = useMemo(() => readTesterProfile().firstName.trim() || undefined, []);

  const totals = useMemo(() => {
    const items = mockTestHistory;
    return {
      total: items.length,
      completed: items.filter((item) => item.status === "completed").length,
      abandoned: items.filter((item) => item.status === "abandoned").length,
      reported: items.filter((item) => item.status === "reported").length,
      averageMinutes: items.length
        ? Math.round(items.reduce((sum, item) => sum + item.minutes, 0) / items.length)
        : 0,
    };
  }, []);

  const completionRate = totals.total ? Math.round((totals.completed / totals.total) * 100) : 0;

  return (
    <TesterShell>
      <TesterAccountLayout active="history" firstName={firstName}>

      <p className="mt-5 max-w-[68ch] text-[14.5px] leading-relaxed text-[#0F1E3D]">{text(copy.intro)}</p>

      <div className="mt-7 grid gap-4 sm:grid-cols-2">
        <article className="rounded-2xl border border-[#DCE4F2] bg-[#F7F9FD] p-5 sm:p-6">
          <p className="text-[13px] font-semibold text-[#5A6B87]">{text(copy.totalTests)}</p>
          <p className="mt-3 text-[44px] font-bold leading-none tracking-[-0.03em] text-[#1E3A8A]">{count(totals.total)}</p>
          <dl className="mt-4 space-y-1.5 text-[13.5px] text-[#0F1E3D]">
            {[
              { label: copy.completed, value: totals.completed, icon: CheckCircle2, tone: "text-[#1E3A8A]" },
              { label: copy.abandoned, value: totals.abandoned, icon: MinusCircle, tone: "text-[#5A6B87]" },
              { label: copy.reported, value: totals.reported, icon: Flag, tone: "text-[#B42318]" },
            ].map(({ label, value, icon: Icon, tone }) => (
              <div key={label.en} className="flex items-center gap-2">
                <Icon className={cn("size-4 shrink-0", tone)} strokeWidth={1.8} aria-hidden="true" />
                <dt className="sr-only">{text(label)}</dt>
                <dd className="flex items-baseline gap-1.5">
                  <span className="font-semibold tabular-nums">{count(value)}</span>
                  <span className="text-[#5A6B87]">{text(label)}</span>
                </dd>
              </div>
            ))}
          </dl>
        </article>

        <article className="rounded-2xl border border-[#DCE4F2] bg-[#F7F9FD] p-5 sm:p-6">
          <p className="flex items-center gap-2 text-[13px] font-semibold text-[#5A6B87]">
            <Clock className="size-4 text-[#1E3A8A]" strokeWidth={1.8} aria-hidden="true" />
            {text(copy.avgTime)}
          </p>
          <p className="mt-3 text-[24px] font-bold leading-none tracking-[-0.02em] text-[#0F1E3D]">
            {totals.averageMinutes} <span className="text-[15px] font-semibold text-[#5A6B87]">{text(copy.min)}</span>
          </p>
          <p className="mt-3 text-[13px] text-[#5A6B87]">{text(copy.completionRate)} · {completionRate}%</p>
        </article>
      </div>
      </TesterAccountLayout>
    </TesterShell>
  );
}
