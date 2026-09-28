import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { WorkspaceShell, useWorkspaceNav } from "@/components/workspace/WorkspaceShell";
import { RecruitPanel, type RecruitSummary } from "@/components/workspace/RecruitPanel";
import { OrderSidebar } from "@/components/workspace/OrderSidebar";
import { StudyHeader } from "@/components/workspace/StudyHeader";
import { StudyRail, type RailStep } from "@/components/workspace/StudyRail";
import { studyQuery, type StudyParams } from "@/components/workspace/studyNav";

export default function Recruit() {
  const nav = useWorkspaceNav();
  const [params] = useSearchParams();
  const [summary, setSummary] = useState<RecruitSummary>({ credits: 244, panelLabel: "~29.7K", speed: 82, participants: 61 });
  const study: StudyParams = {
    method: params.get("method") ?? "card_sort",
    name: params.get("name")?.trim() || "Card Sorting 1",
    lang: params.get("lang") === "ar" ? "ar" : "en",
    project: params.get("project")?.trim() || "hey",
    participants: summary.participants,
  };

  const handleRailSelect = (next: RailStep) => {
    if (next === "recruit") return;
    if (next === "publish") nav.goWithParams(`/publish?${studyQuery(study)}`);
    else nav.goWithParams(`/studies/create?${studyQuery(study)}`);
  };

  return (
    <WorkspaceShell workspaceName={nav.workspaceName} displayName={nav.displayName} firstName={nav.firstName} role={nav.role}
      onSettings={() => nav.goWithParams("/settings")} onBilling={() => nav.goWithParams("/workspace/billing")} onCredits={() => nav.goWithParams("/workspace/credits")} onAccount={() => nav.goWithParams("/account")} onNotifications={() => nav.goWithParams("/account/notifications")} onRefer={() => nav.goWithParams("/account/refer")}>
      <div className="-mx-6 -mt-8 border-b border-[#e8e8ec] bg-[#fafafa] px-6 py-3">
        <StudyHeader studyName={study.name} project={study.project} lang={study.lang} method={study.method} onPublish={() => handleRailSelect("publish")} />
      </div>

      <div className="mt-8 grid gap-10 lg:grid-cols-[200px_minmax(0,1fr)_340px]">
        <aside><StudyRail active="recruit" onSelect={handleRailSelect} /></aside>
        <main className="min-w-0">
          <RecruitPanel onSummary={setSummary} study={study} />
        </main>
        <OrderSidebar participants={summary.participants} panelLabel={summary.panelLabel} speed={summary.speed} />
      </div>
    </WorkspaceShell>
  );
}
