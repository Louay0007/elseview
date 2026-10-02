import { describe, expect, it } from "vitest";
import { testerLifestyleValid, type TesterLifestyleDraft } from "./testerLifestyle";

const base: TesterLifestyleDraft = {
  noPets: false,
  petsOwned: "dog",
  hobby: "cooking",
  fitness: "gym",
  hasVehicle: "yes",
  shoppingFrequency: "weekly",
};

describe("testerLifestyleValid", () => {
  it("accepts a fully answered profile", () => {
    expect(testerLifestyleValid(base)).toBe(true);
  });

  it("requires the pet answer only when the tester has pets", () => {
    expect(testerLifestyleValid({ ...base, noPets: true, petsOwned: "" })).toBe(true);
    expect(testerLifestyleValid({ ...base, noPets: false, petsOwned: "" })).toBe(false);
  });

  it("always requires hobby, fitness, vehicle and shopping frequency", () => {
    expect(testerLifestyleValid({ ...base, hobby: "" })).toBe(false);
    expect(testerLifestyleValid({ ...base, fitness: "" })).toBe(false);
    expect(testerLifestyleValid({ ...base, hasVehicle: "" })).toBe(false);
    expect(testerLifestyleValid({ ...base, shoppingFrequency: "" })).toBe(false);
  });

  it("accepts “no vehicle” as a real answer", () => {
    expect(testerLifestyleValid({ ...base, hasVehicle: "no" })).toBe(true);
  });

  it("rejects values that are not real options", () => {
    expect(testerLifestyleValid({ ...base, hobby: "sleeping" })).toBe(false);
    expect(testerLifestyleValid({ ...base, hasVehicle: "maybe" })).toBe(false);
    expect(testerLifestyleValid({ ...base, petsOwned: "dragon" })).toBe(false);
    expect(testerLifestyleValid({ ...base, shoppingFrequency: "constantly" })).toBe(false);
  });
});
