# Elseview — Tunisian user-research and AI-testing platform

**Brand:** Elseview — See what you’re missing.

A Tunisian company where teams order product tests, recruit real local users, and receive checked results with clear reports. AI assistance uses a configurable OpenAI-compatible cloud LLM through the backend. The application uses four containers: frontend, Python backend, PostgreSQL database and cache; no local model or dedicated worker service.

## The idea

Many companies launch websites, apps, campaigns or chatbots without knowing whether real users understand them. Fixing mistakes after launch costs more than testing before launch.

This platform connects:

- **Buyers:** UX designers, researchers, product teams, marketers, AI teams and business teams.
- **Providers:** local testers and interview participants, including specialists such as developers, healthcare workers or native Arabic speakers.
- **The platform:** test tools, participant recruitment, quality checks and reports.

The strongest part is a Tunisian-built panel of difficult-to-reach local and Arabic-speaking users.

## Use cases and examples

### For UX researchers and UX/UI designers

- **Prototype test:** a bank checks whether customers can open an account in a new app design before developers build it.
- **Five-second test:** an online shop checks what visitors understand from a new homepage in five seconds.
- **Preference test:** a startup compares two checkout pages and learns why users choose one.
- **First-click test:** a government website checks where citizens click first to find a document.
- **Survey:** a telecom company asks 500 users which payment method they prefer.
- **Card sorting:** a supermarket app lets users group products so menus match how people think.
- **Tree test:** a university checks whether students can find exam results using only the menu structure.
- **Usability task test:** a delivery app measures how long an order takes and where users give up.
- **Interview:** a bank talks to customers on video calls about why they stopped using a savings feature.

### For AI and LLM teams

A strong LLM layer turns raw answers into decisions faster. These use cases show where the model helps and where a human must stay in charge.

- **Answer summariser:** an LLM groups 500 open answers into themes, and the dashboard always links each theme back to the original quotes.
- **Failure clustering:** the model groups chatbot mistakes into categories such as wrong address, wrong refund rule or invented policy. Example: a telecom team learns that 40% of failures come from one misunderstood refund sentence.
- **Sentiment and emotion scan:** the model scores answers as happy, neutral or frustrated and flags the most emotional cases for human review. Example: a food brand finds the delivery packaging comments are the angriest ones.
- **Comparison writer:** after an A/B test of two designs, the LLM writes a short comparison with numbers and quotes. Example: a startup reads one page instead of 200 answers.
- **Survey insight finder:** the model finds links such as "users under 25 prefer cash on delivery" and shows the numbers behind each claim.
- **Duplicate and low-quality flagger:** the model flags copy-paste, nonsense or off-topic answers so reviewers check them. Example: ten identical answers from different accounts are flagged before they pollute the report.
- **Interview transcription and highlights:** the model turns a 30-minute interview recording into text, key moments and follow-up questions. Example: a hospital researcher jumps straight to the three minutes where booking failed.
- **Ad and message scorer:** the LLM pre-scores 20 ad captions for clarity and tone, then real users validate the top five. The model narrows the list; humans decide.
- **Multilingual helper:** the model translates Tunisian Arabic and French answers into one working language while keeping the original text visible for verification.
- **Report writer:** the model drafts the final client report from approved charts and verified quotes. A human signs off before delivery.

**Rules for the AI layer:** humans approve safety, medical, legal and financial conclusions; all AI-written text is labelled as AI-assisted; clients can ask the model to show its sources.

### For product teams

- **Concept test:** a startup shows a new subscription idea and learns whether people would pay before building it.
- **Pricing test:** a SaaS company compares monthly versus yearly plans and sees which one users choose.
- **Onboarding test:** a fintech app finds the exact signup step where most users stop.
- **Competitor comparison:** a travel site learns whether users find its booking page clearer than a rival's.
- **Customer-journey test:** an e-commerce store follows a full order from search to delivery and finds every weak point.
- **Feature prioritisation:** a software team lets customers rank ten features and builds the top three first.

### For marketers

