#!/usr/bin/env node
// Render an HTML scene to an MP4, frame by frame.
//
// A scene is an HTML page that defines `window.renderFrame(t)` (t = seconds).
// The renderer sets the time, takes a screenshot, and pipes the frames to ffmpeg,
// so animation is exact and never depends on real-time playback.
//
// Usage:
//   node tools/render.mjs <scene.html> <out.mp4> [--duration 5] [--fps 30]
//        [--width 1920] [--height 1080] [--params '{"key":"value"}'] [--alpha]
//
// --params is passed to the scene as window.SCENE_PARAMS (before it loads).
// --alpha writes a transparent .mov (ProRes 4444) for layering in an editor.

import { createRequire } from 'node:module';
import { spawn } from 'node:child_process';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

// Playwright is installed globally in this environment; ESM imports don't see global
// packages, so load it through require (which honors NODE_PATH / global installs).
const require = createRequire(import.meta.url);
let chromium;
try { ({ chromium } = require('playwright')); }
catch { ({ chromium } = require('/opt/node22/lib/node_modules/playwright')); }

const args = process.argv.slice(2);
const opt = (name, def) => {
  const i = args.indexOf(`--${name}`);
  return i >= 0 ? args[i + 1] : def;
};
const flag = (name) => args.includes(`--${name}`);
const BOOL_FLAGS = ['--alpha'];
const positional = args.filter((a, i) =>
  !a.startsWith('--') && !(i > 0 && args[i - 1].startsWith('--') && !BOOL_FLAGS.includes(args[i - 1])));
const [scene, out] = positional;
if (!scene || !out) {
  console.error('usage: node tools/render.mjs <scene.html> <out.mp4> [--duration s] [--fps n] [--params json] [--alpha]');
  process.exit(1);
}
const duration = parseFloat(opt('duration', '5'));
const fps = parseInt(opt('fps', '30'), 10);
const width = parseInt(opt('width', '1920'), 10);
const height = parseInt(opt('height', '1080'), 10);
const params = JSON.parse(opt('params', '{}'));
const alpha = flag('alpha');
const total = Math.round(duration * fps);

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 });
await page.addInitScript((p) => { window.SCENE_PARAMS = p; }, params);
await page.goto(pathToFileURL(path.resolve(scene)).href);
await page.waitForFunction(() => typeof window.renderFrame === 'function');
await page.evaluate(() => document.fonts.ready);
if (await page.evaluate(() => typeof window.sceneReady === 'function')) {
  await page.evaluate(() => window.sceneReady());
}

const ffArgs = ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-i', '-'];
if (alpha) ffArgs.push('-c:v', 'prores_ks', '-profile:v', '4444', '-pix_fmt', 'yuva444p10le', out);
else ffArgs.push('-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'medium', out);
const ff = spawn('ffmpeg', ffArgs, { stdio: ['pipe', 'inherit', 'inherit'] });
const ffDone = new Promise((res, rej) => ff.on('close', (c) => (c === 0 ? res() : rej(new Error(`ffmpeg exited ${c}`)))));

for (let f = 0; f < total; f++) {
  await page.evaluate((t) => window.renderFrame(t), f / fps);
  const buf = await page.screenshot({ type: 'png', omitBackground: alpha });
  if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
  if (f % fps === 0) process.stdout.write(`\r${scene}: ${f}/${total} frames`);
}
ff.stdin.end();
await ffDone;
await browser.close();
console.log(`\rwrote ${out} (${duration}s, ${total} frames @ ${fps}fps)          `);
