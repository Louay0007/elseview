#!/usr/bin/env node
// Installed Chrome + Node's built-in WebSocket. No driver downloads/services.
import { spawn } from 'node:child_process';
import { mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
const base = process.env.CONTRACT_BASE_URL || 'http://127.0.0.1:8080';
if (!['127.0.0.1', 'localhost', '[::1]'].includes(new URL(base).hostname)) throw new Error('Only local fixtures allowed');
const viewport = process.env.CONTRACT_VIEWPORT;
if (viewport && !/^(1440x900|390x844)$/.test(viewport)) throw new Error('Use a supported desktop/mobile viewport');
const screenshots = process.env.CONTRACT_SCREENSHOT_DIR;
const keyboardSubmit = process.env.CONTRACT_KEYBOARD_SUBMIT;
const keyboardResult = process.env.CONTRACT_KEYBOARD_RESULT;
if (keyboardSubmit && !keyboardResult) throw new Error('Keyboard submit requires an expected result');
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
    if (viewport) {
      const [width, height] = viewport.split('x').map(Number);
      await command('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: width < 600 });
    }
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
    async function screenshot(suffix) {
      if (!screenshots) return;
      await mkdir(screenshots, { recursive: true });
      const image = await command('Page.captureScreenshot', { format: 'png' });
      await writeFile(join(screenshots, `${path.split('/').at(-1).replace('.html', '')}-${viewport || 'default'}-${suffix}.png`), Buffer.from(image.data, 'base64'));
    }
    await screenshot('initial');
    if (keyboardSubmit) {
      const found = await command('Runtime.evaluate', { expression: `(() => { const button = [...document.querySelectorAll('button')].find(element => element.textContent === ${JSON.stringify(keyboardSubmit)}); if (!button || button.disabled) return false; button.focus(); return document.activeElement === button; })()`, returnByValue: true });
      if (!found.result.value) throw new Error('Keyboard target is missing or cannot receive focus');
      await command('Page.bringToFront');
      await command('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Enter', code: 'Enter', text: '\r', unmodifiedText: '\r', windowsVirtualKeyCode: 13 });
      await command('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 });
      let complete = false;
      for (let n = 0; n < 100; n++) {
        complete = (await command('Runtime.evaluate', { expression: `document.body.innerText.includes(${JSON.stringify(keyboardResult)})`, returnByValue: true })).result.value;
        if (complete) break;
        await sleep(50);
      }
      if (!complete) throw new Error('Native Enter did not reach the expected state');
      const ax = await command('Accessibility.getFullAXTree');
      if (!ax.nodes.some(node => !node.ignored && node.role?.value === 'main')) throw new Error('Accessible main landmark missing');
      await screenshot('keyboard-result');
    }
    const layout = (await command('Runtime.evaluate', { expression: `(() => {
      const scope = document.querySelector('.account-app');
      if (!scope) return null;
      const luminance = value => value.match(/[0-9.]+/g).slice(0,3).map(Number).map(v => { v /= 255; return v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4; }).reduce((sum, v, i) => sum + v * [.2126,.7152,.0722][i], 0);
      const ratio = element => { const style = getComputedStyle(element); const a = luminance(style.color), b = luminance(style.backgroundColor); return (Math.max(a,b)+.05)/(Math.min(a,b)+.05); };
      return { overflow: document.documentElement.scrollWidth > innerWidth, textContrast: ratio(scope), buttonContrast: [...scope.querySelectorAll('button')].filter(element => !element.disabled).map(ratio), targets: [...scope.querySelectorAll('button,input,select,textarea')].filter(element => !element.disabled).map(element => { const target = element.matches('input[type=radio],input[type=checkbox]') ? [...element.labels].find(label => label.contains(element)) || element : element; return target.getBoundingClientRect().height; }) };
    })()`, returnByValue: true })).result.value;
    if (layout && (layout.overflow || layout.textContrast < 4.5 || layout.buttonContrast.some(value => value < 4.5) || layout.targets.some(value => value < 44))) throw new Error(`Account layout, contrast or target check failed: ${JSON.stringify(layout)}`);
    console.log(JSON.stringify({ fixture: path, status: 'passed', detail: status, viewport, keyboard: keyboardSubmit ? 'native Enter passed' : 'not requested', layout, browser: 'installed headless Chrome; CDP', network: 'local origin only' }));
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
