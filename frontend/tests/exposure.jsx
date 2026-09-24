// Mocked HTTP only: not browser-to-database E2E. One test waits a real five seconds.
import React from 'react';
import { createRoot } from 'react-dom/client';
import CollectionRunner from '../CollectionRunner.jsx';

const root = createRoot(document.querySelector('#root'));
const sessionId = '00000000-0000-4000-8000-000000000001';
const versionId = '00000000-0000-4000-8000-000000000002';
const attemptId = '00000000-0000-4000-8000-000000000003';
const imageBlob = new Blob(['<svg xmlns="http://www.w3.org/2000/svg" width="800" height="400"><rect width="800" height="400" fill="#eff6f2"/><text x="90" y="200" font-size="44" fill="#142923">Remember the green garden</text></svg>'], { type: 'image/svg+xml' });
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
function assert(value, message) { if (!value) throw new Error(message); }
async function wait(predicate, message, timeout = 2500) {
  const until = performance.now() + timeout;
  while (performance.now() < until) { if (predicate()) return; await sleep(15); }
  throw new Error(message);
}
const button = label => [...document.querySelectorAll('button')].find(b => b.textContent === label);
async function click(label) { await wait(() => button(label) && !button(label).disabled, `Missing enabled ${label}`); button(label).click(); await sleep(20); }
const checkConcealed = () => assert(!document.querySelector('img') || document.querySelector('img').hidden, 'Stimulus must be concealed');
let model;
function snapshot() {
  return { session_id: sessionId, version_id: versionId, revision: model.answer ? 1 : 0, last_sequence: model.sequence, answers: {}, complete: !!model.answer, state: 'active', submitted_at: null,
    block: model.answer ? null : { block_key: 'exposure', schema_version: 1, type: 'five_second', prompt: 'Take a first look', required: true,
      config: { exposure_ms: 5000, interruption_policy: 'invalidate', recall_block_ids: ['recall'] }, exposure_protocol_versions: [1, 2], attempt_state: model.state, attempt_id: model.state === 'not_started' ? null : attemptId, visible_ms: model.visibleMs } };
}
const json = data => new Response(JSON.stringify(data), { status: 200, headers: { 'Content-Type': 'application/json' } });
window.fetch = async (url, options = {}) => {
  const local = model;
  const path = String(url).replace(`/api/v1/collection/sessions/${sessionId}`, '');
  const body = options.body ? JSON.parse(options.body) : null;
  local.calls.push({ path, body, headers: options.headers });
  if (!path) {
    if (['preparing', 'started'].includes(local.state)) { local.state = 'interrupted'; local.visibleMs = null; }
    return json(snapshot());
  }
  if (path.endsWith('/prepare')) {
    assert(body.protocol_version === 2, 'Must negotiate v2');
    assert(local.state === 'not_started', 'A second preparation must not be requested');
    local.state = 'preparing'; local.capability = body.capability;
    return json({ protocol_version: 2, attempt_id: attemptId, state: 'preparing', asset_ref: { asset_id: 'fixture-image' }, preparation_timeout_ms: 30000, exposure_ms: 5000 });
  }
  if (path.startsWith('/assets/')) {
    assert(options.headers['X-Exposure-Token'] === local.capability, 'Asset must be bound to preparation');
    assert(!local.claimed, 'Asset downloaded more than once'); local.claimed = true;
    if (local.delayImage) await sleep(800);
    return new Response(local.decodeFailure ? new Blob(['not an image'], { type: 'image/png' }) : imageBlob);
  }
  if (path.endsWith('/start')) {
    assert(local.claimed, 'Start before asset fetched');
    local.state = 'started';
    if (local.loseStart) throw new TypeError('Synthetic lost start acknowledgement');
    return json({ protocol_version: 2, attempt_id: attemptId, state: 'started', replay: false, exposure_ms: 5000 });
  }
  if (path === '/events') {
    const event = body.events[0].event;
    const previous = local.events.find(e => e.client_event_id === event.client_event_id);
    if (previous) assert(JSON.stringify(previous) === JSON.stringify(event), 'Event replay body changed');
    else {
      assert(event.sequence === local.sequence + 1, 'Event sequence not contiguous');
      local.sequence = event.sequence; local.events.push(event);
      if (event.kind !== 'exposure.started') { local.state = event.kind === 'exposure.interrupted' ? 'interrupted' : 'completed'; local.visibleMs = event.elapsed_ms; }
    }
    if (local.loseEnd && event.kind === 'exposure.ended' && !previous) throw new TypeError('Synthetic lost end acknowledgement');
    return json({ saved: true, last_sequence: local.sequence });
  }
  if (path.startsWith('/answers/')) {
    if (local.failAnswer) { local.failAnswer = false; throw new TypeError('Synthetic answer failure'); }
    local.answer = body; return json({ saved: true });
  }
  if (path === '/withdraw') { local.withdrawn = true; if (local.delayWithdrawal) await sleep(400); return json({ withdrawn: true }); }
  throw new Error(`Unexpected mocked path ${path}`);
};
let generation = 0;
async function mount(options = {}) {
  root.render(null); await sleep(30);
  model = { state: 'not_started', visibleMs: null, calls: [], events: [], sequence: -1, ...options };
  root.render(<CollectionRunner key={++generation} sessionId={sessionId} token={'s'.repeat(64)} />);
  await wait(() => document.querySelector('#timed-heading'), 'Collection runner did not mount');
  assert(document.activeElement.id === 'timed-heading', 'Question heading should receive focus');
  checkConcealed();
}
async function ready() { await click('Prepare image'); await wait(() => button('Show image for five seconds'), 'Image never decoded'); checkConcealed(); }
async function show() { await ready(); await click('Show image for five seconds'); await wait(() => document.querySelector('img') && !document.querySelector('img').hidden, 'Exposure did not become visible'); }
try {
  await mount({ delayImage: true, loseEnd: true });
  await click('Prepare image');
  assert(document.querySelector('[role="status"]').textContent.includes('Loading'), 'Loading status missing');
  await sleep(350);
  assert(model.events.length === 0 && model.state === 'preparing', 'Loading consumed exposure time');
  checkConcealed();
  await wait(() => button('Show image for five seconds'), 'Ready button missing');
  const startButton = button('Show image for five seconds'); startButton.focus();
  assert(document.activeElement === startButton, 'Start button not focusable');
  startButton.click(); startButton.click();
  await wait(() => !document.querySelector('img').hidden, 'Image did not show');
  assert(model.calls.filter(c => c.path.endsWith('/start')).length === 1, 'Double activation created duplicate start');
  await wait(() => button('Retry saving timing'), 'Lost end acknowledgement did not offer retry', 6200);
  checkConcealed();
  await click('Retry saving timing');
  await click('Continue to recall questions');
  assert(model.answer.status === 'responded' && !model.answer.value.interrupted && model.answer.value.visible_ms >= 4900 && model.answer.value.visible_ms <= 5250, 'Incorrect clean observed timing');
  assert(model.events.map(e => e.sequence).join(',') === '0,1', 'Replay changed sequence');

  await mount(); await show();
  Object.defineProperty(document, 'hidden', { configurable: true, value: true });
  document.dispatchEvent(new Event('visibilitychange')); checkConcealed();
  delete document.hidden;
  await click('Continue to recall questions');
  assert(model.answer.value.interrupted, 'Hidden tab counted clean');

  await mount(); await show();
  window.dispatchEvent(new Event('pagehide')); checkConcealed();
  await click('Continue to recall questions');
  assert(model.answer.value.interrupted, 'Page exit counted clean');

  await mount({ decodeFailure: true }); await click('Prepare image');
  await wait(() => model.state === 'interrupted', 'Decode failure did not interrupt attempt');
  checkConcealed();
  document.querySelector('details').open = true;
  await click('Record inability'); assert(model.answer.status === 'unable', 'Decode failure fabricated response');

  await mount({ loseStart: true }); await ready(); await click('Show image for five seconds');
  await wait(() => button('Recover session without replay'), 'Lost start did not require recovery'); checkConcealed();
  await click('Recover session without replay');
  assert(!button('Prepare image') && !button('Show image for five seconds'), 'Recovery offered clean replay');
  document.querySelector('details').open = true;
  await click('Record inability'); assert(model.answer.status === 'unable', 'Unknown timing fabricated observed zero');

  await mount({ failAnswer: true }); await ready();
  document.querySelector('details').open = true; await click('Record inability');
  await wait(() => !button('Record inability').disabled, 'Inability retry not available');
  assert(!button('Show image for five seconds'), 'Failed inability save restored a revoked image');
  checkConcealed(); await click('Record inability');
  assert(model.answer.status === 'unable', 'Inability retry failed');

  await mount({ state: 'started', claimed: true });
  assert(!button('Prepare image') && !button('Show image for five seconds'), 'Reload offered another exposure');
  assert(model.state === 'interrupted' && model.visibleMs === null, 'Reload did not retain honest unknown');

  await mount({ delayWithdrawal: true }); await show();
  const withdrawal = [...document.querySelectorAll('details')].find(d => d.querySelector('summary').textContent === 'Withdraw participation');
  withdrawal.open = true; await click('Confirm withdrawal'); checkConcealed();
  await wait(() => document.body.textContent.includes('Participation withdrawn.'), 'Withdrawal failed');

  await mount();
  assert(document.documentElement.scrollWidth <= innerWidth, 'Horizontal overflow');
  assert(button('Prepare image').getBoundingClientRect().height >= 44, 'Small touch target');
  const image = document.querySelector('img');
  assert(image.hidden && image.alt, 'Concealed stimulus lacks accessible image semantics');
  document.querySelector('#fixture-result').textContent = 'PASS: mocked CollectionRunner: delayed decode, actual five seconds, duplicate click, exact event retry, hidden tab, page exit, decode failure, lost start, reload, inability, withdrawal, focus and touch layout. Not DB E2E.';
} catch (error) {
  document.querySelector('#fixture-result').textContent = 'FAIL: ' + error.message;
  console.error(error);
}
