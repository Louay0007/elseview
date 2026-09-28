export function isValidEmail(value: string) {
  return value.length <= 254 && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());
}

export function isValidPassword(value: string) {
  return Array.from(value).length >= 12 && Array.from(value).length <= 256;
}

export type AuthMode = "login" | "signup" | "verify" | "recover" | "reset" | "invitation";
export const authWords = (en: string, fr: string) => ({ en, fr });
export type AuthField = "email" | "password" | "confirmation" | "token";
export type AuthIssue = "email" | "password" | "loginPassword" | "confirmation" | "token";

export function isValidDisplayName(value: string) {
  return Array.from(value).length <= 100;
}

export function validateAuth(mode: AuthMode, values: Partial<Record<AuthField, string>>) {
  const issues: Partial<Record<AuthField, AuthIssue>> = {};
  if (["login", "signup", "recover"].includes(mode) && !isValidEmail(values.email ?? "")) issues.email = "email";
  if (mode === "login" && (!(values.password ?? "").length || Array.from(values.password ?? "").length > 256)) issues.password = "loginPassword";
  if (["signup", "reset"].includes(mode) && !isValidPassword(values.password ?? "")) issues.password = "password";
  if (mode === "reset" && values.confirmation !== values.password) issues.confirmation = "confirmation";
  if (["verify", "reset", "invitation"].includes(mode)) {
    const length = Array.from(values.token ?? "").length;
    if (length < 20 || length > 256) issues.token = "token";
  }
  return issues;
}
