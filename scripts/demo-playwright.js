/**
 * Archon — Automated Demo Recording via Playwright
 *
 * Drives the live frontend end-to-end and records a .webm screen capture
 * ready to be combined with ElevenLabs narration in FFmpeg.
 *
 * Usage:
 *   npm install playwright @playwright/test    (one time)
 *   npx playwright install chromium            (one time)
 *
 *   # Start frontend pointing at live backend:
 *   cd frontend
 *   echo "VITE_API_BASE_URL=https://archon-backend.politemeadow-da83e97d.westeurope.azurecontainerapps.io" > .env.local
 *   npm install && npm run dev &               (runs on localhost:3000)
 *
 *   # In another terminal:
 *   node scripts/demo-playwright.js
 *
 * Output: scripts/demo-output/demo.webm  (~5 min, 1920x1080)
 *
 * Then combine with narration:
 *   ffmpeg -i scripts/demo-output/demo.webm -i narration.mp3 \
 *          -c:v copy -c:a aac -shortest output/archon-demo.mp4
 */

const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:3000';
const ANALYSIS_URL = process.env.ANALYSIS_URL ||
  'https://archon-analysis.politemeadow-da83e97d.westeurope.azurecontainerapps.io';
const PERIOD = '2026-01';

// Pause durations (ms) — tune to match narration pacing
const PAUSE = {
  hook: 6000,          // 0:00–0:25 hook narration
  problem: 8000,       // 0:25–1:00 problem section
  solution: 10000,     // 1:00–1:45 solution overview
  upload: 12000,       // 1:45–2:30 upload demo
  dashboard: 14000,    // 2:30–3:15 dashboard
  foundry: 12000,      // 3:15–4:00 foundry IQ
  teams: 10000,        // 4:00–4:40 teams section
  close: 6000,         // 4:40–5:00 close
};

async function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

async function seedDemoData() {
  const res = await fetch(`${ANALYSIS_URL}/seed-demo`, { method: 'POST' });
  if (!res.ok) throw new Error(`Seed failed: ${res.status}`);
  console.log('  Demo data seeded via analysis endpoint');
}

(async () => {
  const outputDir = path.join(__dirname, 'demo-output');
  if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir, { recursive: true });

  console.log('Seeding demo data...');
  await seedDemoData();

  console.log('Launching browser for recording...');
  const browser = await chromium.launch({
    headless: false,   // visible window for screen recording (OBS) OR use video below
    args: ['--start-maximized'],
  });

  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    // Playwright built-in video recording (alternative to OBS):
    recordVideo: {
      dir: outputDir,
      size: { width: 1920, height: 1080 },
    },
  });

  const page = await context.newPage();

  // ── [0:00] HOOK — title card ──────────────────────────────────────────────
  console.log('[0:00] Hook — title card');
  await page.goto(FRONTEND_URL);
  await page.waitForLoadState('networkidle');
  await sleep(PAUSE.hook);

  // ── [0:25] THE PROBLEM — upload page ─────────────────────────────────────
  console.log('[0:25] Problem section');
  // Highlight the 4-document-stream concept by navigating to upload
  await page.goto(`${FRONTEND_URL}/upload`);
  await page.waitForLoadState('networkidle');
  await sleep(PAUSE.problem);

  // ── [1:00] SOLUTION — architecture (dashboard page while empty) ───────────
  console.log('[1:00] Solution overview');
  await page.goto(`${FRONTEND_URL}`);
  await page.waitForLoadState('networkidle');
  await sleep(PAUSE.solution);

  // ── [1:45] DEMO — upload flow ─────────────────────────────────────────────
  console.log('[1:45] Upload demo');
  await page.goto(`${FRONTEND_URL}/upload`);
  await page.waitForLoadState('networkidle');

  // Show period selector and fill it
  const periodInput = page.locator('input[placeholder*="period"], input[placeholder*="Period"], input[type="text"]').first();
  if (await periodInput.count()) {
    await periodInput.fill('');
    await periodInput.type(PERIOD, { delay: 80 });
  }
  await sleep(3000);

  // Simulate dragging files (show upload UI)
  // The upload zone renders — pause for narration
  await sleep(PAUSE.upload);

  // ── [2:30] DASHBOARD — trigger analysis and show results ──────────────────
  console.log('[2:30] Analysis dashboard');
  await page.goto(`${FRONTEND_URL}`);
  await page.waitForLoadState('networkidle');

  // Trigger analyze for the demo period
  try {
    const analyzeBtn = page.locator('button:has-text("Analyze"), button:has-text("analyze"), button:has-text("Analyse")').first();
    if (await analyzeBtn.count()) {
      await analyzeBtn.click();
    } else {
      // Directly call the API from the browser console
      await page.evaluate(async (period) => {
        await fetch('/api/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ period }),
        });
      }, PERIOD);
    }
  } catch (_) { /* dashboard may auto-load */ }

  // Wait for dashboard to populate (analysis pipeline runs ~30-60s)
  console.log('  Waiting for analysis to complete...');
  await page.waitForTimeout(45000);
  await page.reload();
  await page.waitForLoadState('networkidle');
  await sleep(PAUSE.dashboard);

  // ── [3:15] FOUNDRY IQ — scroll to executive summary ──────────────────────
  console.log('[3:15] Foundry IQ executive summary');
  // Scroll to executive summary section
  const summaryEl = page.locator(
    '[class*="summary"], [class*="Summary"], [class*="executive"], h2:has-text("Summary"), h3:has-text("Summary")'
  ).first();
  if (await summaryEl.count()) {
    await summaryEl.scrollIntoViewIfNeeded();
    await sleep(1000);
    // Highlight the element
    await page.evaluate((el) => {
      el.style.boxShadow = '0 0 0 4px #7c4dff';
      el.style.borderRadius = '8px';
    }, await summaryEl.elementHandle());
  }
  await sleep(PAUSE.foundry);

  // ── [4:00] TEAMS / ENTERPRISE AGENT note ────────────────────────────────
  console.log('[4:00] Enterprise agent section');
  // Navigate to any dedicated Teams/enterprise section, or show the README
  await page.goto('https://github.com/upgradedev/archon_azure#enterprise-agents-track--microsoft-365-copilot-integration');
  await page.waitForLoadState('networkidle');
  await sleep(PAUSE.teams);

  // ── [4:40] CLOSE — repo link ─────────────────────────────────────────────
  console.log('[4:40] Close');
  await page.goto('https://github.com/upgradedev/archon_azure');
  await page.waitForLoadState('networkidle');
  await sleep(PAUSE.close);

  await context.close();
  await browser.close();

  // Rename the output file
  const files = fs.readdirSync(outputDir).filter(f => f.endsWith('.webm'));
  if (files.length) {
    const src = path.join(outputDir, files[files.length - 1]);
    const dst = path.join(outputDir, 'demo.webm');
    fs.renameSync(src, dst);
    console.log(`\nRecording saved: ${dst}`);
    console.log('\nNext step — add narration:');
    console.log('  ffmpeg -i scripts/demo-output/demo.webm -i narration.mp3 \\');
    console.log('         -c:v copy -c:a aac -shortest output/archon-demo.mp4');
  }

  console.log('\nDone.');
})();
