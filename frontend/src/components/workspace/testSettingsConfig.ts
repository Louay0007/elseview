export type CustomField =
  | { key: string; label: { en: string; fr: string }; hint?: { en: string; fr: string }; type: "text"; placeholder?: { en: string; fr: string } }
  | { key: string; label: { en: string; fr: string }; hint?: { en: string; fr: string }; type: "textarea"; placeholder?: { en: string; fr: string } }
  | { key: string; label: { en: string; fr: string }; hint?: { en: string; fr: string }; type: "number"; min?: number; max?: number; defaultValue?: number }
  | { key: string; label: { en: string; fr: string }; hint?: { en: string; fr: string }; type: "select"; options: { value: string; label: { en: string; fr: string } }[]; defaultValue?: string }
  | { key: string; label: { en: string; fr: string }; hint?: { en: string; fr: string }; type: "switch"; defaultValue?: boolean };

export const TEST_CUSTOM_FIELDS: Record<string, { title: { en: string; fr: string }; fields: CustomField[] }> = {};

export function customFieldsFor(method: string) {
  return TEST_CUSTOM_FIELDS[method] ?? null;
}
