import { describe, expect, it } from "vitest";
import {
  allocatedSum,
  clampInt,
  clampMaxLength,
  clampMultiBounds,
  constantSumError,
  filledValues,
  isValidTarget,
  moveItem,
  moveTarget,
  multiBoundsError,
  optionsError,
  questionError,
  scaleCount,
  scaleValues,
  targetFromPoint,
  validateLocalFile,
} from "./validation";

describe("filledValues", () => {
  it("keeps only non-empty strings", () => {
    expect(filledValues(["a", "  ", "", 1, null, "b "])).toEqual(["a", "b "]);
  });
  it("returns [] for non-arrays", () => {
    expect(filledValues(undefined)).toEqual([]);
  });
});

describe("question / options errors", () => {
  it("flags empty questions", () => {
    expect(questionError("  ")).toBe("empty-question");
    expect(questionError("Why?")).toBeNull();
  });
  it("requires two non-empty options", () => {
    expect(optionsError(["a", " "], 2)).toBe("too-few-options");
    expect(optionsError(["a", "b"], 2)).toBeNull();
  });
});

describe("scales and limits", () => {
  it("resolves scale counts with a safe default", () => {
    expect(scaleCount("1-7")).toBe(7);
    expect(scaleCount("1-10")).toBe(10);
    expect(scaleCount("bogus")).toBe(5);
    expect(scaleValues("1-5")).toEqual([1, 2, 3, 4, 5]);
  });
  it("clamps selection bounds inside option count", () => {
    expect(clampMultiBounds(5, 9, 4)).toEqual({ min: 4, max: 4 });
    expect(multiBoundsError(2, 5, 4)).toBe("max-exceeds-options");
    expect(multiBoundsError(1, 3, 4)).toBeNull();
  });
  it("clamps char limits to a sensible range", () => {
    expect(clampMaxLength(3)).toBe(50);
    expect(clampMaxLength(99999)).toBe(5000);
    expect(clampInt("x", 1, 10, 4)).toBe(4);
  });
});

describe("constant sum", () => {
  it("sums non-negative allocations", () => {
    expect(allocatedSum([40, 60, -5, "x"])).toBe(100);
  });
  it("rejects mismatched and negative totals", () => {
    expect(constantSumError([40, 50], 100, 2)).toBe("sum-mismatch");
    expect(constantSumError([40, -1], 100, 2)).toBe("negative-allocation");
    expect(constantSumError([50, 50], 100, 2)).toBeNull();
    expect(constantSumError([50], 100, 1)).toBe("too-few-options");
  });
});

describe("local file validation", () => {
  it("rejects wrong types and oversize files", () => {
    expect(validateLocalFile(null, ["image/png"], 8)).toBe("missing-file");
    expect(validateLocalFile({ type: "image/gif", size: 10 }, ["image/png"], 8)).toBe("invalid-type");
    expect(validateLocalFile({ type: "image/png", size: 9 }, ["image/png"], 8)).toBe("too-large");
    expect(validateLocalFile({ type: "image/png", size: 8 }, ["image/png"], 8)).toBeNull();
  });
});

describe("first-click target geometry", () => {
  it("builds a clamped box around a click", () => {
    const t = targetFromPoint(0.5, 0.5);
    expect(t && isValidTarget(t)).toBe(true);
    expect(targetFromPoint(2, 0)).toBeNull();
  });
  it("moves without leaving the image", () => {
    const t = targetFromPoint(0.95, 0.95)!;
    const moved = moveTarget(t, 0.1, 0.1);
    expect(moved.x + moved.w).toBeLessThanOrEqual(1);
    expect(isValidTarget({ x: 0, y: 0, w: 0, h: 1 })).toBe(false);
  });
  it("reorders items symmetrically", () => {
    expect(moveItem(["a", "b", "c"], 0, 1)).toEqual(["b", "a", "c"]);
    expect(moveItem(["a"], 0, -1)).toEqual(["a"]);
  });
});