- **Ad-message test:** a clothing brand compares three Instagram captions and sees which one people remember.
- **Brand survey:** a food company measures trust and quality perception every three months.
- **Landing-page test:** an agency learns why a campaign page gets clicks but no sales.
- **Video-ad review:** a cosmetics brand checks whether viewers understand and trust a new video ad.
- **Audience test:** a bank discovers students love a campaign that parents find confusing.
- **Pre-launch check:** a retailer tests offer rules and images before spending money on ads.

### For AI and data teams

- **Chatbot test:** an online shop checks whether its chatbot handles Tunisian Arabic refund requests correctly.
- **Safety check:** a health app checks whether its AI refuses dangerous requests while still answering normal questions.
- **Response review:** a company scores two chatbot versions on helpfulness and politeness.
- **Preference comparison:** users choose the better of two AI answers and explain why.
- **Dialect check:** native speakers mark unnatural words in a voice assistant's Tunisian responses.
- **Voice test:** a call centre checks whether its voice system understands accents and background noise.
- **Dataset labelling:** trained participants label product images so a company can train its own model.

### For business teams

- **Offer test:** an internet provider compares two new packages and sees which one customers choose.
- **Instruction test:** a delivery company rewrites its return rules after users misunderstand them.
- **Form test:** an insurer finds which form field makes most applicants quit.
- **Support check:** a store tests whether its help articles answer the ten most common questions.
- **Market-entry test:** a Tunis brand checks price expectations and payment habits before expanding to another city.

## Features

### Test creation

- Ready-made templates for every test type above.
- Prototype links and mobile screen uploads.
- Survey builder with logic and validation.
- Questions in Arabic, French or both, with right-to-left Arabic layout.
- Preview before launch and version history for repeated tests.

### Participant panel and recruitment

- Target participants by age, city, language, device and experience.
- Screen participants with custom questions.
- Scheduling, reminders and attendance tracking for interviews.
- Quality scores, response history and no-show records.
- Participant payments recorded in the system.
- A customer-owned private panel option alongside the platform's Tunisian and MENA panel.

### Quality checks

- Language qualification tests for testers.
- Attention checks inside studies.
- Duplicate-response detection.
- Reviewer agreement checks on important answers.
- Flags for unusually fast or copied answers.
- Manual review of uncertain submissions.

### Analysis and reports

- Automatic charts, success rates and completion times.
- LLM summaries of themes, linked to original quotes.
- Failure summaries with representative user answers.
- Side-by-side comparison of two tests or two audience groups.
- Spreadsheet and PDF export plus a shareable online summary.
- Raw data access for researchers who want deeper analysis.

### AI and LLM features

- Text is analysed in batches, only after collection, so API costs stay predictable.
- Results are cached per study, so re-opening an unchanged report requires no new model call.
- Customers choose the analysis depth: quick scan, standard themes or deep dive.
- AI output is billed per study or per thousand responses, with a visible usage meter.
- Sensitive studies can run without AI analysis, with humans only.
- Every AI result links to the source answers it came from.

### AI cost control

Keep the model cheap with these rules:

- Group bounded sets of answers for analysis when useful; do not assume the provider offers a discounted batch API.
- Start with one configured cloud model; add a different model only when measured quality or cost justifies it.
- Reuse cached results only when source data, consent, prompt and provider/model configuration remain unchanged.
- Set a token budget per study and show it to the customer before running.
- Charge AI analysis as an add-on, so basic studies stay cheap and heavy analysis pays for itself.

### Team and business features

- Team workspaces, roles and shared study templates.
- Integration with design and project tools.
- Programming interface for advanced customers.
- Consent records, access controls, usage limits and billing.

### Pricing options to consider

- Pay per published study or per completed response.
- Monthly team plans.
- Credits that do not expire.
- Higher fees for specialist participants.
- Managed research services for customers without their own research team.

## References

- [Prolific: research participants and AI evaluation](https://www.prolific.com/)
- [User Interviews: research recruitment](https://www.userinterviews.com/)
- [UserQ: Arabic/English user research in MENA](https://userq.com/)
- [Startup Tunisia: how to obtain the label](https://startup.gov.tn/en/startup_act/how_to_obtain_the_label)

