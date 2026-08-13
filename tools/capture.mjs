#!/usr/bin/env node
/*
 * 4案のフルページスクリーンショットを撮る比較用ツール。
 * 改修の前後で撮って docs/shots/<ラベル>/ を見比べる。
 *
 * 使い方:
 *   npm i playwright-core   # 初回のみ(ブラウザ本体は不要。CHROMIUM env参照)
 *   node tools/capture.mjs <ラベル> [ページ...] [--width 375,1280]
 * 例:
 *   node tools/capture.mjs before                # 4案×375/1280px → docs/shots/before/
 *   node tools/capture.mjs after index.html --width 375
 *
 * Chromium の場所は環境変数 CHROMIUM で上書き可(既定: /opt/pw-browsers/chromium)。
 */
import { chromium } from 'playwright-core';
import { mkdirSync } from 'node:fs';
import { resolve, basename } from 'node:path';

const args = process.argv.slice(2);
const label = args[0] && !args[0].startsWith('--') ? args[0] : 'shots';
const wIdx = args.indexOf('--width');
const widths = wIdx >= 0 ? args[wIdx + 1].split(',').map(Number) : [375, 1280];
const pages = args.slice(1).filter((a, i) => !a.startsWith('--') && args[i] !== '--width' && a.endsWith('.html'));
const targets = pages.length ? pages : ['index.html', 'hitotonari.html', 'editorial.html', 'gravure.html'];

const outDir = resolve('docs/shots', label);
mkdirSync(outDir, { recursive: true });

const executablePath = process.env.CHROMIUM || '/opt/pw-browsers/chromium';
const browser = await chromium.launch({ executablePath, args: ['--no-sandbox'] });

for (const file of targets) {
  for (const width of widths) {
    const page = await browser.newPage({
      viewport: { width, height: 800 },
      deviceScaleFactor: 1,
      // アニメーション途中で撮れると比較がブレるので初期状態で固定する
      reducedMotion: 'reduce',
    });
    await page.goto('file://' + resolve(file), { waitUntil: 'networkidle' });
    await page.waitForTimeout(600); // フォント描画待ち
    const out = `${outDir}/${basename(file, '.html')}-${width}.png`;
    await page.screenshot({ path: out, fullPage: true });
    console.log(out);
    await page.close();
  }
}
await browser.close();
