import { isValidPhoneNumber, normalizePhoneNumber } from "@/lib/phoneCountries";

export function ageOn(dateString: string, now = new Date()): number | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(dateString);
  if (!match) return null;
  const year = Number(match[1]);
  const month = Number(match[2]) - 1;
  const day = Number(match[3]);
  const date = new Date(year, month, day);
  if (date.getFullYear() !== year || date.getMonth() !== month || date.getDate() !== day) return null;
  let age = now.getFullYear() - year;
  if (now.getMonth() < month || (now.getMonth() === month && now.getDate() < day)) age -= 1;
  return age;
}

export type TesterProfileDraft = {
  firstName: string;
  lastName: string;
  gender: string;
  dob: string;
  nationality: string;
  residence: string;
};

export function testerProfileValid(profile: TesterProfileDraft, now = new Date()): boolean {
  const age = ageOn(profile.dob, now);
  return (
    profile.firstName.trim().length > 0 &&
    profile.lastName.trim().length > 0 &&
    (profile.gender === "male" || profile.gender === "female") &&
    age !== null &&
    age >= 18 &&
    age <= 120 &&
    profile.nationality.length > 0 &&
    profile.residence.length > 0
  );
}

/**
 * Step 2 of the tester onboarding. `callingCode` must be the calling code of
 * `countryIso`, so the two stay in sync when the country picker changes.
 */
export function testerContactValid(phone: string, callingCode: string, countryIso: string): boolean {
  if (!phone.trim()) return false;
  return isValidPhoneNumber(normalizePhoneNumber(phone, callingCode, countryIso), callingCode, countryIso);
}
