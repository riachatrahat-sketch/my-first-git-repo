// Renders index.html frame by frame and encodes MP4s with ffmpeg.
// Usage: node render.mjs [voice|short|both] [--stills t1,t2,...]
import { createRequire } from 'node:module';
const { chromium } = createRequire(import.meta.url)(process.env.PLAYWRIGHT_MODULE || 'playwright');
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import fs from 'node:fs';

const dir = path.dirname(fileURLToPath(import.meta.url));
const outDir = path.join(dir, '..', 'Media');
const FPS = 30;
const args = process.argv.slice(2);
const which = args[0] || 'both';
const stillsIdx = args.indexOf('--stills');

const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined });
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
await page.goto('file://' + path.join(dir, 'index.html') + '?render');
await page.evaluate(() => window.ready);
const grab = async t => Buffer.from((await page.evaluate(t => { renderAt(t); return document.getElementById('c').toDataURL('image/png'); }, t)).split(',')[1], 'base64');

if (stillsIdx >= 0) {
  await page.evaluate(m => setMode(m), which === 'short' ? 'short' : 'voice');
  const stillDir = path.join(dir, 'stills'); fs.mkdirSync(stillDir, { recursive: true });
  for (const t of args[stillsIdx + 1].split(',').map(Number)) fs.writeFileSync(path.join(stillDir, `${which}_${t.toFixed(2)}.png`), await grab(t));
  await browser.close(); process.exit(0);
}

async function encode(m, file, audio) {
  const total = await page.evaluate(m => setMode(m), m);
  const frames = Math.round(total * FPS);
  const ff = ['-y', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-'];
  if (audio) ff.push('-i', audio, '-filter_complex', `[1:a]apad,afade=t=out:st=${(total - 0.4).toFixed(2)}:d=0.4[a]`, '-map', '0:v', '-map', '[a]', '-c:a', 'aac', '-b:a', '192k');
  ff.push('-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-t', total.toFixed(3), file);
  const proc = spawn('ffmpeg', ff, { stdio: ['pipe', 'ignore', 'inherit'] });
  for (let f = 0; f < frames; f++) {
    const buf = await grab(f / FPS);
    if (!proc.stdin.write(buf)) await new Promise(r => proc.stdin.once('drain', r));
    if (f % 60 === 0) console.log(`${m}: frame ${f}/${frames}`);
  }
  proc.stdin.end();
  await new Promise((res, rej) => proc.on('close', c => c ? rej(new Error('ffmpeg ' + c)) : res()));
  console.log('wrote', file);
}

if (which === 'voice' || which === 'both') await encode('voice', path.join(outDir, 'gig-video-voiceover.mp4'), path.join(dir, 'voiceover.mp3'));
if (which === 'short' || which === 'both') await encode('short', path.join(outDir, 'gig-video-15s.mp4'), null);
await browser.close();
