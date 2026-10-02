import { describe, expect, it } from "vitest";
import { authRoute, buildPath, reportRoute, routes, studyEditRoute, verifyEmailRoute, withQuery } from "./routes";

describe("route table", () => {
  it("declares each canonical path exactly once", () => {
    const paths = Object.values(routes);
    expect(new Set(paths).size).toBe(paths.length);
  });

  it("spaces every screen under a named section", () => {
    // A bare top-level name like "/terms" or "/preview" is ambiguous once the
    // app has both a researcher and a tester space, so legal and preview paths
    // are namespaced. The remaining flat routes are the documented exception.
    expect(routes.terms).toBe("/legal/terms");
    expect(routes.privacy).toBe("/legal/privacy");
    expect(routes.preview).toBe("/preview");
    for (const path of Object.values(routes)) {
      expect(path.startsWith("/")).toBe(true);
      expect(path).not.toContain("//");
      expect(path).not.toMatch(/\s/);
    }
  });

  it("keeps tester paths inside the tester space", () => {
    const tester = Object.entries(routes).filter(([, path]) => path.startsWith("/tester"));
    expect(tester.length).toBeGreaterThan(0);
    for (const [, path] of tester) expect(path).toMatch(/^\/tester(\/|$)/);
  });
});

describe("buildPath", () => {
  it("substitutes a named parameter", () => {
    expect(buildPath("/studies/:studyId/edit", { studyId: "abc" })).toBe("/studies/abc/edit");
  });

  it("encodes a parameter so a path cannot be escaped", () => {
    expect(buildPath("/reports/:reportId", { reportId: "a/b?c#d" })).toBe("/reports/a%2Fb%3Fc%23d");
  });

  it("refuses to build a path with a missing parameter", () => {
    expect(() => buildPath("/reports/:reportId", {})).toThrow(/reportId/);
    expect(() => buildPath("/reports/:reportId", { reportId: "" })).toThrow(/reportId/);
  });

  it("leaves a pattern with no parameters untouched", () => {
    expect(buildPath(routes.dashboard)).toBe("/dashboard");
  });
});

describe("withQuery", () => {
  it("starts a query string when the path has none", () => {
    expect(withQuery("/dashboard", { role: "researcher" })).toBe("/dashboard?role=researcher");
  });

  it("appends with an ampersand when the path already has one", () => {
    expect(withQuery("/studies/new?method=survey", { role: "tester" })).toBe("/studies/new?method=survey&role=tester");
  });

  it("drops empty values rather than sending role=&", () => {
    expect(withQuery("/dashboard", { role: "researcher", firstName: "" })).toBe("/dashboard?role=researcher");
    expect(withQuery("/dashboard", { role: undefined, firstName: null })).toBe("/dashboard");
  });

  it("returns the path untouched when there is nothing to add", () => {
    expect(withQuery("/dashboard")).toBe("/dashboard");
    expect(withQuery("/dashboard", {})).toBe("/dashboard");
  });
});

describe("auth helpers", () => {
  it("carries the role so AuthFlow renders the right screen", () => {
    expect(authRoute("login", "tester")).toBe("/auth/login?role=tester");
    expect(authRoute("signup", "researcher")).toBe("/auth/signup?role=researcher");
    expect(authRoute("recover", "tester")).toBe("/auth/recover?role=tester");
    expect(authRoute("login")).toBe("/auth/login");
  });

  it("opens the resend form only when asked", () => {
    expect(verifyEmailRoute()).toBe("/auth/verify-email");
    expect(verifyEmailRoute({ resend: true })).toBe("/auth/verify-email?resend=1");
  });
});

describe("parameterised routes", () => {
  it("builds a study edit path from its id", () => {
    expect(studyEditRoute("s1")).toBe("/studies/s1/edit");
  });

  it("builds a report path from its id", () => {
    expect(reportRoute("r1")).toBe("/reports/r1");
  });
});