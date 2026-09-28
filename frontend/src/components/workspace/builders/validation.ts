export function filledValues(values: unknown): string[] {
  if (!Array.isArray(values)) return [];
  return values.filter((v): v is string => typeof v === "string" && v.trim().length > 0);
}

export function questionError(question: unknown): string | null {
  return typeof question === "string" && question.trim().length > 0 ? null : "empty-question";
}

export function optionsError(values: unknown, minCount: number): string | null {
  return filledValues(values).length >= minCount ? null : "too-few-options";
}

export function clampInt(value: unknown, min: number, max: number, fallback: number): number {
  const n = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(n)) return fallback;
  return Math.min(max, Math.max(min, Math.floor(n)));
}

export function scaleCount(scale: unknown): 5 | 7 | 10 {
  return scale === "1-7" ? 7 : scale === "1-10" ? 10 : 5;
}

export function scaleValues(scale: unknown): number[] {
  const n = scaleCount(scale);
  return Array.from({ length: n }, (_, i) => i + 1);
}

export function clampMaxLength(value: unknown, fallback = 500): number {
  return clampInt(value, 50, 5000, fallback);
}

export type MultiBounds = { min: number; max: number };

export function clampMultiBounds(
  rawMin: unknown,
  rawMax: unknown,
  optionCount: number,
): MultiBounds {
  const cap = Math.max(1, optionCount);
  const max = clampInt(rawMax, 1, cap, Math.min(3, cap));
  const min = clampInt(rawMin, 1, max, 1);
  return { min, max };
}

export function multiBoundsError(min: number, max: number, optionCount: number): string | null {
  if (max > optionCount) return "max-exceeds-options";
  if (min > max) return "min-exceeds-max";
  return null;
}

export function allocationTotal(value: unknown): number {
  const n = Number(value);
  return n === 10 ? 10 : 100;
}

export function allocatedSum(allocations: unknown): number {
  if (!Array.isArray(allocations)) return 0;
  return allocations.reduce((sum, v) => sum + (typeof v === "number" && Number.isFinite(v) && v >= 0 ? v : 0), 0);
}

export function constantSumError(allocations: unknown, total: number, optionCount: number): string | null {
  if (optionCount < 2) return "too-few-options";
  if (Array.isArray(allocations) && allocations.some((v) => typeof v === "number" && v < 0)) {
    return "negative-allocation";
  }
  return allocatedSum(allocations) === total ? null : "sum-mismatch";
}

export type FileLike = { type: string; size: number };

export function validateLocalFile(
  file: FileLike | null,
  allowedTypes: string[],
  maxBytes: number,
): string | null {
  if (!file) return "missing-file";
  if (!allowedTypes.includes(file.type)) return "invalid-type";
  if (file.size <= 0 || file.size > maxBytes) return "too-large";
  return null;
}

export const IMAGE_TYPES = ["image/png", "image/jpeg"];
export const VIDEO_TYPES = ["video/mp4", "video/webm"];
export const AUDIO_TYPES = ["audio/mpeg", "audio/wav", "audio/x-wav", "audio/mp4"];

export const MB = 1024 * 1024;

export function clamp01(n: number): number {
  return Math.min(1, Math.max(0, n));
}

export type NormTarget = { x: number; y: number; w: number; h: number };

export function targetFromPoint(x: number, y: number, w = 0.24, h = 0.18): NormTarget | null {
  if (![x, y].every(Number.isFinite) || x < 0 || x > 1 || y < 0 || y > 1) return null;
  const tw = clamp01(w) || 0.24;
  const th = clamp01(h) || 0.18;
  return {
    x: clamp01(x - tw / 2),
    y: clamp01(y - th / 2),
    w: Math.min(tw, 1 - clamp01(x - tw / 2)),
    h: Math.min(th, 1 - clamp01(y - th / 2)),
  };
}

export function moveTarget(target: NormTarget, dx: number, dy: number): NormTarget {
  return {
    ...target,
    x: clamp01(Math.min(target.x + dx, 1 - target.w)),
    y: clamp01(Math.min(target.y + dy, 1 - target.h)),
  };
}

export function isValidTarget(t: unknown): t is NormTarget {
  if (typeof t !== "object" || t === null) return false;
  const v = t as Record<string, unknown>;
  return (
    [v.x, v.y, v.w, v.h].every((n) => typeof n === "number" && Number.isFinite(n)) &&
    (v.w as number) > 0 &&
    (v.h as number) > 0 &&
    (v.x as number) >= 0 &&
    (v.y as number) >= 0 &&
    (v.x as number) + (v.w as number) <= 1 &&
    (v.y as number) + (v.h as number) <= 1
  );
}

export function moveItem<T>(items: T[], index: number, dir: -1 | 1): T[] {
  const next = index + dir;
  if (next < 0 || next >= items.length) return items;
  const copy = [...items];
  [copy[index], copy[next]] = [copy[next], copy[index]];
  return copy;
}

export function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes < 0) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
