// Synthetic contracts; backend ownership and financial retention use PostgreSQL tests.
import React from 'react';
import { createRoot } from 'react-dom/client';
import ParticipantHistory from '../ParticipantHistory.jsx';
import '../account.css';
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
let checks = 0;
const assert = (value, message) => { if (!value) throw new Error(message); checks++; };
async function wait(predicate, message) { for (let i = 0; i < 150; i++) { if (predicate()) return; await sleep(20); } throw new Error(message); }
const button = label => [...document.querySelectorAll('button')].find(item => item.textContent === label);
async function click(label) { await wait(() => button(label) && !button(label).disabled, `Missing ${label}`); button(label).click(); await sleep(30); }
const wid = '00000000-0000-4000-8000-000000000001', other = '00000000-0000-4000-8000-000000000002';
const sid = '00000000-0000-4000-8000-000000000003', second = '00000000-0000-4000-8000-000000000004';
const rid = '00000000-0000-4000-8000-000000000005', pid = '00000000-0000-4000-8000-000000000006';
const bid = '00000000-0000-4000-8000-000000000007';
let mode = 'normal', serverAppeal = null, release, loseAppeal = true;
const calls = [], commands = [];
const item = (id, state) => ({ session_id: id, version_id: second, occurrence_id: null, locale: 'fr', submitted_at: '2026-01-01T12:00:00Z', review_state: state, appeal_state: serverAppeal?.state || null });
const page = (items = [], next_offset = null) => ({ items, next_offset });
const request = async (path, options = {}) => {
  calls.push({ path, options });
  if (path.startsWith('/participant/history?')) return page(mode === 'empty' ? [] : [{ workspace_id: wid }, { workspace_id: other }]);
  if (path.includes(`/${other}/`)) return page();
  if (path.includes(`/${wid}/responses?`)) {
    if (mode === 'denied') throw Object.assign(new Error('private failure'), { status: 403 });
    if (mode === 'late') return new Promise(resolve => { release = () => resolve(page([{ ...item(sid, 'accepted'), locale: 'STALE PRIVATE HISTORY' }])); });
    if (mode === 'keyboard') return page([{ ...item(second, 'accepted'), locale: 'Keyboard refresh confirmed' }]);
    if (path.includes('offset=25')) return page([item(second, 'accepted')]);
    return page([item(sid, serverAppeal ? 'appealed' : 'rejected')], 25);
  }
  if (path.includes('/reviews/sessions/') && path.endsWith('/status')) return { state: serverAppeal ? 'appealed' : 'rejected', decisions: [{ verdict: 'rejected', rationale: 'راجعت النص الأصلي — français', evidence: ['دليل أصلي 🙂 é'] }], appeal: serverAppeal };
  if (path.endsWith('/appeal')) {
    commands.push(structuredClone(options.body));
    serverAppeal = { id: pid, state: 'open', reason: options.body.reason };
    if (loseAppeal) { loseAppeal = false; throw new TypeError('synthetic lost response'); }
    return { id: pid, state: 'open' };
  }
  if (path.includes(`/rewards/${rid}/payments?`)) return page([{ id: pid, state: 'failed', created_at: '2026-01-03T12:00:00Z', manual_record_only: true }]);
  if (path.includes('/rewards?')) return page([{ id: rid, amount_millimes: 1000, currency: 'TND', state: 'earned', created_at: '2026-01-01T12:00:00Z', settled_at: null, manual_record_only: true }]);
  if (path.includes('/attendance?')) return page([{ id: bid, version_id: second, state: 'booked', attendance: 'unknown', attendance_at: null, starts_at: '2026-01-02T12:00:00Z', ends_at: '2026-01-02T12:30:00Z', timezone: 'Africa/Tunis' }]);
  throw new Error('Unexpected fixture route');
};
const root = createRoot(document.querySelector('#root'));
async function workspace(value) {
  const select = document.querySelector('select'); assert(select, 'Workspace selector missing');
  select.value = value; select.dispatchEvent(new Event('change', { bubbles: true })); await sleep(40);
}
async function kind(value) { document.querySelector(`[name="history-kind"][value="${value}"]`).click(); await sleep(40); }
async function expand(label) {
  const summary = [...document.querySelectorAll('summary')].find(item => item.textContent === label);
  assert(summary, `Missing ${label}`); summary.click(); await sleep(40);
}
async function reason(value) {
  const field = document.querySelector('textarea');
  Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set.call(field, value);
  field.dispatchEvent(new Event('input', { bubbles: true })); await sleep(20);
}
try {
  root.render(<ParticipantHistory request={request} sessionKey="first-session" />);
  await wait(() => document.querySelector('select'), 'Scopes did not load');
  assert(!document.querySelector('[aria-label="Responses"]'), 'History exposed without a selected scope');
  await workspace(wid); await wait(() => document.body.textContent.includes('Response reference:'), 'Responses did not load');
  assert(document.body.textContent.includes('not a score shared across clients'), 'Cross-client score boundary missing');
  assert(document.body.textContent.includes('denominator covers loaded records only'), 'Quality denominator is not qualified');
  await click('Load more responses');
  assert(document.querySelectorAll('[aria-label="Responses"] .item-list > li').length === 2, 'Response pagination failed');
  assert(!button('Load more responses'), 'Terminal page still offers more records');
  await expand('Review decision and appeal');
  await wait(() => document.querySelector('textarea'), 'Appeal form missing');
  assert(document.body.textContent.includes('دليل أصلي 🙂 é'), 'Original multilingual evidence changed');
  assert(document.querySelector('[dir="auto"]'), 'Original evidence lacks direction handling');
  await reason('   '); document.querySelector('textarea').form.requestSubmit(); await sleep(30);
  assert(commands.length === 0 && document.body.textContent.includes('Explain why'), 'Whitespace appeal reached the server');
  await reason('Please reconsider my original response.');
  const form = document.querySelector('textarea').form; form.requestSubmit(); form.requestSubmit();
  await wait(() => button('Retry identical appeal'), 'Uncertain appeal recovery missing');
  assert(commands.length === 1, 'Duplicate or automatic appeal replay');
  assert(!document.querySelector('textarea'), 'Uncertain appeal can be changed');
  await click('Refresh review status');
  await wait(() => document.body.textContent.includes('Appeal: open'), 'Recorded uncertain appeal was not recoverable');
  assert(commands.length === 1, 'Status refresh replayed a mutation');
  await click('Retry identical appeal');
  await wait(() => document.body.textContent.includes('Your appeal was recorded.'), 'Appeal retry did not confirm success');
  assert(commands.length === 2 && JSON.stringify(commands[0]) === JSON.stringify(commands[1]), 'Appeal retry changed its identity or payload');
  await wait(() => document.body.textContent.includes('Human review: appealed'), 'History did not refresh after confirmed appeal');
  mode = 'denied'; await click('Refresh responses');
  await wait(() => document.body.textContent.includes('consent or access has changed'), 'Privacy denial missing');
  assert(!document.body.textContent.includes(sid) && !document.body.textContent.includes('دليل أصلي'), 'Denied read retained private response or evidence');
  assert(!document.body.textContent.includes('private failure'), 'Raw error leaked');
  await kind('rewards'); await wait(() => document.body.textContent.includes(rid), 'Retained rewards unavailable after research denial');
  assert(document.body.textContent.includes('not proof of an automatic bank transfer'), 'Manual payment truth boundary missing');
  await expand('View manual payment records'); await wait(() => document.body.textContent.includes(pid), 'Payment history missing');
  assert(document.body.textContent.includes('failed'), 'Failed payment state hidden');
  await kind('attendance'); await wait(() => document.body.textContent.includes(bid), 'Attendance history missing');
  assert(document.body.textContent.includes('Attendance: unknown'), 'Unknown attendance inferred as absent');
  assert(!document.querySelector('a[href^="https:"]'), 'Private meeting link rendered');
  mode = 'late'; await kind('responses'); await wait(() => release, 'Delayed history did not start');
  await workspace(other); await wait(() => document.body.textContent.includes('No currently available responses'), 'Second workspace empty state missing');
  release(); await sleep(40);
  assert(!document.body.textContent.includes('STALE PRIVATE HISTORY'), 'Previous workspace response repopulated current scope');
  release = null; await workspace(wid); await wait(() => release, 'Delayed session response missing');
  mode = 'empty'; root.render(<ParticipantHistory request={request} sessionKey="new-session" />);
  await wait(() => document.body.textContent.includes('No participation records yet'), 'New-session empty state missing');
  release(); await sleep(40);
  assert(!document.body.textContent.includes('STALE PRIVATE HISTORY') && !document.querySelector('select'), 'Previous session repopulated current history');
  mode = 'normal'; await click('Refresh participation scopes'); await workspace(wid);
  await wait(() => document.querySelector('[aria-label="Responses"] .item-list'), 'Final history view missing');
  for (const field of document.querySelectorAll('select,input,textarea')) assert(field.labels.length > 0, 'Form control lacks native label');
  const refresh = button('Refresh responses'); refresh.focus(); assert(document.activeElement === refresh, 'Native action cannot receive keyboard focus');
  for (const control of document.querySelectorAll('button,select')) assert(control.getBoundingClientRect().height >= 44, 'Touch control smaller than44px');
  assert(document.querySelectorAll('main').length === 1, 'Nested main landmarks');
  assert(document.documentElement.scrollWidth <= innerWidth, 'Horizontal viewport overflow');
  assert(localStorage.length === 0 && sessionStorage.length === 0, 'History persisted in browser storage');
  mode = 'keyboard';
  document.querySelector('#fixture-result').textContent = `PASS ${checks} participant history assertions: scoped pagination, human evidence/appeals, exact uncertain retry, financial truth, attendance, denial, stale workspace/session fencing, labels/focus/touch/overflow. Mock HTTP only.`;
} catch (error) { document.querySelector('#fixture-result').textContent = `FAIL ${error.message}`; console.error(error); }
