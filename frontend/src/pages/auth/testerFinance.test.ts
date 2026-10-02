import { describe, expect, it } from "vitest";
import { testerFinanceValid, type TesterFinanceDraft } from "./testerFinance";

const base: TesterFinanceDraft = {
  noBankAccount: false,
  bank: "national",
  paymentMethods: ["cash", "debit"],
};

describe("testerFinanceValid", () => {
  it("accepts a fully answered profile", () => {
    expect(testerFinanceValid(base)).toBe(true);
  });

  it("requires the bank only when the tester has an account", () => {
    expect(testerFinanceValid({ ...base, noBankAccount: true, bank: "" })).toBe(true);
    expect(testerFinanceValid({ ...base, noBankAccount: false, bank: "" })).toBe(false);
  });

  it("still requires payment methods without a bank account", () => {
    expect(testerFinanceValid({ noBankAccount: true, bank: "", paymentMethods: ["cash"] })).toBe(true);
    expect(testerFinanceValid({ noBankAccount: true, bank: "", paymentMethods: [] })).toBe(false);
  });

  it("requires at least one payment method", () => {
    expect(testerFinanceValid({ ...base, paymentMethods: [] })).toBe(false);
    expect(testerFinanceValid({ ...base, paymentMethods: ["barter"] })).toBe(false);
  });

  it("rejects bank values that are not real options", () => {
    expect(testerFinanceValid({ ...base, bank: "paypal" })).toBe(false);
  });
});
