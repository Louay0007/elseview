import { ArrowUp, Check, Mic, MoreHorizontal, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

type ProductMockupProps = {
  className?: string;
  compact?: boolean;
};

export function ProductMockup({ className, compact = false }: ProductMockupProps) {
  return (
    <div className={cn("overflow-hidden rounded-[26px] border border-white/20 bg-[linear-gradient(145deg,#202127,#101116)] text-white shadow-[inset_0_1px_0_rgba(255,255,255,.18),0_28px_80px_rgba(0,28,90,.3)]", className)}>
      <div className="flex h-11 items-center justify-between border-b border-white/10 bg-white/[0.035] px-4 backdrop-blur-xl">
        <div className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-white/15" /><span className="h-2.5 w-2.5 rounded-full bg-white/15" /><span className="h-2.5 w-2.5 rounded-full bg-signal-blue shadow-[0_0_12px_rgba(10,132,255,.8)]" /></div>
        <span className="font-mono text-[10px] text-white/40">workspace / live</span>
        <MoreHorizontal className="h-4 w-4 text-white/40" />
      </div>
      <div className={cn("grid", compact ? "gap-3 p-4" : "gap-4 p-4 sm:grid-cols-[1.35fr_0.65fr] sm:p-6")}>
        <section className="rounded-[20px] border border-white/10 bg-white/[0.06] p-4 backdrop-blur-xl">
          <div className="mb-5 flex items-center justify-between">
            <div><p className="text-[11px] text-white/40">Live workspace</p><h4 className="mt-1 text-sm font-medium">Product strategy sync</h4></div>
            <span className="flex items-center gap-1.5 rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-[10px] text-white/70"><span className="h-1.5 w-1.5 rounded-full bg-signal-blue" />Active</span>
          </div>
          <div className="space-y-3">
            {["Align launch timeline with the product team", "Review the highest-impact customer requests", "Confirm ownership for the next release"].map((text, index) => (
              <div key={text} className="flex items-start gap-3 rounded-lg bg-black/20 p-3">
                <span className={cn("mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full", index === 0 ? "bg-signal-blue" : "border border-white/15")}>
                  {index === 0 && <Check className="h-3 w-3" />}
                </span>
                <span className="text-xs leading-5 text-white/70">{text}</span>
              </div>
            ))}
          </div>
        </section>
        {!compact && (
          <section className="flex min-h-52 flex-col rounded-[20px] border border-white/10 bg-white/[0.07] p-4 backdrop-blur-2xl">
            <div className="flex items-center gap-2 text-xs font-medium"><Sparkles className="h-3.5 w-3.5 text-hover-glow" />Assistant</div>
            <p className="mt-4 text-xs leading-5 text-white/50">Your conversation highlights and next-step suggestions will appear here.</p>
            <div className="mt-auto rounded-[16px] border border-white/10 bg-black/20 p-2.5 shadow-inset backdrop-blur-xl">
              <div className="flex items-center gap-2">
                <Mic className="h-4 w-4 text-white/30" />
                <span className="flex-1 text-xs text-white/30">Ask a question...</span>
                <button aria-label="Send question" className="bluecrest-focus flex h-8 w-8 items-center justify-center rounded-full bg-signal-blue shadow-[inset_0_1px_0_rgba(255,255,255,.3),0_5px_14px_rgba(10,132,255,.3)]"><ArrowUp className="h-3.5 w-3.5" /></button>
              </div>
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
