import { describe, expect, it } from "vitest";
import { countryCallingCodes, getCountryFlag, isValidPhoneNumber, normalizePhoneNumber } from "./phoneCountries";

describe("phone country calling codes", () => {
  it("includes representative country calling codes from around the world", () => {
    expect(countryCallingCodes.length).toBeGreaterThanOrEqual(200);
    expect(countryCallingCodes.find((country) => country.iso === "TN")?.callingCode).toBe("216");
    expect(countryCallingCodes.find((country) => country.iso === "US")?.callingCode).toBe("1");
    expect(countryCallingCodes.find((country) => country.iso === "FR")?.callingCode).toBe("33");
    expect(countryCallingCodes.find((country) => country.iso === "JP")?.callingCode).toBe("81");
  });

  it("generates a flag from an ISO country code", () => {
    expect(getCountryFlag("TN")).toBe("🇹🇳");
    expect(getCountryFlag("FR")).toBe("🇫🇷");
  });

  it("normalizes local and pasted international numbers with the selected calling code", () => {
    expect(normalizePhoneNumber("20 123 456", "216", "TN")).toBe("+21620123456");
    expect(normalizePhoneNumber("06 12 34 56 78", "33", "FR")).toBe("+33612345678");
    expect(normalizePhoneNumber("+33 6 12 34 56 78", "216", "TN")).toBe("+33612345678");
    expect(normalizePhoneNumber("", "216", "TN")).toBe("");
  });

  it("validates mobile numbers against the selected country", () => {
    expect(isValidPhoneNumber("+21620123456", "216", "TN")).toBe(true);
    expect(isValidPhoneNumber("06 12 34 56 78", "33", "FR")).toBe(true);
    expect(isValidPhoneNumber("+33123456789", "33", "FR")).toBe(false);
    expect(isValidPhoneNumber("+447924123456", "44", "IM")).toBe(true);
    expect(isValidPhoneNumber("+358412345678", "358", "AX")).toBe(true);
    expect(isValidPhoneNumber("+77710009998", "7", "RU")).toBe(false);
    expect(isValidPhoneNumber("+33612345678", "216", "TN")).toBe(false);
    expect(isValidPhoneNumber("+216123", "216", "TN")).toBe(false);
  });
});
