export const studies = [
  { title: "Checkout problems — prototype + survey", status: "live", label: "Live", version: "Version 4", method: "Prototype + Survey", replies: 128, goal: 200, progress: 64, reviews: "42 ok · 6 flagged" },
  { title: "Price choice — survey", status: "review", label: "Needs check", version: "Version 2", method: "Survey", replies: 86, goal: 120, progress: 72, reviews: "2 need a final choice" },
  { title: "First week diary", status: "draft", label: "Draft", version: "Version 1", method: "Diary + Chat", replies: 0, goal: 60, progress: 8, reviews: "People only, no AI" },
  { title: "Arabic page — 5 seconds + memory", status: "paused", label: "Paused", version: "Version 6", method: "5 second test", replies: 210, goal: 210, progress: 100, reviews: "Report approved" },
] as const;

export const launches = [
  { name: "Open group — Tunisia, French", quota: "64 of 100 people", pct: 64, label: "Finding people", screener: "3 short questions · unpaid", delivery: "By hand + email" },
  { name: "Private group — experts", quota: "18 of 40 people", pct: 45, label: "Checking people", screener: "Tunisian Arabic speakers", delivery: "By hand only" },
] as const;

export const reviewQueue = [
  { session: "Reply 8F42", flags: "Finished too fast", votes: "1 yes · 1 no", next: "Needs final choice" },
  { session: "Reply 91BD", flags: "Missed check question", votes: "Waiting for 2 checks", next: "Pick people to check" },
  { session: "Reply A017", flags: "No problem", votes: "Person asked again", next: "Check the appeal" },
] as const;

export const reports = [
  { name: "Checkout results 41", state: "Approved", detail: "128 replies · ties kept · small groups hidden" },
  { name: "Price results 18", state: "Draft", detail: "86 replies · totals shown" },
] as const;

export const aiOps = [
  { title: "Themes", desc: "Group written answers into themes with real quotes." },
  { title: "Mood hints", desc: "Simple mood ideas. You decide what they mean." },
  { title: "Report draft", desc: "Make a first draft from finished results only." },
  { title: "Translation", desc: "Translate answers. The first text always stays." },
] as const;

export const replyTrend = [
  { week: "Week 1", replies: 28 },
  { week: "Week 2", replies: 41 },
  { week: "Week 3", replies: 52 },
  { week: "Week 4", replies: 48 },
  { week: "Week 5", replies: 63 },
  { week: "Week 6", replies: 71 },
  { week: "Week 7", replies: 66 },
  { week: "Week 8", replies: 55 },
];

export const methodShare = [
  { method: "Survey", replies: 180 },
  { method: "Prototype", replies: 96 },
  { method: "5 seconds", replies: 84 },
  { method: "Diary", replies: 41 },
  { method: "Menu", replies: 23 },
];

export const checkSplit = [
  { name: "Accepted", value: 379 },
  { name: "Flagged", value: 22 },
  { name: "To check", value: 23 },
];

export const studyLifecycle = [
  { title: "Checkout problems — prototype.task + survey.single", version: "Revision 4 · published", last: "Report approved · Sep 26", status: "live", label: "Live — collecting replies" },
  { title: "Price choice — survey.single", version: "Revision 2 · published", last: "Published · Sep 24", status: "review", label: "Live — in review" },
  { title: "First week diary", version: "Revision 1 · draft", last: "Draft opened · Sep 18", status: "draft", label: "Draft — not shared" },
  { title: "Arabic page — five_second", version: "Revision 6 · paused", last: "Paused · Sep 22 — replies kept", status: "paused", label: "Paused — replies kept" },
] as const;

export const historyEvents = [
  { date: "Sep 26", type: "Report", title: "Checkout results 41 approved", detail: "Report v2 approved by 2 people." },
  { date: "Sep 25", type: "Reply", title: "Arabic page full — 210 of 210 replies", detail: "Last reply came in at night." },
  { date: "Sep 25", type: "Check", title: "Final choice made on Reply 8F42", detail: "1 yes and 1 no became Accepted." },
  { date: "Sep 24", type: "Study", title: "Price choice shared — Version 2", detail: "Shared after consent and pictures were checked." },
  { date: "Sep 24", type: "People", title: "18 of 40 experts checked in", detail: "Private group keeps growing." },
  { date: "Sep 23", type: "AI", title: "Themes draft made for Checkout", detail: "First draft from finished results only." },
  { date: "Sep 23", type: "Check", title: "Appeal filed on Reply A017", detail: "Person asked for a second look." },
  { date: "Sep 22", type: "Study", title: "Arabic page paused — Version 6", detail: "Paused with all 210 replies kept." },
  { date: "Sep 22", type: "Money", title: "42 rewards paid by hand", detail: "Checkout replies paid, no app money moved." },
  { date: "Sep 21", type: "Report", title: "Price results 18 draft made", detail: "86 replies with totals shown." },
  { date: "Sep 21", type: "Reply", title: "86 of 120 replies on Price choice", detail: "Diary still at 0 of 60." },
  { date: "Sep 20", type: "Study", title: "Checkout problems shared — Version 4", detail: "Prototype + Survey went live." },
  { date: "Sep 20", type: "People", title: "Open group reached 64 of 100 people", detail: "Tunisia, French group." },
  { date: "Sep 19", type: "AI", title: "30 answers translated", detail: "First text always kept." },
] as const;

export const eventsTrend = [
  { week: "Week 1", events: 6 },
  { week: "Week 2", events: 9 },
  { week: "Week 3", events: 12 },
  { week: "Week 4", events: 10 },
  { week: "Week 5", events: 15 },
  { week: "Week 6", events: 18 },
  { week: "Week 7", events: 14 },
  { week: "Week 8", events: 11 },
];

export const eventsByType = [
  { type: "Study", events: 18 },
  { type: "Reply", events: 31 },
  { type: "Check", events: 22 },
  { type: "Report", events: 9 },
  { type: "AI", events: 8 },
  { type: "People", events: 5 },
  { type: "Money", events: 2 },
];
