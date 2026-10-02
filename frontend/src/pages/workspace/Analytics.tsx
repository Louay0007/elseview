import { BarChart3, Bot, ClipboardCheck, FlaskConical, ShieldCheck, Trophy, Users, Wallet } from "lucide-react";
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { useAuthLocale } from "@/components/auth/AuthLocale";
import { BackToHome, KpiGrid, WorkspaceShell, useWorkspaceNav } from "@/components/workspace/WorkspaceShell";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Progress } from "@/components/ui/progress";
import { useEffect as useLiveEffect, useState as useLiveState } from "react";
import { apiFetch, backendAvailable } from "@/lib/api";
import { useWorkspace as useLiveWs } from "@/components/workspace/WorkspaceContext";
import { aiOps, checkSplit as mockSplit, launches as mockLaunches, methodShare as mockShare, reports, reviewQueue as mockQueue, replyTrend as mockTrend, studies } from "./workspaceData";

const PIE_COLORS = ["#1d4ed8", "#f59e0b", "#6d6d70"];
const TOTAL_REPLIES = 424;
const leaderboard = [...studies].sort((a, b) => b.replies - a.replies);

export default function Analytics() {
  const { text } = useAuthLocale();
  const { workspaceId: liveWs } = useLiveWs();
  const [replyTrend, setTrend] = useLiveState(mockTrend);
  const [methodShare, setShare] = useLiveState(mockShare);
  const [checkSplit, setSplit] = useLiveState(mockSplit);
  const [launches, setLaunches] = useLiveState(mockLaunches);
  const [reviewQueue, setQueue] = useLiveState(mockQueue);
  useLiveEffect(() => { if (!backendAvailable() || !liveWs) return;
    const g = async (path: string, set: (v: never) => void, key: string) => { try { const r = await apiFetch<{ items: never[] }>(`/workspaces/${liveWs}/analytics/${path}`); if (r.items?.length) set(r.items as never); } catch { /* keep mock */ } void key; };
    void g("replies-trend", setTrend as never, "t"); void g("method-share", setShare as never, "m");
    void g("check-split", setSplit as never, "c"); void g("launches", setLaunches as never, "l"); void g("review-queue", setQueue as never, "q");
  }, [liveWs]);
  const { firstName, role, displayName, workspaceName, goWithParams } = useWorkspaceNav();

  return (
      <WorkspaceShell >
      <BackToHome />
      <p className="mt-6 text-[13px] font-medium uppercase tracking-[0.08em] text-[#6d6d70]">{text({ en: "Your work", fr: "Votre travail" })}</p>
      <h1 className="mt-1 flex items-center gap-3 text-[30px] font-bold tracking-[-0.02em] text-black">
      <BarChart3 className="size-8" strokeWidth={1.6} aria-hidden="true" />
        {text({ en: "Analytics", fr: "Stats" })}
      </h1>
      <p className="mt-3 max-w-[72ch] text-[16px] leading-relaxed text-[#6d6d70]">
        {text({ en: "Replies, checks, reports.", fr: "Réponses, vérifications et rapports, au même endroit." })}
      </p>

      <KpiGrid items={[
        { icon: FlaskConical, label: { en: "Studies", fr: "Études" }, value: "2 live · 1 draft", sub: "Ready to share" },
        { icon: Users, label: { en: "Replies", fr: "Réponses" }, value: "424 replies", sub: "Only good replies counted" },
        { icon: ClipboardCheck, label: { en: "To check", fr: "À vérifier" }, value: "3 to check", sub: "Checked by 2 people" },
        { icon: Wallet, label: { en: "Money", fr: "Argent" }, value: "Money and pay", sub: "Paid by hand" },
      ]} />

      <div className="mt-8 grid gap-4 lg:grid-cols-5">
      <Card className="rounded-[22px] lg:col-span-3">
      <CardHeader>
      <CardTitle>{text({ en: "Replies over time", fr: "Réponses dans le temps" })}</CardTitle>
      <CardDescription>{text({ en: "New replies per week.", fr: "Nouvelles réponses par semaine." })}</CardDescription>
      </CardHeader>
      <CardContent>
      <div className="h-[260px] w-full">
      <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={replyTrend} margin={{ top: 8, right: 8, bottom: 0, left: -12 }}>
      <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" />
      <XAxis dataKey="week" tick={{ fontSize: 12, fill: "#6d6d70" }} tickLine={false} axisLine={{ stroke: "#e4e4e7" }} />
      <YAxis tick={{ fontSize: 12, fill: "#6d6d70" }} tickLine={false} axisLine={false} />
      <Tooltip />
      <Area type="monotone" dataKey="replies" name="Replies" stroke="#1d4ed8" strokeWidth={2.5} fill="#dbeafe" />
      </AreaChart>
      </ResponsiveContainer>
      </div>
      </CardContent>
      </Card>

      <Card className="rounded-[22px] lg:col-span-2">
      <CardHeader>
      <CardTitle>{text({ en: "Check results", fr: "Résultats des vérifs" })}</CardTitle>
      <CardDescription>{text({ en: "Accepted, flagged, or rejected.", fr: "Acceptées, signalées ou rejetées." })}</CardDescription>
      </CardHeader>
      <CardContent>
      <div className="h-[220px] w-full">
      <ResponsiveContainer width="100%" height="100%">
      <PieChart>
      <Pie data={checkSplit} dataKey="value" nameKey="name" innerRadius={55} outerRadius={85} paddingAngle={3}>
                    {checkSplit.map((entry, i) => (
      <Cell key={entry.name} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                    ))}
      </Pie>
      <Tooltip />
      </PieChart>
      </ResponsiveContainer>
      </div>
      <ul className="mt-2 space-y-1.5">
              {checkSplit.map((c, i) => (
      <li key={c.name} className="flex items-center gap-2 text-sm text-[#3a3a3c]">
      <span className="size-3 rounded-full" style={{ background: PIE_COLORS[i % PIE_COLORS.length] }} aria-hidden="true" />
                  {c.name}: <strong className="text-black">{c.value}</strong>
      </li>
              ))}
      </ul>
      </CardContent>
      </Card>
      </div>

      <Card className="mt-4 rounded-[22px]">
      <CardHeader>
      <CardTitle>{text({ en: "Replies by way to test", fr: "Réponses par façon de tester" })}</CardTitle>
      <CardDescription>{text({ en: "Top tests by replies.", fr: "Quels tests apportent le plus de réponses." })}</CardDescription>
      </CardHeader>
      <CardContent>
      <div className="h-[240px] w-full">
      <ResponsiveContainer width="100%" height="100%">
      <BarChart data={methodShare} margin={{ top: 8, right: 8, bottom: 0, left: -12 }}>
      <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" />
      <XAxis dataKey="method" tick={{ fontSize: 12, fill: "#6d6d70" }} tickLine={false} axisLine={{ stroke: "#e4e4e7" }} />
      <YAxis tick={{ fontSize: 12, fill: "#6d6d70" }} tickLine={false} axisLine={false} />
      <Tooltip />
      <Bar dataKey="replies" name="Replies" fill="#1d4ed8" radius={[8, 8, 0, 0]} />
      </BarChart>
      </ResponsiveContainer>
      </div>
      </CardContent>
      </Card>

      <Card className="mt-8 rounded-[22px]">
      <CardHeader>
      <CardTitle className="flex items-center gap-2"><Trophy className="size-5" />{text({ en: "Top studies by replies", fr: "Études en tête" })}</CardTitle>
      <CardDescription>{text({ en: "Ranked by replies, with each share of all 424.", fr: "Classées par réponses, avec la part de chacune sur 424." })}</CardDescription>
      </CardHeader>
      <CardContent>
      <Table>
      <TableHeader><TableRow><TableHead>{text({ en: "Rank", fr: "Rang" })}</TableHead><TableHead>{text({ en: "Study", fr: "Étude" })}</TableHead><TableHead>{text({ en: "Replies", fr: "Réponses" })}</TableHead><TableHead>{text({ en: "Share", fr: "Part" })}</TableHead></TableRow></TableHeader>
      <TableBody>
              {leaderboard.map((s, i) => {
                const share = Math.round((s.replies / TOTAL_REPLIES) * 100);
                return (
      <TableRow key={s.title}>
      <TableCell className="text-lg font-bold text-black">#{i + 1}</TableCell>
      <TableCell><p className="font-semibold text-black">{s.title}</p><p className="text-xs text-[#6d6d70]">{s.method}</p></TableCell>
      <TableCell className="text-sm">{s.replies} replies</TableCell>
      <TableCell><p className="text-sm font-semibold text-black">{share}%</p><Progress value={share} className="mt-2 h-1.5 w-32" aria-label={`${s.title} share`} /></TableCell>
      </TableRow>
                );
              })}
      </TableBody>
      </Table>
      </CardContent>
      </Card>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        {launches.map((l) => (
      <Card key={l.name} className="rounded-[22px]">
      <CardHeader><CardTitle className="text-lg">{l.name}</CardTitle><CardDescription>{l.screener} · {l.delivery}</CardDescription></CardHeader>
      <CardContent><p className="text-sm font-medium">{l.quota}</p><Progress value={l.pct} className="mt-2 h-2" /><Badge className="mt-3" variant="secondary">{l.label}</Badge></CardContent>
      </Card>
        ))}
      </div>

      <Card className="mt-4 rounded-[22px]">
      <CardHeader><CardTitle>{text({ en: "Checks by people", fr: "Vérifs par des gens" })}</CardTitle><CardDescription>{text({ en: "Two people check, then a final choice. AI never blocks pay.", fr: "Deux vérificateurs relisent chaque réponse. L’IA ne bloque jamais le paiement." })}</CardDescription></CardHeader>
      <CardContent>
      <Table><TableHeader><TableRow><TableHead>{text({ en: "Reply", fr: "Réponse" })}</TableHead><TableHead>{text({ en: "Issue", fr: "Problème" })}</TableHead><TableHead>{text({ en: "Votes", fr: "Votes" })}</TableHead><TableHead>{text({ en: "Next", fr: "Suite" })}</TableHead></TableRow></TableHeader>
      <TableBody>{reviewQueue.map((r) => (<TableRow key={r.session}><TableCell className="text-sm font-medium">{r.session}</TableCell><TableCell>{r.flags}</TableCell><TableCell>{r.votes}</TableCell><TableCell><Badge variant="outline">{r.next}</Badge></TableCell></TableRow>))}</TableBody>
      </Table>
      </CardContent>
      </Card>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
      <Card className="rounded-[22px]">
      <CardHeader><CardTitle>{text({ en: "Results and reports", fr: "Résultats et rapports" })}</CardTitle><CardDescription>{text({ en: "Final numbers. Small groups are hidden.", fr: "Chiffres définitifs. Petits groupes masqués." })}</CardDescription></CardHeader>
      <CardContent className="space-y-3">{reports.map((r) => (<div key={r.name} className="rounded-[14px] border border-[#e4e4e7] p-3"><p className="text-sm font-semibold">{r.name}</p><p className="text-xs text-[#6d6d70]">{r.detail}</p><Badge className="mt-2" variant={r.state === "Approved" ? "default" : "secondary"}>{r.state}</Badge></div>))}</CardContent>
      </Card>
      <Card className="rounded-[22px] border-[#1d4ed8]/30">
      <CardHeader><CardTitle className="flex items-center gap-2"><Bot className="size-5" />{text({ en: "AI help — first drafts only", fr: "Aide IA — brouillons seulement" })}</CardTitle><CardDescription>{text({ en: "You approve first. Drafts only.", fr: "Vous validez d’abord. Brouillons seulement." })}</CardDescription></CardHeader>
      <CardContent className="space-y-3">{aiOps.map((a) => (<div key={a.title} className="flex items-start justify-between gap-3 rounded-[14px] bg-[#f5f9ff] p-3"><div><p className="text-sm font-semibold">{a.title}</p><p className="text-[13px] text-[#3a3a3c]">{a.desc}</p></div><Badge variant="outline">See cost</Badge></div>))}<p className="flex items-center gap-2 text-[13px] text-[#6d6d70]"><ShieldCheck className="size-4" />{text({ en: "Some work uses no AI. Numbers are made by the app, not by AI.", fr: "Parfois sans IA. Les chiffres viennent de l'app, pas de l'IA." })}</p></CardContent>
      </Card>
      </div>
      </WorkspaceShell>
  );
}
