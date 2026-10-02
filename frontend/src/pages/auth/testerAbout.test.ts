import { describe, expect, it } from "vitest";
import { testerAboutValid, type TesterAboutDraft } from "./testerAbout";

const base: TesterAboutDraft = {
  relationship: "married",
  religion: "islam",
  education: "bachelor",
  children: "2",
  languages: ["ar", "en"],
  otherLanguage: "",
  noDrivingLicense: true,
  drivingLicense: "",
  noDisability: true,
  disability: "",
};

describe("testerAboutValid", () => {
  it("accepts a fully answered profile", () => {
    expect(testerAboutValid(base)).toBe(true);
  });

  it("requires each of the four dropdowns", () => {
    expect(testerAboutValid({ ...base, relationship: "" })).toBe(false);
    expect(testerAboutValid({ ...base, religion: "" })).toBe(false);
    expect(testerAboutValid({ ...base, education: "" })).toBe(false);
    expect(testerAboutValid({ ...base, children: "" })).toBe(false);
  });

  it("rejects values that are not real options", () => {
    expect(testerAboutValid({ ...base, relationship: "invented" })).toBe(false);
    expect(testerAboutValid({ ...base, education: "phd-ish" })).toBe(false);
  });

  it("requires at least one spoken language", () => {
    expect(testerAboutValid({ ...base, languages: [] })).toBe(false);
    expect(testerAboutValid({ ...base, languages: ["klingon"] })).toBe(false);
  });

  it("accepts the other-languages dropdown on its own", () => {
    expect(testerAboutValid({ ...base, languages: [], otherLanguage: "swahili" })).toBe(true);
  });

  it("only requires the driving licence when the tester has one", () => {
    expect(testerAboutValid({ ...base, noDrivingLicense: true, drivingLicense: "" })).toBe(true);
    expect(testerAboutValid({ ...base, noDrivingLicense: false, drivingLicense: "" })).toBe(false);
    expect(testerAboutValid({ ...base, noDrivingLicense: false, drivingLicense: "manual" })).toBe(true);
  });

  it("only requires the disability select when the tester has one", () => {
    expect(testerAboutValid({ ...base, noDisability: true, disability: "" })).toBe(true);
    expect(testerAboutValid({ ...base, noDisability: false, disability: "" })).toBe(false);
    expect(testerAboutValid({ ...base, noDisability: false, disability: "visual" })).toBe(true);
  });
});
