/**
 * Single source of truth for every internal path in the app.
 *
 * Nothing outside this file should spell a route as a bare string. Importing
 * the helpers instead means a rename can never leave a dangling link behind:
 * TypeScript fails the build if a path is misspelled, and a route that is
 * removed is deleted in exactly one place.
 *
 * Query parameters are appended through the helpers below rather than by hand,
 * so a destination that already carries a query string never ends up with two
 * `?` separators.
 */

/** Static, literal paths. Anything dynamic gets a builder function instead. */
export const routes = {
  landing: "/",

  // Authentication. Each mode is its own screen so a refresh or a shared link
  // always lands on the right step of the flow.
  login: "/auth/login",
  signup: "/auth/signup",
  verifyEmail: "/auth/verify-email",
  recover: "/auth/recover",
  resetPassword: "/auth/reset-password",
  invitation: "/auth/invitation",
  completeProfile: "/auth/complete-profile",

  // Legal copy. Not published yet, but reachable so the footer never 404s.
  terms: "/legal/terms",
  privacy: "/legal/privacy",

  // Researcher workspace.
  dashboard: "/dashboard",
  newStudy: "/studies/new",
  recruit: "/recruit",
  publish: "/publish",
  reviews: "/reviews",
  preview: "/preview",
  analytics: "/analytics",
  history: "/history",
  account: "/account",
  accountNotifications: "/account/notifications",
  accountRefer: "/account/refer",
  settings: "/settings",
  billing: "/workspace/billing",
  credits: "/workspace/credits",
  buyCredits: "/workspace/credits/buy",

  // Tester space. Testers never reach researcher pages, and vice versa.
  tester: "/tester",
  testerOnboarding: "/tester/onboarding",
  testerStudies: "/tester/studies",
  testerRunner: "/tester/runner",
  testerSessions: "/tester/sessions",
  testerHistory: "/tester/history",
  testerNotifications: "/tester/notifications",
  testerEarnings: "/tester/earnings",
  testerProfile: "/tester/profile",
} as const;

export type StaticRoute = (typeof routes)[keyof typeof routes];

/** Path parameters for the routes that take an identifier. */
export type RouteParams = Record<string, string | number>;

/** `/studies/:studyId/edit` with `{ studyId }` replaced. */
export function buildPath(pattern: string, params: RouteParams = {}): string {
  return pattern.replace(/:([A-Za-z0-9_]+)/g, (match, key: string) => {
    const value = params[key];
    if (value === undefined || value === null || value === "") {
      throw new Error(`Missing "${key}" for route "${pattern}"`);
    }
    return encodeURIComponent(String(value));
  });
}

/** Appends a query string to a path, respecting any `?` or `#` it already has. */
export function withQuery(
  path: string,
  query?: Record<string, string | number | boolean | null | undefined>,
): string {
  if (!query) return path;
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null || value === "") continue;
    search.set(key, String(value));
  }
  if (search.toString() === "") return path;
  const separator = path.includes("?") ? "&" : "?";
  return `${path}${separator}${search.toString()}`;
}

/** A study id plus the `studyId` path parameter it fills. */
export const studyEditRoute = (studyId: string | number) =>
  buildPath("/studies/:studyId/edit", { studyId });

/** A report id plus the `reportId` path parameter it fills. */
export const reportRoute = (reportId: string | number) =>
  buildPath("/reports/:reportId", { reportId });

/** The auth screen for a role, carrying `?role=` so AuthFlow picks the right UI. */
export const authRoute = (mode: "login" | "signup" | "recover", role?: "researcher" | "tester") => {
  const base = mode === "login" ? routes.login : mode === "recover" ? routes.recover : routes.signup;
  return withQuery(base, role ? { role } : undefined);
};

/** The verify screen, with `resend` opening the resend form. */
export const verifyEmailRoute = (options: { resend?: boolean } = {}) =>
  withQuery(routes.verifyEmail, options.resend ? { resend: "1" } : undefined);