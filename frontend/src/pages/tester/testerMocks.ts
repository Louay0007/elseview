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
