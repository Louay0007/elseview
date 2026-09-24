// Synthetic HTTP contracts, not persisted browser/API/database acceptance.
import React from 'react';
import { createRoot } from 'react-dom/client';
import AccountApp from '../AccountApp.jsx';
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const assert = (condition, message) => { if (!condition) throw new Error(message); };
async function wait(predicate, message) { for (let i = 0; i < 150; i++) { if (predicate()) return; await sleep(20); } throw new Error(message); }
const button = label => [...document.querySelectorAll('button')].find(element => element.textContent === label);
async function click(label) { await wait(() => button(label) && !button(label).disabled, `Missing ${label}`); button(label).click(); await sleep(30); }
async function route(path) { location.hash = path; await sleep(40); }
const input = (name, value) => { const element = document.querySelector(`[name="${name}"]`); assert(element, `Missing field ${name}`); element.value = value; };
const submit = () => document.querySelector('.account-form form').requestSubmit();
const json = (body, status = 200) => new Response(JSON.stringify(body), { status });
const wid = '00000000-0000-4000-8000-000000000001', sid = '00000000-0000-4000-8000-000000000002';
const vid = '00000000-0000-4000-8000-000000000003', aid = '00000000-0000-4000-8000-000000000004';
let scenario = 'normal', loginCount = 0, createCount = 0, releaseWorkspaces;
let loginSessions = ['fixture-family', 'other-family'];
const calls = [];
const fetchImpl = async (url, options) => {
  calls.push({ url, options });
  const body = options.body && JSON.parse(options.body);
  assert(options.cache === 'no-store' && options.credentials === 'same-origin', 'Private request transport changed');
  if (url === '/api/v1/auth/login') {
    loginCount++;
    if (scenario === 'invalid-login') return json({ error: { code: 'INVALID_CREDENTIALS', message: 'private fixture message' } }, 401);
    return json({ access_token: 'synthetic-session', csrf_token: 'synthetic-csrf', expires_in: 900, family_id: 'fixture-family', token_type: 'bearer' });
  }
  if (['/api/v1/auth/register', '/api/v1/auth/password-reset/request', '/api/v1/auth/verification/request'].includes(url)) return json({ message: 'If the request is eligible, instructions will be delivered.' }, 202);
  if (['/api/v1/auth/verify-email', '/api/v1/auth/password-reset/confirm'].includes(url)) {
    assert(body.token.length >= 20, 'Missing one-time code'); return json({ status: 'ok' });
  }
  if (url === '/api/v1/auth/logout') { assert(options.headers['X-CSRF-Token'] === 'synthetic-csrf', 'Logout omitted CSRF'); return new Response(null, { status: 204 }); }
  assert(options.headers.Authorization, 'Authenticated request omitted bearer');
  if (url === '/api/v1/me') return json({ id: 'fixture-account', email: 'researcher@example.test', display_name: 'Researcher' });
  if (url === '/api/v1/me/login-sessions') return json({ items: loginSessions.map(id => ({ id, expires_at: '2030-01-01T00:00:00Z' })) });
  if (url.startsWith('/api/v1/me/login-sessions/') && options.method === 'DELETE') { loginSessions = loginSessions.filter(id => id !== url.split('/').at(-1)); return new Response(null, { status: 204 }); }
  if (scenario === 'denied-review' && url.endsWith(`/assignments/${aid}`)) return json({ error: { code: 'FORBIDDEN' } }, 403);
  if (url === '/api/v1/workspaces' && options.method === 'POST') {
    createCount++;
    if (scenario === 'uncertain-create') throw new TypeError('lost response');
    return json({ id: wid, name: body.name }, 201);
  }
  if (url.startsWith('/api/v1/workspaces?')) {
    if (scenario === 'delayed-list') return new Promise(resolve => { releaseWorkspaces = () => resolve(json({ items: [] })); });
    if (scenario === 'denied-list') return json({ error: { code: 'FORBIDDEN' } }, 403);
    if (scenario === 'empty' || scenario === 'uncertain-create') return json({ items: [] });
    return json({ items: [{ id: wid, name: 'Recherche تونس · Workspace' }] });
  }
  if (url === `/api/v1/workspaces/${wid}`) return json({ id: wid, name: 'Recherche تونس · Workspace' });
  if (url.startsWith(`/api/v1/workspaces/${wid}/analytics/reports?`)) return json({ items: [], has_more: false });
  if (url.startsWith('/api/v1/participant/history?')) return json({ items: [], next_offset: null });
  if (url.startsWith(`/api/v1/workspaces/${wid}/studies?`)) return json({ items: [{ id: sid, title: 'Bilingual checkout study', status: 'ready', ai_policy: 'human_only' }] });
  if (url === `/api/v1/workspaces/${wid}/studies/${sid}`) return json({ id: sid, title: 'Bilingual checkout study', status: 'ready', ai_policy: 'human_only' });
  if (url.startsWith(`/api/v1/workspaces/${wid}/studies/${sid}/versions?`)) return json({ items: [{ id: vid, number: 1, revision: 2, state: 'published', locales: ['fr', 'ar'] }] });
  if (url.startsWith(`/api/v1/workspaces/${wid}/evaluation/assignments?`)) return json({ items: [{ id: aid, task: 'classification', kind: 'independent', submitted: false }], has_more: false });
  if (url === `/api/v1/workspaces/${wid}/evaluation/assignments/${aid}`) return json({ id: aid, source: { language: 'fr', text: 'Synthetic research evidence' }, schema: { task: 'classification', labels: [{ id: 'yes', label: 'Relevant' }], instructions: 'Review this evidence.', instructions_version: '1', language_basis: 'Human review', min_annotations: 1, max_annotations: 1 }, rights: {}, outcome: { submitted: true } });
  if (url.startsWith('/api/v1/participant/longitudinal/')) return json([]);
  if (url === '/api/v1/panel/profile' || url.startsWith('/api/v1/panel/consent?') || url === '/api/v1/recruiting/targeting-vocabulary') return json({ error: { code: 'SERVICE_UNAVAILABLE' } }, 503);
  if (url.startsWith('/api/v1/panel/language-')) return json({ error: { code: 'SERVICE_UNAVAILABLE' } }, 503);
  throw new Error('Unexpected fixture endpoint');
};
const root = createRoot(document.querySelector('#root'));
async function signIn() {
  await route('/sign-in'); input('email', 'researcher@example.test'); input('password', 'synthetic-password'); submit();
  await wait(() => button('Sign out'), 'Sign-in did not finish');
}
try {
  location.hash = '/register'; root.render(<AccountApp fetchImpl={fetchImpl} />);
  await wait(() => document.querySelector('[name="display_name"]'), 'Registration did not render');
  input('email', 'not-an-email'); input('password', 'synthetic-password');
  assert(document.querySelector('[name="password"]').minLength === 12, 'Registration password minimum changed');
  const before = calls.length; submit(); await sleep(30); assert(calls.length === before, 'Invalid email reached API');
  input('email', 'researcher@example.test'); submit(); await wait(() => document.body.textContent.includes('If this request is eligible'), 'Generic instructions missing');
  assert(document.querySelector('[name="password"]').value === '', 'Password retained after registration');
  await route('/verify'); input('token', 'synthetic-verification-code'); submit(); await wait(() => document.body.textContent.includes('Your email is verified'), 'Verification success missing');
  await route('/recover'); input('email', 'researcher@example.test'); await click('Send verification instructions instead');
  assert(calls.at(-1).url.endsWith('/verification/request'), 'Verification resend used recovery route');
  input('email', 'researcher@example.test'); submit(); await wait(() => calls.at(-1).url.endsWith('/password-reset/request'), 'Recovery request missing');
  await route('/reset'); input('token', 'synthetic-reset-code-long'); input('password', 'synthetic-new-password'); submit(); await wait(() => document.body.textContent.includes('Your password was changed'), 'Reset success missing');
  await route('/sign-in'); scenario = 'invalid-login'; input('email', 'researcher@example.test'); input('password', 'synthetic-password'); submit();
  await wait(() => document.querySelector('#account-error').textContent, 'Login error missing');
  assert(document.querySelector('[name="password"]').value === 'synthetic-password', 'Failed sign-in cleared input');
  assert(!document.body.textContent.includes('private fixture message'), 'Raw server error leaked');
  scenario = 'normal'; submit(); submit(); await wait(() => button('Sign out'), 'Login failed');
  assert(loginCount === 2, 'Double submit created another login');
  await wait(() => document.querySelector(`a[href="#/workspaces/${wid}"]`), 'Workspace navigation missing');
  document.querySelector(`a[href="#/workspaces/${wid}"]`).click(); await wait(() => document.body.textContent.includes('Bilingual checkout study'), 'Studies missing');
  document.querySelector(`a[href="#/workspaces/${wid}/reports"]`).click();
  await wait(() => calls.some(call => call.url.startsWith(`/api/v1/workspaces/${wid}/analytics/reports?`)), 'Reports did not use the authenticated session adapter');
  assert(document.querySelectorAll('main').length === 1, 'Reports nested main landmarks');
  await route(`/workspaces/${wid}`); await wait(() => document.querySelector(`a[href="#/workspaces/${wid}/studies/${sid}"]`), 'Workspace did not return');
  document.querySelector(`a[href="#/workspaces/${wid}/studies/${sid}"]`).click(); await wait(() => document.body.textContent.includes('Version 1'), 'Version history missing');
  assert(document.activeElement.id === 'account-main', 'Route navigation lost focus');
  document.querySelector(`a[href="#/workspaces/${wid}/schedule/${vid}"]`).click();
  await wait(() => document.body.textContent.includes('Interviews and diary'), 'Authorized schedule navigation missing');
  assert(document.querySelectorAll('main').length === 1, 'Schedule nested main landmarks');
  await route(`/workspaces/${wid}/assignments`); await wait(() => document.querySelector(`a[href="#/workspaces/${wid}/assignments/${aid}"]`), 'Assignment navigation missing');
  assert(button('Next page').disabled, 'Final assignment page still allows forward pagination');
  document.querySelector(`a[href="#/workspaces/${wid}/assignments/${aid}"]`).click();
  await wait(() => document.body.textContent.includes('already been submitted'), 'Authenticated evaluation request adapter failed');
  assert(document.querySelectorAll('main').length === 1, 'Evaluation nested main landmarks');
  assert(!document.querySelector('input[name="token"]'), 'Runner still asks for manual credentials');
  scenario = 'denied-review'; await click('Reload assignment state');
  await wait(() => document.body.textContent.includes('Assignment unavailable'), 'Review denial not shown');
  assert(!document.body.textContent.includes('already been submitted'), 'Denied assignment retained private state');
  scenario = 'normal'; await route('/workspaces');
  await wait(() => document.querySelector('a[href="#/participant/profile"]'), 'Profile navigation missing');
  document.querySelector('a[href="#/participant/profile"]').click();
  await wait(() => calls.some(call => call.url === '/api/v1/panel/profile'), 'Profile did not use the authenticated session adapter');
  assert([...document.querySelectorAll('h2')].some(heading => heading.textContent.toLowerCase().includes('public-panel profile')), 'Profile heading missing');
  assert(document.querySelectorAll('main').length === 1, 'Profile nested main landmarks');
  assert(document.querySelector('a[href="#/participant/profile"]').getAttribute('aria-current') === 'page', 'Profile navigation lost current-page state');
  await wait(() => document.querySelector('a[href="#/participant/assessments"]'), 'Assessment navigation missing');
  document.querySelector('a[href="#/participant/assessments"]').click();
  await wait(() => calls.some(call => call.url.startsWith('/api/v1/panel/language-')), 'Assessment did not use the authenticated session adapter');
  assert(document.querySelectorAll('main').length === 1, 'Assessment nested main landmarks');
  document.querySelector('a[href="#/participant/history"]').click();
  await wait(() => document.body.textContent.includes('No participation records yet'), 'Authenticated history empty state missing');
  assert(calls.some(call => call.url.startsWith('/api/v1/participant/history?')), 'History bypassed the authenticated request adapter');
  assert(document.querySelectorAll('main').length === 1, 'History nested main landmarks');
  await route('/login-sessions');
  await wait(() => document.querySelectorAll('[name="session"]').length === 2, 'Login-session list missing');
  assert(button('Confirm end selected session').disabled, 'Session deletion needs no selection');
  document.querySelector('[name="session"][value="other-family"]').click(); await click('Confirm end selected session');
  await wait(() => document.querySelectorAll('[name="session"]').length === 1, 'Other session was not removed');
  document.querySelector('[name="session"][value="fixture-family"]').click(); await click('Confirm end selected session');
  await wait(() => document.body.textContent.includes('This login session was ended'), 'Revoking current session did not sign out');
  assert(!document.querySelector('[name="session"]'), 'Session data retained after revocation');
  await signIn();
  await route('/workspaces'); await wait(() => button('Refresh workspaces') && !button('Refresh workspaces').disabled, 'Workspace list busy');
  scenario = 'denied-list'; await click('Refresh workspaces'); await wait(() => document.body.textContent.includes('This action is not available'), 'Permission failure missing');
  assert(!document.body.textContent.includes('Recherche تونس'), 'Revoked workspace remained visible');
  scenario = 'empty'; await click('Reload server record'); await wait(() => document.body.textContent.includes('No workspaces yet'), 'First-use empty state missing');
  scenario = 'uncertain-create'; input('name', 'Unconfirmed workspace'); document.querySelector('[aria-label="Create workspace"] form').requestSubmit();
  await wait(() => document.body.textContent.includes('may have been created'), 'Uncertain creation not explained');
  assert(button('Create workspace').disabled && createCount === 1, 'Uncertain command can replay');
  await click('Sign out'); await wait(() => document.querySelector('[name="email"]'), 'Logout did not clear account');
  assert(!document.body.textContent.includes('Unconfirmed workspace'), 'Private workspace remained after logout');
  scenario = 'delayed-list'; await signIn(); await wait(() => releaseWorkspaces, 'Delayed list never started');
  assert(document.body.textContent.includes('Loading the server record'), 'Initial loading state missing');
  await click('Sign out'); releaseWorkspaces(); await sleep(50);
  assert(!document.querySelector('[aria-label="Your workspaces"]'), 'Late private data repopulated signed-out page');
  scenario = 'normal';
  input('email', 'researcher@example.test'); input('password', 'synthetic-password');
  assert(!location.href.includes('synthetic-') && !document.body.innerText.includes('synthetic-session'), 'Credential leaked into page or URL');
  assert(!Object.values(localStorage).some(value => value.includes('synthetic-')) && !Object.values(sessionStorage).some(value => value.includes('synthetic-')), 'Credential persisted in browser storage');
  for (const field of document.querySelectorAll('input')) assert(field.labels.length > 0, 'Input missing native label');
  assert(document.querySelectorAll('main').length === 1, 'Incorrect main landmark count');
  assert(document.documentElement.scrollWidth <= innerWidth, 'Horizontal viewport overflow');
  document.querySelector('#fixture-result').textContent = 'PASS account registration, verification, recovery, reset, login, workspace/study/reviewer/schedule navigation, session revocation, denial, empty/loading states, uncertain mutation, sign-out and stale-response isolation. Mock HTTP only.';
} catch (error) { document.querySelector('#fixture-result').textContent = `FAIL ${error.message}`; console.error(error); }
