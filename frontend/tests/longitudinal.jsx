// Synthetic HTTP contracts; persisted recovery and races are separate PostgreSQL tests.
import React from 'react';
import { createRoot } from 'react-dom/client';
import { flushSync } from 'react-dom';
import LongitudinalRunner from '../LongitudinalRunner.jsx';
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const assert = (value, message) => { if (!value) throw new Error(message); };
async function wait(predicate, message) { for (let i = 0; i < 150; i++) { if (predicate()) return; await sleep(20); } throw new Error(message); }
const button = label => [...document.querySelectorAll('button')].find(element => element.textContent === label);
async function click(label) { await wait(() => button(label) && !button(label).disabled, `Unavailable ${label}`); button(label).click(); await sleep(40); }
const slot = { id: 'slot', version_id: 'v', starts_at: '2027-01-01T10:00:00Z', ends_at: '2027-01-01T11:00:00Z', timezone: 'Africa/Tunis' };
let mode = 'normal', sessionId = null, revision = null, capability, rotations = 0, mount = 0;
const commands = [], deferred = [];
const occurrence = () => ({ id: 'occurrence', ordinal: 0, state: 'open', timezone: 'Africa/Tunis', opens_at: slot.starts_at, due_at: slot.ends_at, grace_at: slot.ends_at, session_id: sessionId, session_revision: revision });
const projection = () => ({ session_id: sessionId, version_id: 'v', locale: 'ar', state: 'active', last_sequence: -1, revision, answers: {}, block: null, complete: false });
const request = async (path, options) => {
  if (options?.method) {
    const body = JSON.parse(options.body); commands.push({ path, body });
    if (path.endsWith('/start')) { sessionId = 'saved-diary'; capability = body.capability; revision = 0; }
    else if (path.endsWith('/recover')) {
      if (mode === 'conflict') { mode = 'normal'; revision++; return Response.json({}, { status: 409 }); }
      assert(Number.isInteger(body.expected_revision), 'Recovery omitted observed revision');
      if (body.capability !== capability) { assert(body.expected_revision === revision, 'Recovery reused stale revision'); revision++; rotations++; capability = body.capability; }
      if (mode === 'lost') { mode = 'normal'; throw new TypeError('Synthetic lost acknowledgement'); }
    } else throw new Error('Unexpected synthetic command');
    return Response.json(projection());
  }
  if (mode === 'unavailable') throw new TypeError('Synthetic refresh failure');
  if (mode === 'denied') return Response.json({}, { status: 403 });
  if (mode === 'slow') return new Promise(resolve => deferred.push(() => resolve(Response.json(path.startsWith('/diary') ? [occurrence()] : []))));
  if (mode === 'empty') return Response.json([]);
  return Response.json(path.startsWith('/slots?') ? [slot] : path.startsWith('/bookings?') ? [{ id: 'booking', state: 'booked', revision: 1, attendance: null, slot }] : [occurrence()]);
};
window.fetch = async (path, options) => {
  assert(path === '/api/v1/collection/sessions/saved-diary' && !options.method, 'Unexpected collection request');
  assert(options.headers['X-Session-Token'] === capability && options.cache === 'no-store', 'Wrong memory-only recovered credential');
  return Response.json(projection());
};
const root = createRoot(document.getElementById('root'));
function render() { flushSync(() => root.render(<LongitudinalRunner key={++mount} workspaceId="w" versionId="v" request={request} />)); }
async function run() {
  render();
  await wait(() => button('Start occurrence'), 'Schedule did not load');
  assert(['Book selected time', 'Confirm reschedule', 'Confirm cancellation', 'Africa/Tunis', 'Attendance: unknown'].every(s => document.body.textContent.includes(s)), 'Booking/time controls missing');
  await click('Start occurrence');
  await wait(() => document.querySelector('main[lang="ar"][dir="rtl"]'), 'Original Arabic locale was not pinned');
  assert(document.querySelectorAll('main').length === 1, 'Nested main landmarks');
  await click('Return to diary schedule');
  render();
  await wait(() => button('Recover occurrence'), 'Reloaded occurrence cannot recover');
  assert(!button('Resume occurrence'), 'Reload falsely retained the original credential');
  mode = 'lost'; await click('Recover occurrence');
  await wait(() => button('Retry identical request'), 'Uncertain recovery lost its pending body');
  assert(button('Recover occurrence').disabled, 'Unknown outcome allowed another rotation');
  await click('Retry identical request');
  await wait(() => document.querySelector('main[dir="rtl"]'), 'Recovered occurrence did not open');
  assert(rotations === 1 && JSON.stringify(commands.at(-1)) === JSON.stringify(commands.at(-2)), 'Retry changed the capability or rotated twice');
  await click('Return to diary schedule');
  mode = 'conflict'; await click('Recover occurrence');
  assert(button('Recover occurrence').disabled && !button('Retry identical request'), 'Conflict allowed stale recovery');
  mode = 'unavailable'; await click('Refresh schedule');
  assert(button('Recover occurrence').disabled, 'Failed refresh unlocked recovery');
  mode = 'normal'; await click('Refresh schedule');
  await click('Recover occurrence');
  await wait(() => document.querySelector('main[dir="rtl"]'), 'Recovery after refreshed revision failed');
  assert(commands.at(-1).body.expected_revision === 2 && rotations === 2, 'Fresh recovery used wrong revision');
  await click('Return to diary schedule');
  mode = 'denied'; await click('Refresh schedule');
  assert(!document.body.textContent.includes('Occurrence 1') && !button('Confirm cancellation'), 'Access denial retained private schedule');
  mode = 'slow'; render();
  await wait(() => deferred.length === 3, 'Delayed schedule fixture not entered');
  mode = 'empty'; render();
  await wait(() => document.body.textContent.includes('No diary occurrences.'), 'New empty scope not displayed');
  deferred.forEach(resolve => resolve()); await sleep(60);
  assert(!document.body.textContent.includes('Occurrence 1'), 'Late schedule repopulated an unmounted scope');
  mode = 'normal'; render();
  await wait(() => button('Recover occurrence'), 'Final schedule not ready');
  assert(commands.every(command => !document.body.textContent.includes(command.body.capability)), 'Credential rendered into page');
  assert(!localStorage.length && !sessionStorage.length, 'Credential persisted in browser storage');
  assert(document.documentElement.scrollWidth <= innerWidth + 1, 'Horizontal overflow');
  document.getElementById('result').textContent = 'PASS: booking controls; memory-only start/reload recovery; identical uncertain replay; revision conflict requires successful refresh; pinned Arabic; denial and late-response fencing.';
}
run().catch(error => { document.getElementById('result').textContent = `FAIL: ${error.message}`; });
