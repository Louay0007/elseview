import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { isValidDisplayName, isValidEmail, isValidPassword, validateAuth } from "./auth";
import { resolveLanguage } from "@/components/auth/AuthLocale";

const read = (path: string) => readFileSync(resolve(process.cwd(), path), "utf8");

describe("authentication validation", () => {
  it("supports only English and French and migrates the old Arabic preference", () => {
    expect(resolveLanguage("ar", "fr-TN")).toBe("en");
    expect(resolveLanguage(null, "fr-FR")).toBe("fr");
    expect(resolveLanguage("en", "fr-FR")).toBe("en");
    expect(resolveLanguage(null, "ar-TN")).toBe("en");
    expect(resolveLanguage("invalid", "de-DE")).toBe("en");
  });
  it("accepts normal email addresses and rejects incomplete ones", () => {
    expect(isValidEmail("patient@example.com")).toBe(true);
    expect(isValidEmail("patient@invalid")).toBe(false);
  });

  it("requires passwords of at least 12 characters", () => {
    expect(isValidPassword("12345678901")).toBe(false);
    expect(isValidPassword("123456789012")).toBe(true);
    expect(isValidPassword("a".repeat(257))).toBe(false);
    expect(isValidPassword("😀".repeat(12))).toBe(true);
  });
  it("matches login, signup, code and confirmation contracts", () => {
    expect(validateAuth("login", { email: "demo@example.test", password: "x" })).toEqual({});
    expect(validateAuth("signup", { email: "demo@example.test", password: "123456789012" })).toEqual({});
    expect(isValidDisplayName("x".repeat(100))).toBe(true);
    expect(isValidDisplayName("x".repeat(101))).toBe(false);
    expect(validateAuth("verify", { token: "123456" })).toHaveProperty("token");
    expect(validateAuth("verify", { token: "x".repeat(20) })).toEqual({});
    expect(validateAuth("invitation", { token: "x".repeat(257) })).toHaveProperty("token");
    expect(validateAuth("reset", { token: "x".repeat(20), password: "123456789012", confirmation: "different" })).toEqual({ confirmation: "confirmation" });
    expect(validateAuth("recover", { email: "invalid" })).toHaveProperty("email");
  });
});

describe("frontend route boundaries", () => {
  it("keeps only landing, authentication, workspace, and not-found routes", () => {
    const routes = [...read("src/App.tsx").matchAll(/<Route path="([^"]+)"/g)].map((match) => match[1]);
    expect(routes).toEqual([
      "/", "/login", "/signup", "/mfa", "/auth/login", "/auth/signup",
      "/auth/verify-email", "/auth/complete-profile", "/account", "/account/notifications", "/account/refer", "/dashboard", "/studies/new", "/analytics", "/history", "/workspace/billing", "/workspace/credits", "/workspace/credits/buy", "/settings", "/auth/recover", "/auth/reset-password", "/auth/invitation",
      "/auth/mfa", "/auth/enroll-mfa", "*",
    ]);
  });

  it("keeps auth previews offline and retires simulated authentication", () => {
    for (const page of ["AuthFlow", "CompleteProfile"]) {
      const source = read(`src/pages/auth/${page}.tsx`);
      expect(source).not.toMatch(/fetch\(|axios|sessionStorage|localStorage|completeSession|useAuthSession/);
    }
    expect(read("src/App.tsx")).not.toContain("AuthSessionProvider");
    expect(read("src/App.tsx")).not.toContain("MfaPage");
  });
});
