export const mockStudies = [
  { id: "study-1", title: "Coffee cups — pick your favorite", method: "preference", credits: 200, minutes: 5, languages: ["fr", "en"], tag: "New" },
  { id: "study-2", title: "Checkout page — 5 second look", method: "five_second", credits: 150, minutes: 3, languages: ["fr"], tag: "Fast" },
  { id: "study-3", title: "Bus app — short survey", method: "survey.single", credits: 300, minutes: 8, languages: ["fr", "ar"], tag: "Popular" },
  { id: "study-4", title: "Bank landing — try the prototype", method: "prototype.task", credits: 400, minutes: 12, languages: ["en"], tag: "Long" },
];
export const mockSessions = [
  { id: "b-1", study_title: "Coffee cups — pick your favorite", kind: "study", status: "booked", scheduled_at: "Tomorrow · 10:00" },
  { id: "b-2", study_title: "Bus app — short survey", kind: "study", status: "done", scheduled_at: "Sep 20 · finished" },
  { id: "b-3", study_title: "Checkout page — chat interview", kind: "interview", status: "booked", scheduled_at: "Fri · 14:30" },
];
export const mockEarnings = {
  total_millimes: 8500, pending_millimes: 4500, paid_millimes: 4000,
  items: [
    { id: "e-1", amount_millimes: 3000, state: "paid" },
    { id: "e-2", amount_millimes: 2500, state: "earned" },
    { id: "e-3", amount_millimes: 2000, state: "earned" },
    { id: "e-4", amount_millimes: 1000, state: "paid" },
  ],
};
export const mockRunnerSteps = [
  { key: "welcome", title: "Welcome.", body: "Answer honestly. There is no wrong answer." },
  { key: "q1", title: "Question 1 of 3.", body: "Which cup would you buy? Why?" },
  { key: "q2", title: "Question 2 of 3.", body: "Look at the price for 5 seconds. What do you remember?" },
  { key: "q3", title: "Question 3 of 3.", body: "Anything else to add? One sentence is enough." },
];

/**
 * Destinations a tester can cash out to. `gift_card` resolves to one retailer
 * from the grid; the other two carry a masked account label so the history can
 * show where a payout went without holding the full account number on screen.
 */
export const mockPayouts: {
  id: string;
  requested_at: string;
  amount_millimes: number;
  method: "gift_card" | "bank_transfer" | "mobile_wallet";
  destination: string;
  status: "delivered" | "paid" | "processing";
}[] = [
  { id: "p-1", requested_at: "Sep 06 · 12:20", amount_millimes: 3000, method: "gift_card", destination: "Gift card", status: "delivered" },
  { id: "p-2", requested_at: "Aug 19 · 09:05", amount_millimes: 1500, method: "bank_transfer", destination: "Bank ···· 4417", status: "paid" },
  { id: "p-3", requested_at: "Aug 02 · 17:44", amount_millimes: 2500, method: "mobile_wallet", destination: "Mobile ···· 8821", status: "processing" },
];

/**
 * Past tests behind the Test history tab. `status` covers the four states a
 * tester can end a test in: finished and paid, started then left, flagged to
 * the research team, or still open. Only a completed test earns a reward, which
 * is why the others carry zero rather than a smaller amount.
 */
export const mockTestHistory = [
  { id: "h-1", study_title: "Coffee cups — pick your favorite", method_label: "Preference test", status: "completed", finished_at: "Sep 24 · 10:04", minutes: 6, reward_millimes: 3000 },
  { id: "h-2", study_title: "Checkout page — 5 second look", method_label: "5 second test", status: "completed", finished_at: "Sep 21 · 16:38", minutes: 3, reward_millimes: 1500 },
  { id: "h-3", study_title: "Bus app — short survey", method_label: "Survey", status: "completed", finished_at: "Sep 20 · 14:12", minutes: 8, reward_millimes: 3000 },
  { id: "h-4", study_title: "Bank landing — try the prototype", method_label: "Prototype test", status: "abandoned", finished_at: "Sep 18 · 09:20", minutes: 4, reward_millimes: 0 },
  { id: "h-5", study_title: "Soda bottles — card sorting", method_label: "Card sorting", status: "completed", finished_at: "Sep 12 · 11:55", minutes: 9, reward_millimes: 4000 },
  { id: "h-6", study_title: "Help centre tree test", method_label: "Tree test", status: "reported", finished_at: "Sep 08 · 17:02", minutes: 7, reward_millimes: 0 },
  { id: "h-7", study_title: "Grocery app — first click", method_label: "First click", status: "in_progress", finished_at: null, minutes: 2, reward_millimes: 0 },
] as const;


/**
 * Tester rating starts at 100 and is reduced when responses are flagged as low
 * quality — it measures reliability, not how many studies are finished, so it
 * is not a completion ratio. No quality data exists yet, so a tester with no
 * history correctly reads 100.
 */
export const mockTesterRating = 100;

/** Identity is collected by the onboarding wizard; nothing is verified yet. */
export const mockTesterVerified = false;

