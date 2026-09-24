import test from 'node:test';
import assert from 'node:assert/strict';
import { createAccountSession, accountRoute, accountError } from './accountSession.js';
const login = { access_token: 'synthetic-bearer', csrf_token: 'synthetic-csrf', expires_in: 900 };
const json = value => new Response(JSON.stringify(value));
test('expired credentials refresh once before concurrent commands, with no command replay', async () => {
  const calls = [];
  const session = createAccountSession({ ...login, expires_in: 1 }, { fetchImpl: async (url, options) => {
    calls.push({ url, options });
    if (url.endsWith('/refresh')) { assert.equal(options.headers['X-CSRF-Token'], login.csrf_token); await new Promise(resolve => setTimeout(resolve, 10)); return json(login); }
    return json({ ok: true });
  } });
  await Promise.all([session.request('/me'), session.request('/workspaces', { method: 'POST', body: { name: 'Example' } })]);
  assert.deepEqual(calls.map(call => call.url), ['/api/v1/auth/refresh', '/api/v1/me', '/api/v1/workspaces']);
});
test('401 closes session, clears credentials and never repeats a mutation', async () => {
  let calls = 0, expired = 0;
  const session = createAccountSession(login, { onExpired: () => expired++, fetchImpl: async () => { calls++; return new Response('{}', { status: 401 }); } });
  await assert.rejects(session.request('/workspaces', { method: 'POST' }));
  await assert.rejects(session.request('/me'), error => error.code === 'SESSION_CLOSED');
  assert.equal(calls, 1); assert.equal(expired, 1);
});
test('uncertain refresh closes session without dispatching queued business commands', async () => {
  let calls = 0, expired = 0;
  const session = createAccountSession({ ...login, expires_in: 1 }, { onExpired: () => expired++, fetchImpl: async () => { calls++; throw new TypeError('lost response'); } });
  const results = await Promise.allSettled([session.request('/me'), session.request('/workspaces', { method: 'POST' })]);
  assert.ok(results.every(result => result.status === 'rejected'));
  assert.equal(calls, 1); assert.equal(expired, 1);
});
test('late responses after closing cannot repopulate a different account', async () => {
  let release;
  const session = createAccountSession(login, { fetchImpl: () => new Promise(resolve => { release = resolve; }) });
  const request = session.request('/me');
  await new Promise(resolve => setTimeout(resolve, 0));
  session.close(); release(json({ id: 'old-account' }));
  await assert.rejects(request, error => error.code === 'SESSION_CLOSED');
});
test('logout uses current CSRF and clears memory even when remote revocation is uncertain', async () => {
  let calls = 0;
  const session = createAccountSession(login, { fetchImpl: async (url, options) => {
    calls++; assert.equal(url, '/api/v1/auth/logout'); assert.equal(options.headers['X-CSRF-Token'], login.csrf_token);
    throw new TypeError('lost');
  } });
  await assert.rejects(session.logout());
  await assert.rejects(session.request('/me'));
  assert.equal(calls, 1);
});
test('routes accept only known pages and resource identifiers; errors never echo payloads', () => {
  assert.deepEqual(accountRoute('#/register'), { page: 'register' });
  assert.deepEqual(accountRoute('#/login-sessions'), { page: 'login-sessions' });
  assert.deepEqual(accountRoute('#/participant/profile'), { page: 'participant-profile' });
  assert.deepEqual(accountRoute('#/participant/profile/extra'), { page: 'workspaces' });
  assert.deepEqual(accountRoute('#/participant/assessments'), { page: 'assessments' });
  assert.deepEqual(accountRoute('#/participant/history'), { page: 'participant-history' });
  assert.deepEqual(accountRoute('#/participant/history/extra'), { page: 'workspaces' });
  const workspaceId = '00000000-0000-4000-8000-000000000001', resourceId = '00000000-0000-4000-8000-000000000002';
  assert.deepEqual(accountRoute(`#/workspaces/${workspaceId}/reports`), { page: 'reports', workspaceId });
  assert.deepEqual(accountRoute(`#/workspaces/${workspaceId}/reports/extra`), { page: 'workspaces' });
  assert.deepEqual(accountRoute(`#/workspaces/${workspaceId}/assignments/${resourceId}`), { page: 'evaluation', workspaceId, assignmentId: resourceId });
  assert.deepEqual(accountRoute(`#/workspaces/${workspaceId}/schedule/${resourceId}`), { page: 'schedule', workspaceId, versionId: resourceId });
  assert.deepEqual(accountRoute('#/workspaces/00000000-0000-4000-8000-000000000001'), { page: 'workspace', workspaceId: '00000000-0000-4000-8000-000000000001', studyId: undefined });
  assert.deepEqual(accountRoute('#/workspaces/../../private'), { page: 'workspaces' });
  assert.ok(!accountError({ message: 'sensitive server detail' }).includes('sensitive'));
});
