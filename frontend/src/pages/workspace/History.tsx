import { useEffect, useState } from "react";
import { apiFetch, backendAvailable } from "@/lib/api";
import { useWorkspace } from "@/components/workspace/WorkspaceContext";
import { BadgeCheck, CalendarDays, FileText, History as HistoryIcon, LayoutGrid } from "lucide-react";
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { useAuthLocale } from "@/components/auth/AuthLocale";
import { BackToHome, KpiGrid, WorkspaceShell, useWorkspaceNav } from "@/components/workspace/WorkspaceShell";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { eventsByType, eventsTrend, historyEvents, studyLifecycle } from "./workspaceData";

const filters = ["All", "Study", "Reply", "Check", "Report", "AI", "People", "Money"] as const;

export default function History() {
  const { text } = useAuthLocale();
  const { firstName, role, displayName, workspaceName, goWithParams } = useWorkspaceNav();
  const [filter, setFilter] = useState<(typeof filters)[number]>("All");
  const [events, setEvents] = useState<{ date: string; type: string; title: string; detail: string }[]>([...historyEvents]);
  type Life = { id?: string; title: string; version: string; last: string; status: string; label: string };
  const [lifecycle, setLifecycle] = useState<Life[]>([...studyLifecycle]);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const { workspaceId } = useWorkspace();

  useEffect(() => {
    if (!backendAvailable() || !workspaceId) return;
    apiFetch<{ items: { id: string; title: string; status: string }[] }>(`/workspaces/${workspaceId}/studies`)
      .then((r) => setLifecycle(r.items.map((x) => ({ id: x.id, title: x.title, version: "", last: "", status: x.status, label: x.status }))))
      .catch(() => {});
    apiFetch<{ items: { id: string; action: string; details: Record<string, unknown>; created_at: string | null }[] }>(`/workspaces/${workspaceId}/analytics/history?kind=${filter}`)
      .then((r) => setEvents(r.items.map((x) => ({ date: (x.created_at ?? "").slice(0, 10), type: x.action.split(".")[0], title: x.action, detail: "" }))))
      .catch(() => {});
  }, [workspaceId, filter]);

  const setStudyState = (id: string, status: "paused" | "ready" | "closed") => {
    if (!backendAvailable() || !workspaceId) {
      setHistoryError(text({ en: "Sign in to change.", fr: "Connectez-vous pour modifier une étude." }));
      return;
    }
    setHistoryError(null);
    void apiFetch(`/workspaces/${workspaceId}/studies/${id}/state`, { method: "PATCH", body: { status } })
      .catch(() => setHistoryError(text({ en: "Update failed.", fr: "Étude non mise à jour." })));
    setLifecycle((current) => current.map((item) => (item.id ?? item.title) === id ? { ...item, status, label: status } : item));
  };
  const shown = events;

  return (
      <WorkspaceShell >
      <BackToHome />
      <p className="mt-6 text-[13px] font-medium uppercase tracking-[0.08em] text-[#6d6d70]">{text({ en: "Your work", fr: "Votre travail" })}</p>
      <h1 className="mt-1 flex items-center gap-3 text-[30px] font-bold tracking-[-0.02em] text-black">
      <HistoryIcon className="size-8" strokeWidth={1.6} aria-hidden="true" />
        {text({ en: "History", fr: "Historique" })}
      </h1>
      <p className="mt-3 max-w-[72ch] text-[16px] leading-relaxed text-[#6d6d70]">
        {text({ en: "All work here. Newest first.", fr: "Tout ce qui s’est passé ici, du plus récent au plus ancien." })}
      </p>

      <KpiGrid items={[
        { icon: HistoryIcon, label: { en: "Events", fr: "Actions" }, value: "95 events", sub: "All time in this workspace" },
        { icon: LayoutGrid, label: { en: "Kinds", fr: "Types" }, value: "7 kinds", sub: "From studies to money" },
        { icon: CalendarDays, label: { en: "Weeks", fr: "Semaines" }, value: "8 weeks", sub: "Of activity in a row" },
        { icon: BadgeCheck, label: { en: "Latest", fr: "Dernier" }, value: "Sep 26", sub: "Checkout report approved" },
      ]} />

      <div className="mt-8 grid gap-4 lg:grid-cols-5">
      <Card className="rounded-[22px] lg:col-span-3">
      <CardHeader>
      <CardTitle>{text({ en: "Over time", fr: "Activité dans le temps" })}</CardTitle>
      <CardDescription>{text({ en: "Per week.", fr: "Actions par semaine." })}</CardDescription>
      </CardHeader>
      <CardContent>
      <div className="h-[260px] w-full">
      <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={eventsTrend} margin={{ top: 8, right: 8, bottom: 0, left: -12 }}>
      <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" />
      <XAxis dataKey="week" tick={{ fontSize: 12, fill: "#6d6d70" }} tickLine={false} axisLine={{ stroke: "#e4e4e7" }} />
      <YAxis tick={{ fontSize: 12, fill: "#6d6d70" }} tickLine={false} axisLine={false} />
      <Tooltip />
      <Area type="monotone" dataKey="events" name="Events" stroke="#1d4ed8" strokeWidth={2.5} fill="#dbeafe" />
      </AreaChart>
      </ResponsiveContainer>
      </div>
      </CardContent>
      </Card>

      <Card className="rounded-[22px] lg:col-span-2">
      <CardHeader>
      <CardTitle>{text({ en: "By kind", fr: "Actions par type" })}</CardTitle>
      <CardDescription>{text({ en: "Most common first.", fr: "Ce qui arrive le plus." })}</CardDescription>
      </CardHeader>
      <CardContent>
      <div className="h-[260px] w-full">
      <ResponsiveContainer width="100%" height="100%">
      <BarChart data={eventsByType} layout="vertical" margin={{ top: 0, right: 12, bottom: 0, left: 8 }}>
      <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" horizontal={false} />
      <XAxis type="number" tick={{ fontSize: 12, fill: "#6d6d70" }} tickLine={false} axisLine={false} />
      <YAxis type="category" dataKey="type" width={64} tick={{ fontSize: 12, fill: "#6d6d70" }} tickLine={false} axisLine={false} />
      <Tooltip />
      <Bar dataKey="events" name="Events" fill="#1d4ed8" radius={[0, 8, 8, 0]} />
      </BarChart>
      </ResponsiveContainer>
      </div>
      </CardContent>
      </Card>
      </div>

      <Card className="mt-8 rounded-[22px]">
      <CardHeader>
      <CardTitle className="flex items-center gap-2"><FileText className="size-5" />{text({ en: "Your studies", fr: "Vos études" })}</CardTitle>
      <CardDescription>{text({ en: "Draft, publish, pause, close.", fr: "Brouillon → publication → pause ou clôture. Les versions publiées sont verrouillées. Mêmes états que le backend : brouillon, en direct, en pause, clôturé." })}</CardDescription>
      </CardHeader>
      <CardContent>
          {historyError && <p role="alert" className="text-sm text-[#b42318]">{historyError}</p>}
      <Table>
      <TableHeader><TableRow><TableHead>{text({ en: "Study", fr: "Étude" })}</TableHead><TableHead>{text({ en: "Last change", fr: "Dernier changement" })}</TableHead><TableHead>{text({ en: "Status", fr: "État" })}</TableHead></TableRow></TableHeader>
      <TableBody>
              {lifecycle.map((item) => (
      <TableRow key={item.title}>
      <TableCell><p className="font-semibold text-black">{item.title}</p><p className="text-xs text-[#6d6d70]">{item.version}</p></TableCell>
      <TableCell className="text-sm text-[#3a3a3c]">{item.last}</TableCell>
      <TableCell>
      <Badge variant={item.status === "live" ? "default" : item.status === "draft" ? "outline" : "secondary"}>{item.label}</Badge>
      <span className="mt-2 flex flex-wrap gap-2">
      <button type="button" className="rounded-full border border-[#e4e4e7] px-3 py-1 text-xs" onClick={() => setStudyState(item.id ?? item.title, "paused")}>{text({ en: "Pause", fr: "Pause" })}</button>
      <button type="button" className="rounded-full border border-[#e4e4e7] px-3 py-1 text-xs" onClick={() => setStudyState(item.id ?? item.title, "ready")}>{text({ en: "Resume", fr: "Reprendre" })}</button>
      <button type="button" className="rounded-full border border-[#e4e4e7] px-3 py-1 text-xs" onClick={() => setStudyState(item.id ?? item.title, "closed")}>{text({ en: "Close", fr: "Clôturer" })}</button>
      </span>
      </TableCell>
      </TableRow>
              ))}
      </TableBody>
      </Table>
      </CardContent>
      </Card>

      <Card className="mt-4 rounded-[22px]">
      <CardHeader>
      <CardTitle>{text({ en: "Full log", fr: "Journal complet" })}</CardTitle>
      <CardDescription>{text({ en: "Newest first.", fr: "Plus récent d’abord. Filtrez par type." })}</CardDescription>
      </CardHeader>
      <CardContent>
      <div className="flex flex-wrap gap-2" role="group" aria-label="Filter history">
            {filters.map((f) => (
      <button
                key={f}
                type="button"
                onClick={() => setFilter(f)}
                aria-pressed={filter === f}
                className={`inline-flex min-h-[40px] items-center rounded-full px-5 text-[14px] font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff] ${filter === f ? "bg-[#18181b] text-white" : "border border-[#e4e4e7] text-black hover:bg-[#f7f8fa]"}`}
              >
                {f === "All" ? text({ en: "All", fr: "Tout" }) : f}
      </button>
            ))}
      </div>
      <Table>
      <TableHeader><TableRow><TableHead>{text({ en: "Date", fr: "Date" })}</TableHead><TableHead>{text({ en: "Kind", fr: "Type" })}</TableHead><TableHead>{text({ en: "What happened", fr: "Quoi" })}</TableHead></TableRow></TableHeader>
      <TableBody>
              {shown.map((e) => (
      <TableRow key={`${e.date}-${e.title}`}>
      <TableCell className="whitespace-nowrap text-sm text-[#6d6d70]">{e.date}</TableCell>
      <TableCell><Badge variant="secondary">{e.type}</Badge></TableCell>
      <TableCell><p className="font-semibold text-black">{e.title}</p><p className="text-sm text-[#6d6d70]">{e.detail}</p></TableCell>
      </TableRow>
              ))}
      </TableBody>
      </Table>
          {shown.length === 0 && (
      <p className="py-6 text-center text-sm text-[#6d6d70]">{text({ en: "Nothing here yet.", fr: "Rien ici pour l'instant." })}</p>
          )}
      </CardContent>
      </Card>
      </WorkspaceShell>
  );
}
