import * as React from "react";
import { cn } from "@/lib/utils";

type BluecrestBadgeProps = React.HTMLAttributes<HTMLSpanElement> & {
  tone?: "neutral" | "active" | "blue";
};

export function BluecrestBadge({ className, tone = "neutral", ...props }: BluecrestBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-3.5 py-1.5 text-xs font-semibold tracking-[-0.01em] backdrop-blur-xl",
        tone === "neutral" && "border-black/[0.05] bg-black/[0.05] text-carbon",
        tone === "active" && "border-[#30d158]/25 bg-[#30d158]/10 text-[#167c32]",
        tone === "blue" && "border-signal-blue/15 bg-signal-blue/10 text-[#0066cc]",
        className,
      )}
      {...props}
    />
  );
}
