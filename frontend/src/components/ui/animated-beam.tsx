"use client";

import { motion } from "framer-motion";
import { forwardRef, useEffect, useId, useState, type ReactNode, type RefObject } from "react";
import { cn } from "@/lib/utils";

type AnimatedBeamProps = {
  containerRef: RefObject<HTMLElement>;
  fromRef: RefObject<HTMLElement>;
  toRef: RefObject<HTMLElement>;
  className?: string;
  curvature?: number;
  reverse?: boolean;
  duration?: number;
  delay?: number;
  pathColor?: string;
  pathWidth?: number;
  pathOpacity?: number;
  gradientStartColor?: string;
  gradientStopColor?: string;
};

export function AnimatedBeam({
  containerRef, fromRef, toRef, className, curvature = 0, reverse = false,
  duration = 3.5, delay = 0, pathColor = "#cfe4fb", pathWidth = 1.5,
  pathOpacity = 0.75, gradientStartColor = "#64d2ff", gradientStopColor = "#0a84ff",
}: AnimatedBeamProps) {
  const id = useId().replace(/:/g, "");
  const [geometry, setGeometry] = useState({ path: "", width: 0, height: 0 });

  useEffect(() => {
    const update = () => {
      const container = containerRef.current;
      const from = fromRef.current;
      const to = toRef.current;
      if (!container || !from || !to) return;

      const root = container.getBoundingClientRect();
      const start = from.getBoundingClientRect();
      const end = to.getBoundingClientRect();
      const startX = start.left - root.left + start.width / 2;
      const startY = start.top - root.top + start.height / 2;
      const endX = end.left - root.left + end.width / 2;
      const endY = end.top - root.top + end.height / 2;

      setGeometry({
        width: root.width,
        height: root.height,
        path: `M ${startX},${startY} Q ${(startX + endX) / 2},${startY - curvature} ${endX},${endY}`,
      });
    };

    const observer = new ResizeObserver(update);
    if (containerRef.current) observer.observe(containerRef.current);
    update();
    return () => observer.disconnect();
  }, [containerRef, curvature, fromRef, toRef]);

  const coordinates = reverse
    ? { x1: ["110%", "-10%"], x2: ["100%", "-20%"] }
    : { x1: ["-10%", "110%"], x2: ["-20%", "100%"] };

  return (
    <svg aria-hidden="true" className={cn("pointer-events-none absolute inset-0 z-0", className)} width={geometry.width} height={geometry.height} viewBox={`0 0 ${geometry.width} ${geometry.height}`} fill="none">
      <path d={geometry.path} stroke={pathColor} strokeWidth={pathWidth} strokeOpacity={pathOpacity} />
      {geometry.path && (
        <>
          <motion.path d={geometry.path} stroke={`url(#${id})`} strokeWidth={pathWidth * 1.8} strokeLinecap="round" />
          <defs>
            <motion.linearGradient
              id={id}
              gradientUnits="userSpaceOnUse"
              initial={{ x1: coordinates.x1[0], x2: coordinates.x2[0], y1: "0%", y2: "0%" }}
              animate={{ x1: coordinates.x1, x2: coordinates.x2 }}
              transition={{ duration, delay, ease: [0.16, 1, 0.3, 1], repeat: Infinity }}
            >
              <stop stopColor={gradientStartColor} stopOpacity="0" />
              <stop offset="42%" stopColor={gradientStartColor} />
              <stop offset="62%" stopColor={gradientStopColor} />
              <stop offset="100%" stopColor={gradientStopColor} stopOpacity="0" />
            </motion.linearGradient>
            <filter id={`${id}-glow`} x="-300%" y="-300%" width="700%" height="700%">
              <feGaussianBlur stdDeviation="4" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>
          <circle r="9" fill={gradientStartColor} opacity="0.42" filter={`url(#${id}-glow)`}>
            <animateMotion
              key={`${geometry.path}-glow`}
              dur={`${duration}s`}
              begin={`${delay}s`}
              repeatCount="indefinite"
              path={geometry.path}
              keyPoints={reverse ? "1;0" : "0;1"}
              keyTimes="0;1"
              calcMode="spline"
              keySplines="0.4 0 0.2 1"
            />
          </circle>
          <circle r="4" fill="#ffffff" stroke={gradientStopColor} strokeWidth="2" filter={`url(#${id}-glow)`}>
            <animateMotion
              key={`${geometry.path}-core`}
              dur={`${duration}s`}
              begin={`${delay}s`}
              repeatCount="indefinite"
              path={geometry.path}
              keyPoints={reverse ? "1;0" : "0;1"}
              keyTimes="0;1"
              calcMode="spline"
              keySplines="0.4 0 0.2 1"
            />
          </circle>
        </>
      )}
    </svg>
  );
}

export const Circle = forwardRef<HTMLDivElement, { className?: string; children?: ReactNode; label?: string }>(
  ({ className, children, label }, ref) => (
    <div ref={ref} aria-label={label} className={cn("relative z-10 flex size-12 shrink-0 items-center justify-center rounded-full border border-[#dce8f6] bg-white text-[#0a84ff] shadow-[0_10px_32px_-18px_rgba(0,45,105,.38)]", className)}>
      {children}
    </div>
  ),
);

Circle.displayName = "Circle";
