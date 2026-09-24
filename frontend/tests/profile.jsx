import React from 'react';
import { createRoot } from 'react-dom/client';
import ParticipantProfile from '../ParticipantProfile.jsx';

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
let checks = 0;
function check(value, label) { if (!value) throw new Error(label); checks++; }
async function wait(predicate, label = 'State did not settle') { for (let i = 0; i < 150; i++) { if (predicate()) return; await sleep(15); } throw new Error(label); }
const text = () => document.body.textContent;
const button = label => [...document.querySelectorAll('button')].find(element => element.textContent === label);
const field = name => document.querySelector(`[name="${name}"]`);
async function click(label) { await wait(() => button(label) && !button(label).matches(':disabled'), `Missing enabled ${label}`); button(label).click(); await sleep(30); }
async function fill(name, value) {
  const element = field(name); if (!element) throw new Error(`Missing ${name}`);
  const prototype = element instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : element instanceof HTMLSelectElement ? HTMLSelectElement.prototype : HTMLInputElement.prototype;
  Object.getOwnPropertyDescriptor(prototype, 'value').set.call(element, value);
  element.dispatchEvent(new Event(element instanceof HTMLSelectElement ? 'change' : 'input', { bubbles: true })); await sleep(15);
}
async function agree() { if (!field('panel-consent').checked) { field('panel-consent').click(); await sleep(15); } }
const uuid = '10000000-0000-4000-8000-000000000001';
const defaults = { age: null, devices: [], languages: [], country_id: null, city_id: null, experience: null };
const profile = (attributes = {}, status = 'active') => ({ id: uuid, status, attributes: { ...defaults, ...attributes }, targeting_provenance: { consent: { receipt_key: 'PRIVATE_RECEIPT_CANARY' } } });
const documents = { '1': { version: '1', digest: 'a'.repeat(64), body: 'Synthetic public-panel consent version 1. Optional research matching using age, devices and self-reported languages.' }, '2': { version: '2', digest: 'b'.repeat(64), body: 'Synthetic panel targeting consent version 2. Optional country/city identifiers and self-reported experience may be frozen for matching. These are not professional credentials.' } };
const vocabulary = { version: '1', country_ids: ['FR', 'TN', 'US'], experience_categories: ['software', 'design', 'research', 'business', 'education', 'healthcare', 'finance', 'manufacturing', 'retail', 'hospitality'], experience_levels: ['beginner', 'intermediate', 'advanced'], public_targeting_consent_version: '2', city_country_association: 'self_reported_not_verified', experience_scope: 'self_reported_not_verified_credentials' };
let state, calls = [], receipts, generation = 0, release;
const reset = (value = null) => { state = { profile: value, mode: '', denied: '', readFailure: '', documentRevision: false }; calls = []; receipts = new Map(); release = null; };
const copy = value => structuredClone(value);
const error = (status, code = '') => Object.assign(new Error('PRIVATE SERVER DETAIL'), { status, code });
const request = async (path, options = {}) => {
  if (!['/panel/profile', '/panel/consent?version=1', '/panel/consent?version=2', '/recruiting/targeting-vocabulary'].includes(path)) throw new Error(`Unexpected path ${path}`);
  if (options.rawResponse || options.headers || options.credentials) throw new Error('Profile bypassed parsed memory-session transport');
  calls.push({ path, method: options.method || 'GET', body: copy(options.body) });
  if (state.denied && path === '/panel/profile') throw error(Number(state.denied));
  if (!options.method) {
    if (state.readFailure === path) throw error(503);
    if (path.startsWith('/panel/consent?')) { const version = path.slice(-1); return { ...documents[version], ...(state.documentRevision ? { digest: 'c'.repeat(64), body: 'Updated synthetic consent. Review again.' } : {}) }; }
    if (path === '/recruiting/targeting-vocabulary') return copy(vocabulary);
    if (state.mode === 'slow-read') return new Promise(resolve => { const snapshot = copy(state.profile); release = () => resolve(snapshot); });
    if (state.mode === 'malformed-read') return {};
    if (state.profile === null) throw error(404, 'NOT_FOUND');
    return copy(state.profile);
  }
  if (options.method !== 'PUT') throw new Error('Profile did not use PUT');
  const body = options.body;
  if (Object.keys(body).sort().join(',') !== 'attributes,decision,document_version,presented_digest,receipt_key') throw new Error('Unexpected profile command fields');
  if (!['granted', 'withdrawn'].includes(body.decision) || !body.receipt_key || body.receipt_key.length > 128) throw new Error('Unsupported status/receipt');
  if (body.presented_digest !== (state.documentRevision ? 'c'.repeat(64) : documents[body.document_version].digest)) throw error(409, 'CONSENT_DOCUMENT_MISMATCH');
  if (Object.keys(body.attributes).some(key => !Object.keys(defaults).includes(key))) throw new Error('Invented or private attribute submitted');
  if (body.attributes.age != null && !Number.isInteger(body.attributes.age)) throw new Error('Age was not a strict integer');
  if (state.mode === 'late-write') return new Promise(resolve => { release = () => resolve(profile({ age: 77, languages: ['STALE_MUTATION_CANARY'] })); });
  if (state.mode === 'validation') throw error(422);
  if (state.mode === 'conflict') throw error(409, 'CONSENT_DOCUMENT_MISMATCH');
  if (state.mode === 'rate-limit') throw error(429);
  if (state.mode === 'write-denied') throw error(403);
  const serialized = JSON.stringify(body);
  if (receipts.has(body.receipt_key)) {
    const old = receipts.get(body.receipt_key);
    if (old !== serialized) throw new Error('Same receipt was replayed with different bytes');
    return copy(state.profile);
  }
  if (state.mode === 'lost-uncommitted') { state.mode = ''; throw error(undefined); }
  state.profile = body.decision === 'withdrawn' ? { id: uuid, status: 'withdrawn', attributes: {}, targeting_provenance: null } : profile(copy(body.attributes));
  receipts.set(body.receipt_key, serialized);
  if (state.mode === 'lost-committed') { state.mode = ''; throw error(503); }
  if (state.mode === 'malformed-success') { state.mode = ''; return { status: 'active' }; }
  return copy(state.profile);
};
const puts = () => calls.filter(call => call.method === 'PUT');
const root = createRoot(document.querySelector('#root'));
async function mount({ loading = false, denied = false } = {}) {
  root.render(<ParticipantProfile request={request} sessionKey={String(++generation)} />);
  await sleep(40);
  if (!loading) await wait(() => denied ? text().includes('Access to your private profile ended') : button('Reload profile and documents') && !button('Reload profile and documents').disabled);
}
try {
  reset(); await mount();
  check(text().includes('No public-panel profile exists yet') && button('Join public panel'), '404 first-use shape was not handled');
  check(button('Pause unavailable').disabled && text().includes('Interests are not supported'), 'Unsupported controls were invented');
  await click('Join public panel'); check(puts().length === 0, 'Missing consent reached the API');
  await fill('age', '17'); await agree(); await click('Join public panel'); check(puts().length === 0, 'Underage value reached the API');
  await fill('age', '28'); await fill('languages', Array.from({ length: 11 }, (_, i) => `lang${i}`).join('\n')); await click('Join public panel'); check(puts().length === 0 && text().includes('at most 10 language identifiers'), 'Language bound not enforced');
  await fill('languages', 'fr\narabizi'); field('device-mobile').click(); await sleep(15); await click('Join public panel');
  check(state.profile.attributes.age === 28 && state.profile.attributes.languages.join(',') === 'fr,arabizi' && state.profile.attributes.devices[0] === 'mobile', 'Basic profile values did not survive strict serialization');
  check(puts()[0].body.document_version === '1' && puts()[0].body.presented_digest === documents['1'].digest, 'Basic grant did not use exact v1 document');
  check(!text().includes('PRIVATE_RECEIPT_CANARY') && text().includes('self-reported and unverified'), 'Provenance leaked or credibility was implied');
  await agree(); await fill('country', 'TN'); check(!field('panel-consent').checked && text().includes('requires targeting consent version 2'), 'Adding targeting did not reset consent');
  await fill('city', 'geonames:12345678901'); await agree(); await click('Save profile and consent'); check(puts().length === 1 && field('city').getAttribute('aria-invalid') === 'true', 'City size bound missing');
  await fill('city', 'geonames:2464461'); await fill('country', ''); await agree(); await click('Save profile and consent'); check(puts().length === 1 && text().includes('A city requires a country'), 'City without country accepted');
  await fill('country', 'TN'); await fill('experience-software', 'advanced'); await agree(); await click('Save profile and consent');
  check(state.profile.attributes.experience.version === '1' && state.profile.attributes.experience.categories.software === 'advanced', 'Versioned experience contract drift');
  check(puts().at(-1).body.document_version === '2' && puts().at(-1).body.presented_digest === documents['2'].digest, 'Targeting grant not bound to exact v2 consent');
  check([...field('country').options].map(option => option.value).join(',') === ',FR,TN,US', 'Country dataset invented rather than supplied by API');
  await fill('age', '31'); state.mode = 'validation'; await agree(); await click('Save profile and consent'); check(field('age').value === '31' && !text().includes('PRIVATE SERVER DETAIL'), 'Validation erased input or exposed server error');
  state.mode = 'rate-limit'; await click('Save profile and consent'); check(text().includes('Too many requests') && !button('Check server profile'), 'Definite rate limit treated as uncertain replay');
  state.mode = 'conflict'; await click('Save profile and consent'); check(button('Save profile and consent').matches(':disabled') && !field('panel-consent').checked, 'Consent conflict did not lock writes');
  state.mode = ''; state.documentRevision = true; await click('Reload profile and documents'); check(field('age').value === '31' && !field('panel-consent').checked && text().includes('Updated synthetic consent'), 'Document refresh lost draft or kept agreement');
  await agree(); await click('Save profile and consent'); check(puts().at(-1).body.presented_digest === 'c'.repeat(64), 'Changed digest was not used');

  reset(profile({ age: 20 })); await mount(); await fill('age', '21'); await agree(); state.mode = 'lost-committed'; await click('Save profile and consent');
  check(puts().length === 1 && !button('Retry original request') && field('age').matches(':disabled'), 'Unknown result was replayed or left editable');
  await sleep(100); check(puts().length === 1, 'Unknown write auto-replayed');
  state.readFailure = '/panel/profile'; await click('Check server profile'); check(!button('Retry original request') && text().includes('server response was not confirmed'), 'Failed reconciliation unlocked retry');
  state.readFailure = ''; await click('Check server profile'); check(puts().length === 1 && text().includes('server profile now matches') && !button('Check server profile'), 'Committed outcome was not reconciled read-only');

  reset(profile({ age: 20 })); await mount(); await fill('age', '22'); await agree(); state.mode = 'lost-uncommitted'; await click('Save profile and consent');
  await click('Check server profile'); check(puts().length === 1 && button('Retry original request'), 'Uncommitted outcome did not require explicit retry after GET');
  await click('Retry original request'); check(puts().length === 2 && JSON.stringify(puts()[0].body) === JSON.stringify(puts()[1].body) && state.profile.attributes.age === 22, 'Explicit retry changed original body/receipt');

  reset(profile({ age: 20 })); await mount(); await fill('age', '23'); await agree(); state.mode = 'malformed-success'; await click('Save profile and consent');
  check(button('Check server profile') && !button('Retry original request'), 'Malformed success was treated as confirmed');
  await click('Check server profile'); check(puts().length === 1 && field('age').value === '23', 'Malformed success reconciliation replayed write');

  reset(profile({ country_id: 'TN', city_id: 'geonames:2464461' })); await mount(); await click('Review panel withdrawal');
  await click('Confirm panel withdrawal'); check(puts().length === 0, 'Destructive withdrawal skipped confirmation');
  await click('Keep panel participation'); check(!button('Confirm panel withdrawal') && puts().length === 0, 'Safe cancellation changed participation');
  await click('Review panel withdrawal'); field('withdraw-consent').click(); await sleep(15); state.mode = 'lost-committed'; await click('Confirm panel withdrawal');
  check(button('Check server profile') && !button('Retry original request'), 'Unknown withdrawal did not require reconciliation');
  await click('Check server profile');
  check(puts().length === 1 && puts()[0].body.document_version === '2' && JSON.stringify(puts()[0].body.attributes) === '{}', 'Withdrawal did not use exact stored-source consent and empty attributes');
  check(state.profile.status === 'withdrawn' && field('country').value === '' && field('city').value === '' && button('Rejoin public panel') && !field('panel-consent').checked, 'Withdrawn empty shape leaked prior attributes or consent');
  await agree(); await click('Rejoin public panel'); check(state.profile.status === 'active' && state.profile.attributes.country_id === null, 'Rejoin invented old attributes');
  reset(profile({ age: 44 }, 'paused')); await mount(); await agree(); await click('Resume panel participation'); check(puts()[0].body.decision === 'granted' && state.profile.status === 'active', 'Paused profile resume invented an API operation');

  reset(profile({ age: 65, languages: ['PRIVATE_ACCESS_CANARY'] })); await mount(); state.denied = '403'; await click('Reload profile and documents');
  check(!field('age') && !text().includes('PRIVATE_ACCESS_CANARY') && !text().includes('PRIVATE_RECEIPT_CANARY') && text().includes('Access to your private profile ended'), 'Read access loss did not clear private state');
  reset(); state.denied = '401'; await mount({ denied: true }); check(!button('Join public panel') && !field('age'), 'Unauthorized initial read exposed editable profile');
  reset(profile({ age: 64 })); await mount(); await agree(); state.mode = 'write-denied'; await click('Save profile and consent'); check(!field('age') && text().includes('Access to your private profile ended'), 'Write access loss retained private form');

  reset(profile({ age: 66, languages: ['STALE_READ_CANARY'] })); state.mode = 'slow-read'; await mount({ loading: true }); check(text().includes('Loading or saving'), 'Slow initial loading state absent');
  const oldRead = release; state.mode = ''; state.profile = profile({ age: 29 }); await mount(); oldRead(); await sleep(40); check(field('age').value === '29' && !text().includes('STALE_READ_CANARY'), 'Old session GET repopulated new session');
  await agree(); state.mode = 'late-write'; await click('Save profile and consent'); const oldWrite = release; state.mode = ''; state.profile = profile({ age: 30 }); await mount(); oldWrite(); await sleep(40); check(field('age').value === '30' && !text().includes('STALE_MUTATION_CANARY'), 'Old mutation repopulated new session');

  reset(profile({ age: 33 })); state.readFailure = '/recruiting/targeting-vocabulary'; await mount(); check(text().includes('Participation: active') && field('age').matches(':disabled'), 'Partial vocabulary failure invented writable options');
  state.readFailure = ''; await click('Reload profile and documents'); check(!field('age').matches(':disabled'), 'Vocabulary retry failed to recover');
  await fill('age', '34'); state.readFailure = '/panel/consent?version=1'; await click('Reload profile and documents'); check(field('age').value === '34' && button('Save profile and consent').matches(':disabled'), 'Missing consent lost draft or allowed save');
  state.readFailure = ''; await click('Reload profile and documents');
  state.readFailure = '/panel/profile'; await click('Reload profile and documents'); check(field('age').value === '34' && field('age').matches(':disabled'), 'Transient profile read failure discarded the draft or left writes unlocked');
  state.readFailure = ''; await click('Reload profile and documents'); check(field('age').value === '34', 'Profile read retry overwrote unsaved input');
  state.profile = { id: uuid, status: 'withdrawn', attributes: {}, targeting_provenance: null }; await click('Reload profile and documents'); check(field('age').value === '' && !field('panel-consent').checked, 'External withdrawal retained old attributes or consent');
  reset(); state.mode = 'malformed-read'; await mount(); check(!field('age') && text().includes('server response was not confirmed'), 'Malformed profile was treated as empty creation');

  reset(profile({ age: 28, devices: ['mobile'], languages: ['fr'], country_id: 'TN', city_id: 'geonames:2464461', experience: { version: '1', categories: { software: 'intermediate' } } })); await mount(); await agree();
  check(!document.querySelector('main main') && document.querySelector('.participant-profile').tagName === 'SECTION', 'Component introduced nested main');
  check([...document.querySelectorAll('.participant-profile input, .participant-profile select, .participant-profile textarea')].every(element => element.labels.length), 'Native field label missing');
  check(document.documentElement.scrollWidth <= innerWidth, 'Profile overflows mobile viewport');
  check(!text().includes('PRIVATE_RECEIPT_CANARY') && !JSON.stringify(puts()).includes('targeting_provenance'), 'Private receipt provenance leaked');
  document.querySelector('#fixture-result').textContent = `PASS: ${checks} profile checks; first-use/withdrawn shapes, v1/v2 consent, strict targeting, unsupported pause/interests disclosure, source withdrawal confirmation, unknown-outcome reconciliation without automatic replay, exact explicit retry, errors, access/session fencing, labels and responsive layout. Synthetic only.`;
} catch (failure) { document.querySelector('#fixture-result').textContent = `FAIL: ${failure.message}`; console.error(failure); }
