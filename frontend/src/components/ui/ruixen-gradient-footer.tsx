"use client";

import {
  useEffect,
  useId,
  useRef,
  useState,
  type CSSProperties,
  type ReactNode,
} from "react";

type Stop = { offset: number; color: string };

const VBW = 1271;
const VBH = 599;

const RUIXEN_STOPS: Stop[] = [
  { offset: 0, color: "#07172F" },
  { offset: 0.2, color: "#0A3A78" },
  { offset: 0.4, color: "#0A84FF" },
  { offset: 0.6, color: "#64D2FF" },
  { offset: 0.78, color: "#E1ECFE" },
  { offset: 0.9, color: "#FFFFFF" },
  { offset: 1, color: "#FFFFFF00" },
];

function bellHeights(n: number, peak: number, valley: number): number[] {
  const output: number[] = [];
  const midpoint = (n - 1) / 2;

  for (let index = 0; index < n; index += 1) {
    const distance = midpoint === 0 ? 0 : Math.abs(index - midpoint) / midpoint;
    const eased = 1 - Math.pow(distance, 1.24);
    output.push(peak * VBH * (valley + (1 - valley) * eased));
  }

  return output;
}

const clamp01 = (value: number) => Math.max(0, Math.min(1, value));

export interface RuixenGradientFooterProps {
  children?: ReactNode;
  gradientHeight?: string;
  minReveal?: number;
  bars?: number;
  blur?: number;
  peak?: number;
  valley?: number;
  stops?: Stop[];
  className?: string;
  style?: CSSProperties;
}

export function RuixenGradientFooter({
  children,
  gradientHeight = "40vh",
  minReveal = 0.045,
  bars = 9,
  blur = 15,
  peak = 0.98,
  valley = 0.55,
  stops = RUIXEN_STOPS,
  className,
  style,
}: RuixenGradientFooterProps) {
  const uid = useId().replace(/:/g, "");
  const bandRef = useRef<HTMLDivElement>(null);
  const frameRef = useRef<number | null>(null);
  const [progress, setProgress] = useState(minReveal);

  useEffect(() => {
    const element = bandRef.current;
    if (!element) return;

    const documentElement = element.ownerDocument;
    const view = documentElement.defaultView ?? window;

    const measure = () => {
      frameRef.current = null;
      const height = element.offsetHeight || 1;
      const scrollLeft =
        documentElement.documentElement.scrollHeight - view.innerHeight - view.scrollY;
      const reveal = clamp01((height - scrollLeft) / height);
      setProgress(minReveal + (1 - minReveal) * reveal);
    };

    const requestMeasure = () => {
      if (frameRef.current !== null) return;
      frameRef.current = view.requestAnimationFrame(measure);
    };

    measure();
    view.addEventListener("scroll", requestMeasure, { passive: true });
    view.addEventListener("resize", requestMeasure, { passive: true });

    return () => {
      view.removeEventListener("scroll", requestMeasure);
      view.removeEventListener("resize", requestMeasure);
      if (frameRef.current !== null) view.cancelAnimationFrame(frameRef.current);
    };
  }, [minReveal]);

  const columnWidth = VBW / bars;

  return (
    <footer
      className={className}
      style={{ paddingBottom: gradientHeight, ...style }}
    >
      {children}

      <div
        ref={bandRef}
        aria-hidden="true"
        style={{
          position: "fixed",
          left: 0,
          right: 0,
          bottom: 0,
          height: gradientHeight,
          pointerEvents: "none",
          transformOrigin: "bottom",
          transform: `scaleY(${progress})`,
          willChange: "transform",
        }}
      >
        <svg
          className="block h-full w-full"
          viewBox={`0 0 ${VBW} ${VBH}`}
          preserveAspectRatio="none"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <defs>
            <linearGradient id={`grad-${uid}`} x1="0" y1="1" x2="0" y2="0">
              {stops.map((stop) => (
                <stop key={`${stop.offset}-${stop.color}`} offset={stop.offset} stopColor={stop.color} />
              ))}
            </linearGradient>
            <filter id={`blur-${uid}`} x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation={blur} />
            </filter>
          </defs>

          {bellHeights(bars, peak, valley).map((barHeight, index) => (
            <g key={index} filter={`url(#blur-${uid})`}>
              <rect
                x={index * columnWidth}
                y={VBH - barHeight}
                width={columnWidth * 1.23}
                height={barHeight}
                fill={`url(#grad-${uid})`}
              />
            </g>
          ))}
        </svg>
      </div>
    </footer>
  );
}
