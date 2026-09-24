import assert from 'node:assert/strict';
import test from 'node:test';
import config from './vite.config.js';

test('development proxy forwards API routes without swallowing API-named modules', () => {
  const keys = Object.keys(config.server.proxy);
  assert.deepEqual(keys, ['/api/']);
  const matches = path => keys.some(prefix => path.startsWith(prefix));
  assert.equal(matches('/api/v1/health/ready'), true);
  assert.equal(matches('/apiClient.js'), false);
  assert.equal(matches('/assets/logo.svg'), false);
  assert.equal(config.server.proxy['/api/'].changeOrigin, false);
});