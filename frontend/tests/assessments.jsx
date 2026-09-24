import React from 'react';
import { createRoot } from 'react-dom/client';
import ParticipantAssessments from '../ParticipantAssessments.jsx';
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const assert = (condition, message) => { if (!condition) throw new Error(message); };
async function wait(predicate, message = 'State did not settle') { for (let i = 0; i < 150; i++) { if (predicate()) return; await sleep(20); } throw new Error(message); }
const text = () => document.body.textContent;
const button = label => [...document.querySelectorAll('button')].find(item => item.textContent === label);
async function click(label) { await wait(() => button(label) && !button(label).matches(':disabled'), `Missing enabled ${label}`); button(label).click(); await sleep(35); }
function fill(name, value) {
  const field = document.querySelector(`[name="${name}"]`); assert(field, `Missing ${name}`);
  Object.getOwnPropertyDescriptor(field instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype, 'value').set.call(field, value);
  field.dispatchEvent(new Event('input', { bubbles: true }));
}
const time = offset => new Date(Date.now() + offset).toISOString();
const copy = value => structuredClone(value);
const doc = { version: '1', digest: 'a'.repeat(64), body: 'Synthetic consent document: separate text assessment; retained evidence; withdrawal and independent human review.' };
const version = { id: 'version', assessment_key: 'fixture', version: 1, language: 'french', synthetic: true, state: 'approved', limitations: 'Synthetic fixture, not real validated language content.', policy: { duration_minutes: 30, max_starts_30_days: 3, cooldown_hours: 24, validity_days: 90, retention_days: 180 } };
const tasks = [{ id: 'choice', kind: 'single_choice', prompt: 'Choose the displayed greeting.', choices: [{ id: 'bonjour', label: 'Bonjour' }, { id: 'other', label: 'Other' }], criteria: { comprehension: 'Read the provided text.' } }, { id: 'text', kind: 'text', prompt: 'Write a short response. اكتب إجابة قصيرة', choices: [], criteria: { clarity: 'Make your meaning clear.' } }];
const makeAttempt = () => ({ id: 'attempt', version_id: version.id, language: 'french', state: 'started', consent_grant_id: 'grant', sequence: 1, started_at: time(-1000), deadline_at: time(1800000), retention_until: time(180 * 86400000), evidence_available: true, tasks, responses: null, submitted_at: null, decisions: [], appeal_requested_at: null, appeal_reason: null });
let state, generation = 0, calls = [], receipts = new Map(), release;
const reset = () => { state = { mode: 'normal', attempts: [], grants: [], lost: '', denied: '', current: [] }; receipts = new Map(); calls = []; };
const request = async (path, options = {}) => {
  assert(path.startsWith('/panel/'), 'Participant called an operator route');
  assert(!options.rawResponse, 'Transport requested raw response instead of parsed JSON');
  const body = options.body; calls.push({ path, body: copy(body), method: options.method });
  if (state.denied && path.includes(state.denied)) throw Object.assign(new Error('PRIVATE server explanation'), { status: 403 });
  if (!options.method) {
    if (path.endsWith('/language-assessment-consent')) return copy(doc);
    if (path.startsWith('/panel/language-assessment-consents?')) {
      const offset = Number(new URLSearchParams(path.split('?')[1]).get('offset'));
      return { items: copy(state.grants.slice(offset, offset + 25)), next_offset: offset + 25 < state.grants.length ? offset + 25 : null };
    }
    if (path.startsWith('/panel/language-assessments?')) {
      if (state.mode === 'slow') return new Promise(resolve => { release = () => resolve({ items: [{ ...version, limitations: 'STALE PRIVATE CONTENT' }], languages: ['french'], next_offset: null }); });
      return { items: state.mode === 'empty' || path.includes('offset=25') ? [] : [copy(version)], languages: ['french'], next_offset: state.mode === 'pages' && path.includes('offset=0') ? 25 : null };
    }
    if (path.startsWith('/panel/language-qualifications?')) return { current: copy(state.current), attempts: copy(state.attempts).map(item => ({ ...item, tasks: null, responses: null, decisions: item.decisions.map(decision => ({ ...decision, rationale: null, findings: null })) })), legacy: [{ language: 'ar', passed: true, expires_at: time(50000), evidence_kind: 'legacy_development_not_reviewed' }], next_offset: null };
    if (path === '/panel/language-assessment-attempts/attempt') return copy(state.attempts[0]);
    throw new Error(`Unexpected read ${path}`);
  }
  if (state.mode === 'late-mutation') return new Promise(resolve => { release = () => resolve({ id: 'late-grant', decision: 'granted', created_at: time(0) }); });
  const key = body.command_key || body.receipt_key;
  assert(typeof key === 'string' && key.length > 0, 'Mutation omitted command/receipt key');
  const serialized = JSON.stringify(body);
  if (receipts.has(key)) { const receipt = receipts.get(key); assert(receipt.serialized === serialized, 'Uncertain retry changed exact body'); return copy(receipt.result); }
  let result, kind;
  if (path.endsWith('/language-assessment-consent')) {
    assert(options.method === 'PUT' && body.presented_digest === doc.digest && body.document_version === doc.version, 'Consent contract drift');
    kind = body.decision === 'granted' ? 'grant' : 'withdraw';
    if (kind === 'withdraw') { assert(state.grants.some(grant => grant.id === body.grant_id), 'Withdrawal did not target an own grant'); state.grants.find(grant => grant.id === body.grant_id).withdrawn_at = time(0); state.attempts.filter(row => row.consent_grant_id === body.grant_id).forEach(row => { row.state = 'withdrawn'; }); }
    else state.grants.unshift({ id: 'grant', document_version: doc.version, created_at: time(0), withdrawn_at: null });
    result = { id: kind === 'grant' ? 'grant' : 'withdrawal', decision: body.decision, grant_id: body.grant_id || null, created_at: time(0) };
  } else if (path === '/panel/language-assessment-attempts') {
    kind = 'start'; assert(body.version_id === version.id && body.consent_grant_id === 'grant', 'Start contract drift');
    if (state.mode === 'cooldown') throw Object.assign(new Error('private'), { status: 409, code: 'ASSESSMENT_COOLDOWN' });
    state.attempts = [makeAttempt()]; result = state.attempts[0];
  } else if (path.endsWith('/submit')) {
    kind = 'submit'; assert(Object.keys(body.responses).sort().join(',') === 'choice,text', 'Submission omitted tasks');
    if (state.mode === 'validation') throw Object.assign(new Error('PRIVATE response'), { status: 422 });
    Object.assign(state.attempts[0], { state: 'submitted', responses: body.responses, submitted_at: time(0) }); result = state.attempts[0];
  } else if (path.endsWith('/appeal')) {
    kind = 'appeal'; assert(body.reason.trim(), 'Appeal omitted reason'); Object.assign(state.attempts[0], { appeal_requested_at: time(0), appeal_reason: body.reason }); result = state.attempts[0];
  } else throw new Error('Unexpected mutation');
  receipts.set(key, { serialized, result: copy(result) });
  if (state.lost === kind) { state.lost = ''; throw Object.assign(new Error('Lost success response'), kind === 'grant' ? { status: 200, code: 'INVALID_RESPONSE' } : {}); }
  return copy(result);
};
const root = createRoot(document.querySelector('#root'));
async function mount() { root.render(<ParticipantAssessments sessionKey={String(++generation)} request={request} />); await wait(() => text().includes('Grant assessment consent')); await sleep(40); }
async function grant() { document.querySelector('[name="assessment-consent"]').click(); await click('Grant assessment consent'); }
async function open() { await click('Open French attempt 1'); await wait(() => document.querySelector('[name="answer-text"]') || text().includes('Human decision · round 1') || text().includes('Raw evidence is no longer available') || text().includes('deadline passed')); }
try {
  reset(); state.mode = 'slow'; await mount(); assert(text().includes('Loading available assessments'), 'Loading state missing');
  state.mode = 'empty'; await mount(); release(); await sleep(50); assert(!text().includes('STALE PRIVATE CONTENT') && text().includes('No approved assessments'), 'Stale GET repopulated another session');
  reset(); state.denied = 'language-qualifications'; await mount(); assert(text().includes('This action is not permitted') && !text().includes('PRIVATE server'), 'Permission state leaks raw detail');
  reset(); state.denied = 'language-assessment-consents'; await mount(); assert(button('Reload consent grants') && !button('Confirm withdrawal') && !text().includes('PRIVATE server'), 'Denied consent enumeration exposed or inferred grants');
  reset(); state.mode = 'late-mutation'; await mount(); await grant(); await wait(() => release && button('Grant assessment consent').matches(':disabled'), 'Pending grant was not locked'); state.mode = 'normal'; await mount(); release(); await sleep(50); assert(!text().includes('Consent recorded at'), 'Late mutation repopulated another session');
  reset(); state.mode = 'empty'; state.grants = [...Array.from({ length: 25 }, (_, i) => ({ id: `withdrawn-${i}`, document_version: '1', created_at: time(-100000), withdrawn_at: time(-1000) })), { id: 'unused-retired-grant', document_version: '0', created_at: time(-200000), withdrawn_at: null }];
  await mount(); await click('Next consent grants'); assert(document.querySelector('[name="grant"]').value === 'unused-retired-grant', 'Unused historical grant missing from server page');
  await mount(); await click('Next consent grants'); assert(button('Grant assessment consent') && text().includes('No approved assessments') && !text().includes('Consent recorded at'), 'Fixture did not clear page memory for reload');
  assert(document.documentElement.scrollWidth <= innerWidth, 'Historical consent page overflow');
  const unusedDetails = [...document.querySelectorAll('details')].find(item => item.querySelector('summary')?.textContent.includes('Withdraw an exact')); unusedDetails.open = true; unusedDetails.querySelector('input[type=checkbox]').click(); await click('Confirm withdrawal');
  assert(calls.find(call => call.body?.decision === 'withdrawn').body.grant_id === 'unused-retired-grant', 'Reload withdrawal substituted a different grant'); assert(state.grants.at(-1).withdrawn_at && state.attempts.length === 0, 'Unused grant withdrawal required an attempt');
  await mount(); await click('Next consent grants'); assert(text().includes('Withdrawn') && !button('Confirm withdrawal'), 'Withdrawn unused grant remained actionable after reload');
  reset(); state.mode = 'pages'; await mount(); await click('Next assessments'); assert(text().includes('No approved assessments'), 'Catalogue pagination failed'); await click('Previous assessments');
  assert(button('Start French version 1').disabled, 'Start enabled without explicit consent');
  const beforeConsent = calls.length; await click('Grant assessment consent'); assert(calls.length === beforeConsent, 'Missing consent checkbox reached API');
  state.lost = 'grant'; await grant(); assert(text().includes('outcome is unconfirmed'), 'Malformed success did not retain exact consent request'); await click('Retry exact request'); assert(text().includes('Consent recorded at'), 'Consent retry did not resolve');
  state.mode = 'cooldown'; await click('Start French version 1'); assert(text().includes('cooldown has not ended'), 'Cooldown recovery absent'); state.mode = 'normal';
  state.lost = 'start'; await click('Start French version 1'); assert(button('Grant assessment consent').matches(':disabled'), 'Competing mutation allowed during unknown outcome'); await click('Retry exact request'); await wait(() => document.querySelector('[name="answer-text"]'));
  const starts = calls.filter(call => call.path === '/panel/language-assessment-attempts'); assert(JSON.stringify(starts.at(-1).body) === JSON.stringify(starts.at(-2).body), 'Start retry changed body'); assert(state.attempts.length === 1, 'Retry duplicated attempt');
  const beforeSubmit = calls.filter(call => call.path.endsWith('/submit')).length; await click('Submit answers for human review'); assert(calls.filter(call => call.path.endsWith('/submit')).length === beforeSubmit, 'Blank submission reached API');
  document.querySelector('[name="answer-choice"]').click(); fill('answer-text', '   '); await sleep(20); await click('Submit answers for human review'); assert(text().includes('Answer every task'), 'Whitespace validation missing');
  fill('answer-text', 'Bonjour. هذه إجابة تجريبية.'); await sleep(20); state.mode = 'validation'; await click('Submit answers for human review'); assert(document.querySelector('[name="answer-text"]').value.includes('Bonjour'), '422 erased typed answer'); assert(!text().includes('PRIVATE response'), 'Server error echoed');
  state.mode = 'normal'; state.lost = 'submit'; await click('Submit answers for human review'); assert(document.querySelector('[name="answer-text"]').matches(':disabled'), 'Unknown submit leaves editable body'); await click('Retry exact request'); await wait(() => text().includes('Awaiting a manual human decision')); assert(text().includes('No current reviewed qualifications'), 'Synthetic submission became eligibility');
  state.attempts[0].state = 'adjudicated'; state.attempts[0].decisions = [{ id: 'decision', round: 1, verdict: 'not_qualified', findings: { text: { clarity: 'not_met' } }, rationale: 'Synthetic reviewer fixture only.', decided_at: time(-1000), expires_at: null }];
  await click('Refresh selected attempt'); await wait(() => button('Request independent appeal')); fill('appeal-reason', 'Please review the text criterion again.'); await sleep(20); state.lost = 'appeal'; await click('Request independent appeal'); await click('Retry exact request'); await wait(() => text().includes('Awaiting a different reviewer.'));
  const consentDetails = [...document.querySelectorAll('details')].find(item => item.querySelector('summary')?.textContent.includes('Withdraw an exact')); consentDetails.open = true;
  const withdrawalForm = consentDetails.querySelector('form'); withdrawalForm.querySelector('input[type=checkbox]').click(); state.lost = 'withdraw'; await click('Confirm withdrawal'); await click('Retry exact request'); await wait(() => text().includes('This exact consent grant was withdrawn')); assert(state.attempts[0].state === 'withdrawn', 'Withdrawal did not revoke attempt');
  const withdrawals = calls.filter(call => call.body?.decision === 'withdrawn'); assert(JSON.stringify(withdrawals[0].body) === JSON.stringify(withdrawals[1].body), 'Withdrawal retry changed exact grant/body');
  for (const kind of ['/submit', '/appeal']) { const commands = calls.filter(call => call.path.endsWith(kind)); assert(JSON.stringify(commands.at(-1).body) === JSON.stringify(commands.at(-2).body), `${kind} retry drift`); }
  reset(); state.attempts = [{ ...makeAttempt(), deadline_at: time(-1000) }]; await mount(); await open(); assert(!button('Submit answers for human review'), 'Expired attempt remained submittable');
  reset(); state.attempts = [{ ...makeAttempt(), state: 'adjudicated', evidence_available: false, retention_until: time(-1000), responses: { text: 'PRIVATE EXPIRED ANSWER' }, decisions: [{ id: 'old', round: 1, verdict: 'qualified', decided_at: time(-40 * 86400000), expires_at: time(-1000), rationale: 'PRIVATE EXPIRED RATIONALE' }] }]; await mount(); await open(); assert(!text().includes('PRIVATE EXPIRED') && !button('Request independent appeal'), 'Expired evidence/appeal leaked');
  reset(); state.attempts = [makeAttempt()]; state.current = [{ language: 'french', assessment_version: 1, decision_id: 'current-fixture', expires_at: time(90 * 86400000) }]; await mount(); await open();
  assert(document.documentElement.scrollWidth <= innerWidth, 'Horizontal mobile overflow');
  assert([...document.querySelectorAll('button, select, textarea')].every(element => element.getBoundingClientRect().height >= 44), 'Control below 44px');
  assert([...document.querySelectorAll('input, select, textarea')].every(element => element.labels?.length), 'Form control missing native label');
  assert(text().includes('Synthetic practice — not recruitment eligibility') && text().includes('Legacy development results — not reviewed qualifications'), 'Provenance distinction missing');
  assert(!calls.some(call => call.path.includes('material') || call.path.includes('workspaces')), 'Operator endpoint reached');
  document.querySelector('#fixture-result').textContent = 'PASS: consent enumeration, reload/retired-unused-grant withdrawal, bounded consent pagination, malformed success, exact retries, start/cooldown, answer validation, manual review, appeal, exact withdrawal, history, expiry/retention, stale reads/mutations, permission, native labels and 44px responsive controls. Synthetic only.';
} catch (error) { document.querySelector('#fixture-result').textContent = `FAIL: ${error.message}`; console.error(error); }
