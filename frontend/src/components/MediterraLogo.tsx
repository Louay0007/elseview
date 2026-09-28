import { cn } from "@/lib/utils";

type MediterraLogoProps = {
  className?: string;
  compact?: boolean;
  variant?: "light" | "dark";
};

export function MediterraLogo({ className, compact = false, variant = "light" }: MediterraLogoProps) {
  return (
    <span className={cn("inline-flex items-center gap-3", variant === "dark" && "text-white", className)}>
      <img
        src="/images/brand/elseview-logo.png"
        width={512}
        height={512}
        alt={compact ? "Elseview" : ""}
        aria-hidden={compact ? undefined : true}
        className="size-16 shrink-0 object-contain sm:size-[72px]"
      />
      {!compact && <span className="text-[26px] font-semibold tracking-normal sm:text-[30px]">Elseview</span>}
    </span>
  );
}
