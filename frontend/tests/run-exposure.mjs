// Installed Chrome, local mocked fixtures only. No database or driver download.
import { spawn } from 'node:child_process';
import { mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import { resolve, join } from 'node:path';
const base = process.env.CONTRACT_BASE_URL || 'http://127.0.0.1:8080';
if (!['127.0.0.1', 'localhost', '[::1]'].includes(new URL(base).hostname)) throw new Error('Only local fixtures allowed');
const profile = resolve(`.c06-browser-${process.pid}`);
await mkdir(profile);
const browser = spawn(process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', ['--headless=new', '--disable-gpu', '--no-first-run', '--disable-background-networking', '--disable-component-update', '--disable-sync', '--no-default-browser-check', '--remote-debugging-port=0', `--user-data-dir=${profile}`, 'about:blank'], { stdio: 'ignore' });
const sleep = ms => new Promise(r => setTimeout(r, ms));
let socket, failure;
browser.on('error', e => { failure = e; });
try {
  let port;
  for (let i = 0; i < 100; i++) {
    if (failure) throw failure;
    try { port = (await readFile(join(profile, 'DevToolsActivePort'), 'utf8')).split('\n')[0]; break; } catch { await sleep(100); }
  }
  if (!port) throw new Error('Chrome did not start');
  for (const [name, width, height] of [['desktop', 1440, 900], ['mobile', 390, 844]]) {
    const target = await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, { method: 'PUT' })).json();
    socket = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => { socket.addEventListener('open', resolve, { once: true }); socket.addEventListener('error', reject, { once: true }); });
    const pending = new Map(); let id = 0;
    const command = (method, params = {}) => new Promise((resolve, reject) => {
      const key = ++id;
      const timer = setTimeout(() => { pending.delete(key); reject(new Error(`CDP timeout: ${method}`)); }, 10000);
      pending.set(key, { resolve, reject, timer }); socket.send(JSON.stringify({ id: key, method, params }));
    });
    socket.addEventListener('message', ({ data }) => {
      const event = JSON.parse(data), call = pending.get(event.id);
      if (call) { pending.delete(event.id); clearTimeout(call.timer); event.error ? call.reject(new Error(event.error.message)) : call.resolve(event.result); }
      if (event.method === 'Fetch.requestPaused') {
        const url = new URL(event.params.request.url);
        const allowed = url.origin === new URL(base).origin || ['blob:', 'data:'].includes(url.protocol);
        command(allowed ? 'Fetch.continueRequest' : 'Fetch.failRequest', { requestId: event.params.requestId, ...(allowed ? {} : { errorReason: 'BlockedByClient' }) }).catch(() => {});
      }
    });
    await command('Fetch.enable', { patterns: [{ urlPattern: '*' }] });
    await command('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: name === 'mobile' });
    await command('Page.navigate', { url: base + '/tests/exposure.html' });
    let status;
    for (let i = 0; i < 300; i++) {
      status = (await command('Runtime.evaluate', { expression: "document.querySelector('#fixture-result')?.textContent || ''", returnByValue: true })).result.value;
      if (/^(PASS|FAIL)/.test(status || '')) break;
      await sleep(100);
    }
    if (!status?.startsWith('PASS')) {
      console.error((await command('Runtime.evaluate', { expression: 'document.body.innerText', returnByValue: true })).result.value);
      throw new Error(`${name}: ${status || 'fixture timed out'}`);
    }
    // Browser-native keyboard activation, rather than synthetic JS KeyboardEvents.
    await command('Runtime.evaluate', { expression: "[...document.querySelectorAll('button')].find(b => b.textContent === 'Prepare image').focus()" });
    await command('Page.bringToFront');
    await command('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Enter', code: 'Enter', text: '\r', unmodifiedText: '\r', windowsVirtualKeyCode: 13 });
    await command('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 });
    await sleep(250);
    const keyboardReady = (await command('Runtime.evaluate', { expression: "!![...document.querySelectorAll('button')].find(b => b.textContent === 'Show image for five seconds')", returnByValue: true })).result.value;
    if (!keyboardReady) throw new Error('Native Enter did not prepare the stimulus');
    const ax = await command('Accessibility.getFullAXTree');
    if (ax.nodes.some(n => !n.ignored && n.role?.value === 'image' && n.name?.value === 'Timed study stimulus')) throw new Error('Concealed stimulus is exposed to assistive technology');
    if (!ax.nodes.some(n => !n.ignored && n.role?.value === 'button' && n.name?.value === 'Show image for five seconds')) throw new Error('Accessible start control missing');
    const contrast = (await command('Runtime.evaluate', { expression: `(() => {
      const luminance = rgb => rgb.match(/[0-9.]+/g).slice(0,3).map(Number).map(v => { v /= 255; return v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4; }).reduce((sum, v, i) => sum + v * [.2126,.7152,.0722][i], 0);
      const contrast = element => { const s = getComputedStyle(element); const a = luminance(s.color), b = luminance(s.backgroundColor); return (Math.max(a,b) + .05) / (Math.min(a,b) + .05); };
      return [contrast(document.querySelector('main')), contrast([...document.querySelectorAll('button')].find(b => b.textContent === 'Show image for five seconds'))];
    })()`, returnByValue: true })).result.value;
    if (contrast.some(value => value < 4.5)) throw new Error('Participant text/control contrast below AA');
    if (process.argv.includes('--screenshots')) {
      const png = await command('Page.captureScreenshot', { format: 'png' });
      await writeFile(resolve(`.c06-${name}.png`), Buffer.from(png.data, 'base64'));
    }
    console.log(`${name} ${width}x${height}: ${status} Native Enter passed.`);
    socket.close(); socket = null;
    await fetch(`http://127.0.0.1:${port}/json/close/${target.id}`);
  }
} finally {
  socket?.close(); browser.kill('SIGTERM');
  await Promise.race([new Promise(resolve => browser.once('exit', resolve)), sleep(2000)]);
  if (browser.exitCode === null) { browser.kill('SIGKILL'); await sleep(300); }
  await rm(profile, { recursive: true, force: true, maxRetries: 5 });
}
