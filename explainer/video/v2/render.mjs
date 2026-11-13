// Render the film frame by frame in headless Chrome (DevTools protocol) and pipe the frames to ffmpeg.
// usage: node --experimental-websocket render.mjs video <frames.mkv> [startFrame endFrame]
//        node --experimental-websocket render.mjs stills <outDir> <t1,t2,...>
//        node --experimental-websocket render.mjs sfx <out.json>
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
const [mode, out, ...rest] = process.argv.slice(2);
const HERE = path.dirname(new URL(import.meta.url).pathname);
const W = 1080, H = 1350, port = 9400 + Math.floor(Math.random() * 400);
const prof = fs.mkdtempSync(path.join(os.tmpdir(), 'film-prof-'));
const chrome = spawn('/usr/bin/google-chrome', ['--headless=new', '--remote-debugging-port=' + port, '--user-data-dir=' + prof, '--no-first-run',
  '--hide-scrollbars', '--disable-gpu', '--allow-file-access-from-files', '--force-device-scale-factor=1', 'about:blank'], { stdio: 'ignore' });
const sleep = ms => new Promise(r => setTimeout(r, ms));
let target;
for (let i = 0; i < 60 && !target; i++) { await sleep(200); try { target = (await (await fetch('http://127.0.0.1:' + port + '/json/list')).json()).find(t => t.type === 'page'); } catch (e) {} }
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise(r => ws.addEventListener('open', r));
let id = 0; const pend = new Map(); const errors = []; let loaded; const onLoad = new Promise(r => { loaded = r; });
ws.addEventListener('message', ev => {
  const m = JSON.parse(ev.data);
  if (m.id && pend.has(m.id)) { pend.get(m.id)(m); pend.delete(m.id); }
  if (m.method === 'Page.loadEventFired') loaded();
  if (m.method === 'Runtime.exceptionThrown') errors.push('EXC ' + (m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text));
  if (m.method === 'Log.entryAdded' && m.params.entry.level === 'error') errors.push('LOG ' + m.params.entry.text + ' ' + (m.params.entry.url || ''));
});
const send = (method, params = {}) => new Promise(r => { const i = ++id; pend.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async expr => { const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true }); if (r.result.exceptionDetails) errors.push('EVAL ' + (r.result.exceptionDetails.exception?.description || r.result.exceptionDetails.text)); return r.result.result?.value; };
await send('Page.enable'); await send('Runtime.enable'); await send('Log.enable');
await send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 1, mobile: false });
await send('Page.navigate', { url: 'file://' + path.join(HERE, 'film.html') });
await onLoad;
console.log('fonts loaded:', await ev('F.ready()'), 'duration', await ev('TL.dur'));
await ev('F.seek(1)'); await sleep(300);
const shot = async (fmt, q) => Buffer.from((await send('Page.captureScreenshot', { format: fmt, quality: q, clip: { x: 0, y: 0, width: W, height: H, scale: 1 } })).result.data, 'base64');
if (mode === 'sfx') {
  fs.writeFileSync(out, await ev('JSON.stringify({dur: TL.dur, sfx: F.sfx})'));
} else if (mode === 'stills') {
  fs.mkdirSync(out, { recursive: true });
  for (const t of rest[0].split(',')) { await ev(`F.seek(${+t})`); fs.writeFileSync(path.join(out, 't' + (+t).toFixed(2).padStart(6, '0') + '.png'), await shot('png')); }
} else {
  const fps = 30, total = Math.round((await ev('TL.dur')) * fps), f0 = +(rest[0] || 0), f1 = +(rest[1] || total);
  const ff = spawn('ffmpeg', ['-y', '-v', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-',
    '-c:v', 'copy', out], { stdio: ['pipe', 'inherit', 'inherit'] });   // JPEG frames kept as they are (.mkv); encode.sh makes the H.264 file
  const t0 = Date.now();
  for (let f = f0; f < f1; f++) {
    await ev(`F.seek(${f / fps})`);
    const buf = await shot('jpeg', 96);
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (f % 300 === 0) console.log('frame', f, 'of', f1, ((Date.now() - t0) / 1000).toFixed(0) + 's');
  }
  ff.stdin.end(); await new Promise(r => ff.on('close', r));
  console.log('frames', f1 - f0, 'in', ((Date.now() - t0) / 1000).toFixed(0) + 's');
}
console.log(errors.length ? errors.slice(0, 20).join('\n') : 'no page errors');
ws.close(); chrome.kill(); await sleep(300); fs.rmSync(prof, { recursive: true, force: true });
