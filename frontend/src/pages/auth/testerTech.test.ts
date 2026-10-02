import { describe, expect, it } from "vitest";
import { testerTechValid, type TesterTechDraft } from "./testerTech";

const base: TesterTechDraft = {
  screenTime: "6-8",
  mostUsedDevice: "smartphone",
  dailyApps: ["social", "messaging"],
  mobileUserType: "heavy",
  desktopUserType: "light",
  ownedDevices: ["android", "laptop"],
};

describe("testerTechValid", () => {
  it("accepts a fully answered profile", () => {
    expect(testerTechValid(base)).toBe(true);
  });

  it("requires each of the four dropdowns", () => {
    expect(testerTechValid({ ...base, screenTime: "" })).toBe(false);
    expect(testerTechValid({ ...base, mostUsedDevice: "" })).toBe(false);
    expect(testerTechValid({ ...base, mobileUserType: "" })).toBe(false);
    expect(testerTechValid({ ...base, desktopUserType: "" })).toBe(false);
  });

  it("requires at least one daily app", () => {
    expect(testerTechValid({ ...base, dailyApps: [] })).toBe(false);
    expect(testerTechValid({ ...base, dailyApps: ["myspace"] })).toBe(false);
  });

  it("requires at least one owned device", () => {
    expect(testerTechValid({ ...base, ownedDevices: [] })).toBe(false);
    expect(testerTechValid({ ...base, ownedDevices: ["toaster"] })).toBe(false);
  });

  it("rejects dropdown values that are not real options", () => {
    expect(testerTechValid({ ...base, screenTime: "all-day" })).toBe(false);
    expect(testerTechValid({ ...base, mostUsedDevice: "fridge" })).toBe(false);
  });

  it("allows “I don’t use” answers without inventing other detail", () => {
    expect(testerTechValid({ ...base, mobileUserType: "none", desktopUserType: "none" })).toBe(true);
  });
});
