import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/utils";

type MarqueeProps = HTMLAttributes<HTMLDivElement> & {
  children: ReactNode;
  pauseOnHover?: boolean;
  reverse?: boolean;
  repeat?: number;
};

export function Marquee({
  children,
  className,
  pauseOnHover = false,
  reverse = false,
  repeat = 2,
  ...props
}: MarqueeProps) {
  return (
    <div
      className={cn(
        "group flex overflow-hidden py-2 [--gap:1rem] [gap:var(--gap)]",
        className,
      )}
      {...props}
    >
      {Array.from({ length: repeat }, (_, index) => (
        <div
          key={index}
          aria-hidden={index > 0 || undefined}
          style={{ animationDirection: reverse ? "reverse" : "normal" }}
          className={cn(
            "flex min-w-full shrink-0 items-stretch justify-around [gap:var(--gap)] [animation:marquee_var(--duration)_linear_infinite]",
            pauseOnHover &&
              "group-hover:[animation-play-state:paused] group-focus-within:[animation-play-state:paused]",
          )}
        >
          {children}
        </div>
      ))}
    </div>
  );
}
