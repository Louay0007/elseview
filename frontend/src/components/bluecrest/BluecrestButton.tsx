import * as React from "react";
import { ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

type BluecrestButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  size?: "sm" | "md";
  showArrow?: boolean;
};

export const BluecrestButton = React.forwardRef<HTMLButtonElement, BluecrestButtonProps>(
  ({ className, children, size = "md", showArrow = false, ...props }, ref) => (
    <button
      ref={ref}
      className={cn(
        "bluecrest-focus inline-flex items-center justify-center gap-2 rounded-full bg-signal-blue font-semibold tracking-[-0.02em] text-white shadow-[inset_0_1px_0_rgba(255,255,255,.34),0_8px_24px_rgba(0,92,230,.24)] transition-all duration-300 hover:-translate-y-0.5 hover:bg-[#0077ed] hover:shadow-[inset_0_1px_0_rgba(255,255,255,.42),0_12px_30px_rgba(0,92,230,.32)] active:translate-y-0 active:scale-[.98] disabled:pointer-events-none disabled:opacity-50",
        size === "md" ? "min-h-12 px-6 py-3 text-[15px]" : "min-h-9 px-4 py-2 text-[13px]",
        className,
      )}
      {...props}
    >
      {children}
      {showArrow && <ArrowRight className="h-4 w-4" strokeWidth={2.25} aria-hidden="true" />}
    </button>
  ),
);
BluecrestButton.displayName = "BluecrestButton";
