import test from 'node:test';
import assert from 'node:assert/strict';
import { createApiClient, ApiError } from './apiClient.js';
test('canonical transport, bearer and idempotency key; no mutation retries', async () => {
  let count = 0;
  const api = createApiClient({ token: 'memory-only', fetchImpl: async (url, options) => {
    count++; assert.equal(url, '/api/v1/studies'); assert.equal(options.headers.Authorization, 'Bearer memory-only'); assert.equal(options.headers['Idempotency-Key'], 'same-key'); assert.equal(options.cache, 'no-store'); assert.equal(options.credentials, 'same-origin'); assert.deepEqual(JSON.parse(options.body), { title: 'Study' });
    return new Response('{"error":{"code":"REVISION_CONFLICT","message":"Reload revision"},"request_id":"fixture-conflict"}', { status: 409 });
  } });
  await assert.rejects(api('/studies', { method: 'POST', body: { title: 'Study' }, idempotencyKey: 'same-key' }), error => error instanceof ApiError && error.status === 409 && error.code === 'REVISION_CONFLICT'); assert.equal(count, 1);
});
test('network failure is safe and does not leak implementation errors', async () => {
  const api = createApiClient({ fetchImpl: async () => { throw new Error('private transport detail'); } });
  await assert.rejects(api('/x'), error => error.status === 0 && !error.message.includes('private'));
});
test('204, JSON, malformed success and non-JSON errors', async () => {
  for (const [response, expected] of [[new Response(null, { status: 204 }), null], [new Response('{"state":"queued"}'), { state: 'queued' }]]) assert.deepEqual(await createApiClient({ fetchImpl: async () => response })('/x'), expected);
  await assert.rejects(createApiClient({ fetchImpl: async () => new Response('bad') })('/x'), error => error.code === 'INVALID_RESPONSE');
  await assert.rejects(createApiClient({ fetchImpl: async () => new Response('private error', { status: 500 }) })('/x'), error => error.message === 'Request failed (500).');
});
test('abort remains distinguishable', async () => {
  const error = new DOMException('Aborted', 'AbortError');
  await assert.rejects(createApiClient({ fetchImpl: async () => { throw error; } })('/x'), candidate => candidate === error);
});
test('canonical 422 remains distinguishable for editable form recovery', async () => {
  const envelope = { error: { code: 'VALIDATION_ERROR', message: 'Request validation failed.' }, request_id: 'fixture-422' };
  await assert.rejects(createApiClient({ fetchImpl: async () => new Response(JSON.stringify(envelope), { status: 422 }) })('/auth/register', { method: 'POST', body: { email: 'fixture@example.test', password: 'synthetic-password' } }), error => error.status === 422 && error.code === envelope.error.code && error.message === envelope.error.message);
});
