import { describe, expect, it } from "vitest";
import { ageOn, testerContactValid, testerProfileValid } from "./testerProfile";

const NOW = new Date(2026, 8, 29); // Sep 29, 2026
const base = {
  firstName: "Louay",
  lastName: "Rjili",
  gender: "male",
  dob: "2000-01-15",
  nationality: "TN",
  residence: "FR",
};

describe("ageOn", () => {
  it("computes age around birthdays", () => {
    expect(ageOn("2008-09-29", NOW)).toBe(18);
    expect(ageOn("2008-09-30", NOW)).toBe(17);
    expect(ageOn("2008-09-28", NOW)).toBe(18);
  });
  it("rejects malformed or impossible dates", () => {
    expect(ageOn("", NOW)).toBeNull();
    expect(ageOn("15/01/2000", NOW)).toBeNull();
    expect(ageOn("2000-02-30", NOW)).toBeNull();
  });
});

describe("testerProfileValid", () => {
  it("accepts a complete adult profile", () => {
    expect(testerProfileValid(base, NOW)).toBe(true);
  });
  it("rejects minors, blanks, and missing selections", () => {
    expect(testerProfileValid({ ...base, dob: "2010-05-01" }, NOW)).toBe(false);
    expect(testerProfileValid({ ...base, firstName: "  " }, NOW)).toBe(false);
    expect(testerProfileValid({ ...base, gender: "" }, NOW)).toBe(false);
    expect(testerProfileValid({ ...base, gender: "other" }, NOW)).toBe(false);
    expect(testerProfileValid({ ...base, nationality: "" }, NOW)).toBe(false);
    expect(testerProfileValid({ ...base, residence: "" }, NOW)).toBe(false);
  });
});

describe("testerContactValid", () => {
  // TN = Tunisia, calling code 216.
  it("accepts a valid Tunisian mobile number", () => {
    expect(testerContactValid("20123456", "216", "TN")).toBe(true);
    expect(testerContactValid("+216 20 123 456", "216", "TN")).toBe(true);
    expect(testerContactValid("20.123.456", "216", "TN")).toBe(true);
  });
  it("rejects empty input", () => {
    expect(testerContactValid("", "216", "TN")).toBe(false);
    expect(testerContactValid("   ", "216", "TN")).toBe(false);
  });
  it("rejects numbers too short to be valid", () => {
    expect(testerContactValid("1234", "216", "TN")).toBe(false);
  });
  it("rejects a number that does not belong to the selected country", () => {
    // French mobile entered while Tunisia is selected.
    expect(testerContactValid("612345678", "216", "TN")).toBe(false);
  });
  it("accepts a valid French number when France is selected", () => {
    expect(testerContactValid("612345678", "33", "FR")).toBe(true);
  });
});
