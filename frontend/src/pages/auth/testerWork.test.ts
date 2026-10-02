import { describe, expect, it } from "vitest";
import { isEmployedStatus, testerWorkValid, type TesterWorkDraft } from "./testerWork";

const employed: TesterWorkDraft = {
  employmentStatus: "employed-full-time",
  industry: "it-software",
  department: "engineering",
  careerStage: "mid",
  companySize: "51-200",
  workingEnvironment: "hybrid-remote",
};

describe("isEmployedStatus", () => {
  it("treats paid work as employed", () => {
    expect(isEmployedStatus("employed-full-time")).toBe(true);
    expect(isEmployedStatus("employed-part-time")).toBe(true);
    expect(isEmployedStatus("self-employed")).toBe(true);
    expect(isEmployedStatus("freelancer")).toBe(true);
    expect(isEmployedStatus("business-owner")).toBe(true);
  });

  it("treats study, retirement and unemployment as not employed", () => {
    expect(isEmployedStatus("student")).toBe(false);
    expect(isEmployedStatus("retired")).toBe(false);
    expect(isEmployedStatus("unemployed-looking")).toBe(false);
    expect(isEmployedStatus("homemaker")).toBe(false);
    expect(isEmployedStatus("prefer-not")).toBe(false);
    expect(isEmployedStatus("")).toBe(false);
  });
});

describe("testerWorkValid", () => {
  it("accepts a fully answered employed profile", () => {
    expect(testerWorkValid(employed)).toBe(true);
  });

  it("always requires employment status and working environment", () => {
    expect(testerWorkValid({ ...employed, employmentStatus: "" })).toBe(false);
    expect(testerWorkValid({ ...employed, workingEnvironment: "" })).toBe(false);
  });

  it("requires the four job questions when employed", () => {
    expect(testerWorkValid({ ...employed, industry: "" })).toBe(false);
    expect(testerWorkValid({ ...employed, department: "" })).toBe(false);
    expect(testerWorkValid({ ...employed, careerStage: "" })).toBe(false);
    expect(testerWorkValid({ ...employed, companySize: "" })).toBe(false);
  });

  it("rejects values that are not real options", () => {
    expect(testerWorkValid({ ...employed, industry: "space" })).toBe(false);
    expect(testerWorkValid({ ...employed, employmentStatus: "employed" })).toBe(false);
  });

  it("skips the job questions for a student", () => {
    const student: TesterWorkDraft = {
      employmentStatus: "student",
      industry: "",
      department: "",
      careerStage: "",
      companySize: "",
      workingEnvironment: "unemployed",
    };
    expect(testerWorkValid(student)).toBe(true);
  });

  it("still requires the working environment for a student", () => {
    expect(testerWorkValid({ employmentStatus: "student", industry: "", department: "", careerStage: "", companySize: "", workingEnvironment: "" })).toBe(false);
  });
});
