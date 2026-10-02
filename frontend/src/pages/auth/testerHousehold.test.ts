import { describe, expect, it } from "vitest";
import { clampHouseholdSize, HOUSEHOLD_MAX, HOUSEHOLD_MIN, testerHouseholdValid, type TesterHouseholdDraft } from "./testerHousehold";

const base: TesterHouseholdDraft = {
  housingStatus: "rent-private",
  livingArrangements: "family",
  monthlyIncome: "1000-2000",
  householdSize: 4,
};

describe("clampHouseholdSize", () => {
  it("keeps values inside the allowed range", () => {
    expect(clampHouseholdSize(0)).toBe(HOUSEHOLD_MIN);
    expect(clampHouseholdSize(-3)).toBe(HOUSEHOLD_MIN);
    expect(clampHouseholdSize(1)).toBe(1);
    expect(clampHouseholdSize(99)).toBe(HOUSEHOLD_MAX);
  });
  it("rounds and recovers from non-finite input", () => {
    expect(clampHouseholdSize(3.6)).toBe(4);
    expect(clampHouseholdSize(Number.NaN)).toBe(HOUSEHOLD_MIN);
  });
});

describe("testerHouseholdValid", () => {
  it("accepts a fully answered household", () => {
    expect(testerHouseholdValid(base)).toBe(true);
  });

  it("requires each dropdown", () => {
    expect(testerHouseholdValid({ ...base, housingStatus: "" })).toBe(false);
    expect(testerHouseholdValid({ ...base, livingArrangements: "" })).toBe(false);
    expect(testerHouseholdValid({ ...base, monthlyIncome: "" })).toBe(false);
  });

  it("rejects values that are not real options", () => {
    expect(testerHouseholdValid({ ...base, housingStatus: "castle" })).toBe(false);
    expect(testerHouseholdValid({ ...base, monthlyIncome: "a-million" })).toBe(false);
  });

  it("rejects household sizes outside the bounds or non-integers", () => {
    expect(testerHouseholdValid({ ...base, householdSize: 0 })).toBe(false);
    expect(testerHouseholdValid({ ...base, householdSize: HOUSEHOLD_MAX + 1 })).toBe(false);
    expect(testerHouseholdValid({ ...base, householdSize: 2.5 })).toBe(false);
    expect(testerHouseholdValid({ ...base, householdSize: Number.NaN })).toBe(false);
  });

  it("accepts the range boundaries", () => {
    expect(testerHouseholdValid({ ...base, householdSize: HOUSEHOLD_MIN })).toBe(true);
    expect(testerHouseholdValid({ ...base, householdSize: HOUSEHOLD_MAX })).toBe(true);
  });
});
