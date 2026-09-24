#!/usr/bin/env node
// Installed Chrome + Node's built-in WebSocket. No driver downloads/services.
import { spawn } from 'node:child_process';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
const base = process.env.CONTRACT_BASE_URL || 'http://127.0.0.1:8080';
if (!['127.0.0.1', 'localhost', '[::1]'].includes(new URL(base).hostname)) throw new Error('Only local fixtures allowed');
const paths = process.argv.slice(2);
if (!paths.length || paths.some(p => !/^\/tests\/[A-Za-z0-9_-]+\.html$/.test(p))) throw new Error('Supply explicit /tests/name.html fixture paths');
const profile = await mkdtemp(join(tmpdir(), 'elseview-browser-'));
const child = spawn(process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', ['--headless=new', '--disable-gpu', '--no-first-run', '--disable-background-networking', '--disable-component-update', '--disable-sync', '--no-default-browser-check', '--remote-debugging-port=0', `--user-data-dir=${profile}`, 'about:blank'], { stdio: 'ignore' });
let startupError;
child.on('error', error => { startupError = error; });
const sleep = ms => new Promise(r => setTimeout(r, ms));
let socket;
try {
  let port;
  for (let n = 0; n < 100; n++) {
    if (startupError) throw startupError;
    try { port = (await readFile(join(profile, 'DevToolsActivePort'), 'utf8')).split('\n')[0]; break; } catch { await sleep(100); }
  }
  if (!port) throw new Error('Chrome startup timed out');
  for (const path of paths) {
    const target = await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, { method: 'PUT' })).json();
    socket = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => { socket.addEventListener('open', resolve, { once: true }); socket.addEventListener('error', reject, { once: true }); });
    let id = 0;
    const pending = new Map();
    socket.addEventListener('message', ({ data }) => { const reply = JSON.parse(data); const call = pending.get(reply.id); if (call) { pending.delete(reply.id); clearTimeout(call.timer); reply.error ? call.reject(new Error(reply.error.message)) : call.resolve(reply.result); } });
    const command = (method, params = {}) => new Promise((resolve, reject) => { const key = ++id; const timer = setTimeout(() => { pending.delete(key); reject(new Error(`Chrome command timeout: ${method}`)); }, 10000); pending.set(key, { resolve, reject, timer }); socket.send(JSON.stringify({ id: key, method, params })); });
    await command('Runtime.enable');
    socket.addEventListener('message', ({ data }) => { const event = JSON.parse(data); if (event.method === 'Runtime.exceptionThrown') console.error(JSON.stringify(event.params.exceptionDetails)); });
    // Page requests cannot escape the local fixture origin. Blob/data URLs are
    // browser-generated assets; no cloud API credentials or real research data.
    await command('Fetch.enable', { patterns: [{ urlPattern: '*' }] });
    socket.addEventListener('message', ({ data }) => {
      const event = JSON.parse(data);
      if (event.method !== 'Fetch.requestPaused') return;
      const request = event.params;
      const address = new URL(request.request.url);
      const allowed = address.origin === new URL(base).origin || ['blob:', 'data:'].includes(address.protocol);
      command(allowed ? 'Fetch.continueRequest' : 'Fetch.failRequest', { requestId: request.requestId, ...(allowed ? {} : { errorReason: 'BlockedByClient' }) }).catch(() => {});
    });
    await command('Page.navigate', { url: base + path });
    let status = '';
    for (let n = 0; n < 150; n++) {
      const result = await command('Runtime.evaluate', { expression: "document.querySelector('#smoke,#result,#results,#fixture-result')?.textContent || ''", returnByValue: true });
      status = result.result.value || '';
      if (/^(PASS|FAIL)/.test(status.trim())) break;
      await sleep(100);
    }
    if (!status.trim().startsWith('PASS')) {
      const diagnostic = await command('Runtime.evaluate', { expression: 'document.body.innerText', returnByValue: true });
      console.error(diagnostic.result.value);
      throw new Error(`Fixture ${path}: ${status || 'timed out'}`);
    }
    console.log(JSON.stringify({ fixture: path, status: 'passed', detail: status, browser: 'installed headless Chrome; CDP', network: 'local origin only' }));
    socket.close(); socket = null;
    await fetch(`http://127.0.0.1:${port}/json/close/${target.id}`);
  }
} finally {
  socket?.close();
  child.kill('SIGTERM');
  await Promise.race([new Promise(resolve => child.once('exit', resolve)), sleep(2000)]);
  if (child.exitCode === null) child.kill('SIGKILL');
  await rm(profile, { recursive: true, force: true, maxRetries: 5 });
}
