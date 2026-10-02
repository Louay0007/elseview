import { authWords as words } from "@/lib/auth";

/**
 * The onboarding wizard writes a draft to localStorage when the tester finishes
 * step 8. The profile page edits that same draft, so both surfaces stay in sync
 * and the tester never re-types what they already told us.
 */
export const TESTER_PROFILE_KEY = "elseview.tester.profile";

export type SavedTesterProfile = {
  firstName: string;
  lastName: string;
  gender: string;
  dob: string;
  nationality: string;
  residence: string;
  email?: string;
  phone?: string;
  callingCode?: string;
  countryIso?: string;
  whatsappPhone?: string;
  whatsapp?: boolean;
  about?: Record<string, unknown>;
  household?: Record<string, unknown>;
  work?: Record<string, unknown>;
  tech?: Record<string, unknown>;
  lifestyle?: Record<string, unknown>;
  finance?: Record<string, unknown>;
};

const empty = {
  firstName: "",
  lastName: "",
  gender: "",
  dob: "",
  nationality: "",
  residence: "",
  email: "",
  phone: "",
  whatsapp: false,
  about: {} as Record<string, unknown>,
  household: {} as Record<string, unknown>,
  work: {} as Record<string, unknown>,
  tech: {} as Record<string, unknown>,
  lifestyle: {} as Record<string, unknown>,
  finance: {} as Record<string, unknown>,
};

export function readTesterProfile(): SavedTesterProfile {
  if (typeof window === "undefined") return { ...empty };
  try {
    const raw = window.localStorage.getItem(TESTER_PROFILE_KEY);
    if (!raw) return { ...empty };
    const parsed = JSON.parse(raw) as Partial<SavedTesterProfile>;
    return {
      ...empty,
      ...parsed,
      firstName: typeof parsed.firstName === "string" ? parsed.firstName : "",
      lastName: typeof parsed.lastName === "string" ? parsed.lastName : "",
      gender: typeof parsed.gender === "string" ? parsed.gender : "",
      dob: typeof parsed.dob === "string" ? parsed.dob : "",
      nationality: typeof parsed.nationality === "string" ? parsed.nationality : "",
      residence: typeof parsed.residence === "string" ? parsed.residence : "",
      email: typeof parsed.email === "string" ? parsed.email : "",
      phone: typeof parsed.phone === "string" ? parsed.phone : "",
    };
  } catch {
    // Corrupt or unavailable storage must not break the page.
    return { ...empty };
  }
}

export function writeTesterProfile(profile: SavedTesterProfile): boolean {
  try {
    window.localStorage.setItem(TESTER_PROFILE_KEY, JSON.stringify(profile));
    return true;
  } catch {
    /* private mode: the form still works, it just will not persist */
    return false;
  }
}

export function clearTesterProfile() {
  try {
    window.localStorage.removeItem(TESTER_PROFILE_KEY);
  } catch {
    /* ignore */
  }
}
