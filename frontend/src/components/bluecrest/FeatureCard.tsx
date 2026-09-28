import * as React from "react";
import { cn } from "@/lib/utils";

type FeatureCardProps = React.HTMLAttributes<HTMLElement> & {
  variant?: "white" | "frost";
  eyebrow?: string;
  title: string;
  description: string;
};

export function FeatureCard({ className, variant = "white", eyebrow, title, description, children, ...props }: FeatureCardProps) {
  return (
    <article
      className={cn(
        "rounded-[30px] border p-6 shadow-[inset_0_1px_0_rgba(255,255,255,.9),0_18px_55px_rgba(31,73,125,.08)] sm:p-7",
        variant === "frost"
          ? "border-white/80 bg-[linear-gradient(145deg,rgba(255,255,255,.9),rgba(232,244,255,.72))]"
          : "border-black/[0.07] bg-white/80 backdrop-blur-xl",
        className,
      )}
      {...props}
    >
      {eyebrow && <p className="mb-3 text-xs font-semibold uppercase tracking-[0.08em] text-fog">{eyebrow}</p>}
      <h3 className="text-[22px] font-semibold leading-[1.2] tracking-[-0.035em] text-carbon">{title}</h3>
      <p className="mt-2 text-[16px] leading-6 tracking-[-0.018em] text-steel">{description}</p>
      {children && <div className="mt-6">{children}</div>}
    </article>
  );
}
