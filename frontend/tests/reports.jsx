import React from 'react';
import { createRoot } from 'react-dom/client';
import ResearchReports from '../ResearchReports.jsx';

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
function assert(condition, message) { if (!condition) throw new Error(message); }
async function wait(condition, message) { for (let n = 0; n < 150; n++) { if (condition()) return; await sleep(20); } throw new Error(`Timed out: ${message}`); }
const text = () => document.querySelector('#root').textContent;
const button = name => [...document.querySelectorAll('button')].find(element => element.textContent.trim() === name);
async function click(name) { await wait(() => button(name) && !button(name).disabled, `button ${name}`); button(name).click(); await sleep(20); }
function change(element, value) { const setter = Object.getOwnPropertyDescriptor(element instanceof HTMLSelectElement ? HTMLSelectElement.prototype : HTMLInputElement.prototype, 'value').set; setter.call(element, value); element.dispatchEvent(new Event('input', { bubbles: true })); element.dispatchEvent(new Event('change', { bubbles: true })); }
const failure = (status, code) => Object.assign(new Error('Synthetic private fixture error'), { status, code });
const deferred = () => { let resolve; const promise = new Promise(done => { resolve = done; }); return { promise, resolve }; };
const root = createRoot(document.querySelector('#root'));
const reportId = '11111111-1111-4111-8111-111111111111', otherId = '22222222-2222-4222-8222-222222222222';
const exportId = '33333333-3333-4333-8333-333333333333';
const original = 'مرحبا بالعالم — جودة البحث · Français : fidélité à l’original';
const types = { pdf: 'application/pdf', xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', json: 'application/json', csv: 'text/csv' };
let mounts = 0, checked = 0;
const created = new Set(), revoked = new Set(), downloads = [];
const nativeCreate = URL.createObjectURL.bind(URL), nativeRevoke = URL.revokeObjectURL.bind(URL);
URL.createObjectURL = blob => { const url = nativeCreate(blob); created.add(url); return url; };
URL.revokeObjectURL = url => { revoked.add(url); nativeRevoke(url); };
HTMLAnchorElement.prototype.click = function () { downloads.push({ name: this.download, url: this.href }); };
const initial = () => ({ id: reportId, version_id: otherId, revision: 2, state: 'draft', snapshot_id: otherId, metrics: { metric_version: '1', source_unit: 'session', sampling: 'panel_sample_not_population_representative', included: 12, original_text: original, harmless_text: '<img src=x onerror=alert(1)>', responses: { numerator: 12, denominator: 15, value: 0.8 }, missingness: { numerator: 3, denominator: 15, value: 0.2 } } });
function mock() {
  const state = { record: initial(), calls: [], list: { items: [{ id: reportId, revision: 2, state: 'draft' }, { id: otherId, revision: 1, state: 'approved' }], has_more: false }, mode: '', lastExport: { format: 'pdf', scope: 'summary' }, hook: null };
  state.request = async (path, options = {}) => {
    const call = { path, method: options.method || 'GET', body: options.body, raw: options.rawResponse, signal: options.signal };
    state.calls.push(call);
    if (state.hook) { const override = state.hook(call); if (override !== undefined) return override; }
    await sleep(15);
    if (path.includes('/reports?')) {
      if (state.mode === 'list-error') throw failure(503, 'UNAVAILABLE');
      if (state.mode === 'list-limit') throw failure(422, 'REPORT_INDEX_LIMIT');
      return state.list;
    }
    if (path.endsWith('/approve')) {
      if (state.mode === 'approve-forbidden') throw failure(403, 'FORBIDDEN');
      if (state.mode === 'approve-unknown') { state.mode = ''; throw failure(0, 'NETWORK_ERROR'); }
      if (state.mode === 'approve-lost') { state.record.state = 'approved'; state.mode = ''; throw failure(0, 'NETWORK_ERROR'); }
      if (state.mode === 'revision-conflict') { state.record.revision = 3; throw failure(409, 'REVISION_CONFLICT'); }
      state.record.state = 'approved'; return structuredClone(state.record);
    }
    if (path.endsWith('/exports')) {
      state.lastExport = options.body;
      if (state.mode === 'raw-forbidden' && options.body.scope === 'raw') throw failure(403, 'FORBIDDEN');
      if (state.mode === 'summary-forbidden') throw failure(403, 'FORBIDDEN');
      if (state.mode === 'export-unknown') { state.mode = ''; throw failure(0, 'NETWORK_ERROR'); }
      return { id: exportId, ...options.body };
    }
    if (path.endsWith(`/exports/${exportId}`)) {
      assert(options.rawResponse === true, 'Binary GET must request rawResponse');
      assert(options.signal instanceof AbortSignal, 'Binary GET must be abortable');
      if (state.mode === 'download-network') { state.mode = ''; throw failure(0, 'NETWORK_ERROR'); }
      if (state.mode === 'privacy-revoked') throw failure(409, 'ANALYSIS_UNAVAILABLE');
      if (state.mode === 'wrong-type') return new Response('not a report', { headers: { 'Content-Type': 'text/html' } });
      return new Response(original, { headers: { 'Content-Type': types[state.lastExport.format], 'Content-Disposition': 'attachment; filename="unsafe.html"' } });
    }
    if (path.includes('?revision=')) {
      const revision = Number(new URL(path, location.origin).searchParams.get('revision'));
      return { ...structuredClone(state.record), revision, state: 'approved' };
    }
    if (path.endsWith(`/${reportId}`)) return structuredClone(state.record);
    if (path.endsWith(`/${otherId}`)) return { ...structuredClone(state.record), id: otherId, revision: 1, state: 'approved', metrics: { original_text: 'Other authorized report' } };
    throw new Error(`Unexpected fixture path: ${path}`);
  };
  return state;
}
async function mount(state, session = `family-${++mounts}`, workspace = '44444444-4444-4444-8444-444444444444') {
  root.render(<main className="account-app"><h1>Workspace research</h1><ResearchReports request={state.request} sessionKey={session} workspaceId={workspace} /></main>);
  await sleep(30);
}
async function open(state) { await mount(state); await click('Report 11111111 · Revision 2'); await wait(() => text().includes(original), 'original metrics'); }
async function selectFormat(value) { change(document.querySelector('select'), value); await sleep(5); }
async function selectScope(value) { change(document.querySelectorAll('select')[1], value); await sleep(5); }
function check(condition, message) { assert(condition, message); checked++; }
async function run() {
  let state = mock(); state.mode = 'list-error'; await mount(state);
  await wait(() => text().includes('Reports could not be loaded'), 'read error');
  check(state.calls.every(call => call.method === 'GET'), 'Read failure never mutates');
  state.mode = ''; await click('Reload reports'); await wait(() => button('Report 11111111 · Revision 2'), 'read retry');
  state = mock(); state.mode = 'list-limit'; await mount(state);
  await wait(() => text().includes('This report page exceeds privacy-check limits'), 'bounded index failure explanation'); checked++;
  state = mock(); state.list = { items: [], has_more: false }; await mount(state);
  await wait(() => text().includes('No reports are available'), 'empty list'); checked++;
  state = mock(); state.list = {}; await mount(state); await wait(() => text().includes('Reports could not be loaded'), 'invalid list response fails closed'); checked++;
  state = mock(); await open(state);
  check(document.querySelectorAll('main').length === 1, 'Component must not nest main');
  check(!document.querySelector('img'), 'Report text must never become HTML');
  check(text().includes('not AI-generated findings') && text().includes('Draft — not approved'), 'Provenance and draft label visible');
  change(document.querySelector('input[type=number]'), '1'); await sleep(5); await click('View revision');
  await wait(() => text().includes('Historical preview'), 'revision history');
  check(button('Create PDF summary download').disabled, 'Historical revision must not silently export latest');
  check(!button('Approve revision 1'), 'Historical revision must not be approved as current');
  check(state.calls.some(call => call.path.endsWith('?revision=1')), 'Revision read uses current contract');
  await click('View latest revision');
  for (const format of Object.keys(types)) {
    for (const scope of ['summary', 'raw']) {
      await selectFormat(format); await selectScope(scope);
      const before = downloads.length;
      await click(`Create ${format.toUpperCase()} ${scope} download`);
      await wait(() => downloads.length === before + 1, `${format} ${scope} download`);
      check(downloads.at(-1).name === `report.${format}`, 'Filename must ignore response disposition');
      check(!document.querySelector('a[download]'), 'Download anchor removed');
    }
  }
  await sleep(1100); check([...created].every(url => revoked.has(url)), 'All object URLs are revoked after use');
  state = mock(); state.mode = 'raw-forbidden'; await open(state); await selectScope('raw'); await click('Create PDF raw download');
  await wait(() => text().includes('Raw export access is unavailable'), 'raw permission explanation'); checked++;
  await click('Reload latest report'); await wait(() => document.querySelector('select') && !document.querySelector('select').disabled, 'permission reload'); await selectScope('summary'); await click('Create PDF summary download');
  await wait(() => text().includes('PDF summary download sent'), 'summary after raw denial'); checked++;
  state = mock(); state.mode = 'summary-forbidden'; await open(state); await click('Create PDF summary download');
  await wait(() => text().includes('Summary export access is unavailable'), 'summary permission explanation'); checked++;
  state = mock(); state.mode = 'approve-forbidden'; await open(state); document.querySelector('input[type=checkbox]').click(); await click('Approve revision 2');
  await wait(() => text().includes('Approval is not permitted'), 'publish permission explanation'); checked++;
  state = mock(); state.mode = 'approve-unknown'; await open(state); document.querySelector('input[type=checkbox]').click(); await click('Approve revision 2');
  await wait(() => text().includes('Unconfirmed approval'), 'unknown approval');
  await sleep(100); check(state.calls.filter(call => call.method === 'POST').length === 1, 'Unknown approval is never auto replayed');
  await click('Retry exact request'); await wait(() => text().includes('Revision 2 is approved.'), 'manual approval retry');
  const approvals = state.calls.filter(call => call.method === 'POST');
  check(approvals.length === 2 && approvals[0].path === approvals[1].path && JSON.stringify(approvals[0].body) === JSON.stringify(approvals[1].body), 'Approval retry must preserve exact command');
  state = mock(); state.mode = 'approve-lost'; await open(state); document.querySelector('input[type=checkbox]').click(); await click('Approve revision 2');
  await wait(() => text().includes('Unconfirmed approval'), 'lost approval'); await click('Reload latest report'); await click('Accept confirmed approval');
  check(state.calls.filter(call => call.method === 'POST').length === 1, 'Reconciliation must not mutate');
  state = mock(); state.mode = 'export-unknown'; await open(state); await click('Create PDF summary download');
  await wait(() => text().includes('Unconfirmed export request'), 'unknown export');
  check(text().includes('duplicate export record'), 'Non-idempotent export retry warns of duplicates');
  check(document.querySelector('select').matches(':disabled'), 'Unknown command locks options');
  await click('Retry exact request'); await wait(() => text().includes('PDF summary download sent'), 'exact export retry');
  const posts = state.calls.filter(call => call.method === 'POST');
  check(posts.length === 2 && posts[0].path === posts[1].path && JSON.stringify(posts[0].body) === JSON.stringify(posts[1].body), 'Export retry preserves exact body/path');
  state = mock(); state.mode = 'download-network'; await open(state); await click('Create PDF summary download'); await click('Retry download');
  await wait(() => text().includes('PDF summary download sent'), 'download GET retry');
  check(state.calls.filter(call => call.method === 'POST').length === 1, 'Binary retry does not create another export');
  state = mock(); state.mode = 'privacy-revoked'; await open(state); const beforeRevoke = downloads.length; await click('Create PDF summary download');
  await wait(() => text().includes('Consent, source data, or privacy permissions changed'), 'privacy error');
  check(!text().includes(original) && downloads.length === beforeRevoke, 'Revocation clears metrics and releases no download');
  state = mock(); state.mode = 'wrong-type'; await open(state); const beforeType = downloads.length; await click('Create PDF summary download');
  await wait(() => !!button('Retry download') && !button('Retry download').disabled, 'wrong type failure');
  check(downloads.length === beforeType, 'Untrusted download MIME does not produce file');
  state = mock(); await open(state); const createButton = button('Create PDF summary download'); createButton.click(); createButton.click();
  await wait(() => text().includes('PDF summary download sent'), 'double-click completed');
  check(state.calls.filter(call => call.method === 'POST').length === 1, 'Synchronous mutation lock defeats double clicks');
  const latestURL = downloads.at(-1).url; const replacement = mock(); replacement.list = { items: [] }; await mount(replacement);
  check(revoked.has(latestURL), 'Session changes revoke pending object URLs');
  state = mock(); const oldList = deferred(); state.hook = call => call.path.includes('/reports?') ? oldList.promise : undefined;
  await mount(state); await wait(() => text().includes('Loading reports'), 'loading state');
  const next = mock(); next.list = { items: [] }; await mount(next); oldList.resolve(state.list); await sleep(40);
  check(text().includes('No reports are available') && !button('Report 11111111 · Revision 2'), 'Old list response fenced after identity change');
  state = mock(); const oldDetail = deferred(); state.hook = call => call.path.endsWith(`/${reportId}`) ? oldDetail.promise : undefined;
  await mount(state); await click('Report 11111111 · Revision 2'); await click('Report 22222222 · Revision 1'); await wait(() => text().includes('Other authorized report'), 'new selection');
  oldDetail.resolve(initial()); await sleep(40);
  check(text().includes('Other authorized report') && !text().includes(original), 'Old detail cannot overwrite new selection');
  state = mock(); const delayedBlob = deferred(); state.hook = call => call.path.includes(`/exports/${exportId}`) ? { headers: new Headers({ 'Content-Type': types.pdf }), blob: () => delayedBlob.promise } : undefined;
  await open(state); await click('Create PDF summary download'); await wait(() => state.calls.some(call => call.raw), 'slow blob started');
  const beforeBlob = downloads.length, clean = mock(); clean.list = { items: [] }; await mount(clean); delayedBlob.resolve(new Blob([original], { type: types.pdf })); await sleep(50);
  check(downloads.length === beforeBlob && !text().includes(original), 'Session change fences delayed blob and clears private content');
  check(state.calls.find(call => call.raw).signal.aborted, 'Session change aborts in-flight download');
  state = mock(); await open(state); state.list = { items: [] }; await click('Refresh reports');
  await wait(() => text().includes('No reports are available'), 'report removed from accessible list');
  check(!text().includes(original), 'List removal clears previously selected private report');
  state = mock(); await mount(state, 'same-family'); await click('Report 11111111 · Revision 2'); await wait(() => text().includes(original), 'same-family original');
  await mount(state, 'same-family', '55555555-5555-4555-8555-555555555555');
  check(!text().includes(original) && state.calls.at(-1).path.includes('55555555-5555-4555-8555-555555555555'), 'Workspace changes clear selected report with stable request');
  await click('Report 11111111 · Revision 2'); await wait(() => text().includes(original), 'workspace original');
  await mount(state, 'replacement-family', '55555555-5555-4555-8555-555555555555');
  check(!text().includes(original), 'Session-family changes clear selected report with stable request');
  state = mock(); const revisionError = deferred(); state.hook = call => call.path.includes('?revision=') ? revisionError.promise : undefined;
  await open(state); change(document.querySelector('input[type=number]'), '1'); await sleep(5); await click('View revision'); revisionError.resolve(null);
  await wait(() => text().includes('Reports could not be loaded'), 'failed historical read'); await click('Reload latest report'); await wait(() => text().includes(original), 'recover to current revision'); checked++;
  await mount(mock());
  check(document.documentElement.scrollWidth <= innerWidth, 'No viewport overflow');
  document.querySelector('#fixture-result').textContent = `PASS ${checked} private report checks`;
}
run().catch(error => { console.error(error); document.querySelector('#fixture-result').textContent = `FAIL ${error.message}`; });
