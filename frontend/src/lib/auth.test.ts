import { readFileSync, readdirSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { isValidDisplayName, isValidEmail, isValidPassword, validateAuth } from "./auth";
import { resolveLanguage } from "@/components/auth/AuthLocale";
import { routes } from "./routes";

const read = (path: string) => readFileSync(resolve(process.cwd(), path), "utf8");

/** Every .tsx/.ts file under a directory, so a link audit covers new files too. */
function walk(dir: string): string[] {
  return readdirSync(resolve(process.cwd(), dir), { withFileTypes: true }).flatMap((entry) => {
    const path = `${dir}/${entry.name}`;
    if (entry.isDirectory()) return walk(path);
    return /\.tsx?$/.test(entry.name) ? [path] : [];
  });
}

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
  // These read the real route table rather than scraping App.tsx source, so a
  // route may be written as `routes.x` without the test caring about how it is
  // spelled. Anything routed through <Navigate> is an alias for a canonical
  // path and is checked separately, because aliases are deliberately redundant.
  const canonical = Object.values(routes).filter((path) => path !== "/");

  it("routes every canonical path to a component", () => {
    const app = read("src/App.tsx");
    for (const path of canonical) {
      expect(app, `App.tsx must route ${path} via the routes table`).toContain(`path={routes.`);
    }
    expect(app).toMatch(/<Route path="\*" element=\{<NotFound \/>} \/>/);
  });

  it("keeps every canonical path unique", () => {
    expect(new Set(canonical).size).toBe(canonical.length);
  });

  it("keeps the tester space free of researcher workspace routes", () => {
    // A tester must never reach a workspace page that manages studies, credits,
    // reports or billing, so no tester route may alias one of them.
    const tester = Object.values(routes).filter((path) => path.startsWith("/tester"));
    expect(tester).toContain(routes.tester);
    for (const forbidden of [routes.account, routes.dashboard, routes.recruit, routes.reviews, routes.preview, routes.credits, routes.billing]) {
      expect(tester).not.toContain(forbidden);
    }
    for (const path of tester) {
      expect(path.startsWith("/tester")).toBe(true);
    }
  });

  it("redirects every legacy alias instead of leaving it unrouted", () => {
    const app = read("src/App.tsx");
    for (const legacy of ["/login", "/signup", "/mfa", "/auth/mfa", "/auth/enroll-mfa", "/studies/create", "/study-preview", "/terms", "/privacy"]) {
      expect(app).toContain(`path="${legacy}"`);
    }
  });

  it("gives every linked path a real destination", () => {
    // A footer or menu link with no matching route falls through to NotFound,
    // which is how /terms and /privacy used to 404 from both app shells.
    const known = new Set([...canonical, "*", "/"]);
    for (const alias of ["/login", "/signup", "/mfa", "/auth/mfa", "/auth/enroll-mfa", "/studies/create", "/study-preview", "/terms", "/privacy", "/reports/:reportId", "/studies/:studyId/edit"]) {
      known.add(alias);
    }
    const orphans: string[] = [];
    for (const file of walk("src")) {
      // Test sources quote paths on purpose, to assert on them, so auditing them
      // would only ever report this file.
      if (file.includes(".test.")) continue;
      const source = read(file);
      // Every position a destination can be written: JSX link props, imperative
      // navigation, and the prop-based hero link. A path literal in any of them
      // is a route that can drift away from the table without the table's tests
      // noticing, so each one has to resolve to something App.tsx actually serves.
      const pattern = /\b(?:to|href|readMoreLink|src|navigate|replace|goWithParams|go)\s*[=(]\s*(?:"(?<p>\/[^"]*)"|'(?<p2>\/[^']*)'|`(?<p3>\/[^`]*)`)/g;
      for (const match of source.matchAll(pattern)) {
        const path = match.groups?.p ?? match.groups?.p2 ?? match.groups?.p3;
        if (path.startsWith("/images/") || path.startsWith("/api/")) continue;
        // "#section" on the landing page is a scroll anchor within "/", not a route.
        if (path !== "/" && path.startsWith("/#")) continue;
        if (!known.has(path)) orphans.push(`${file} -> ${path}`);
      }
    }
    expect(orphans).toEqual([]);
  });

  it("builds every study handoff through the route table", () => {
    // The builder, recruit, publish and preview screens pass a study along as a
    // query string. studyQuery returning a pre-encoded string meant each caller
    // hand-rolled `${path}?${studyQuery(...)}` and had to guard the empty case,
    // so the params belong to withQuery instead.
    for (const file of ["Recruit", "Publish", "StudyEditor", "Dashboard"]) {
      const source = read(`src/pages/workspace/${file}.tsx`);
      expect(source, `${file}.tsx must not concatenate a path onto a query`).not.toMatch(/goWithParams\(\s*`\$\{/);
    }
    expect(read("src/components/workspace/studyNav.ts")).toMatch(/Record<string, string \| number \| undefined>/);
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
