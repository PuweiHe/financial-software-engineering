const { test, before, after } = require('node:test');
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const { spawn } = require('node:child_process');
const path = require('node:path');
const fs = require('node:fs');
const artifacts = path.resolve(__dirname, '../test-results');
let caseNumber = 0;
async function openPage(options) {
  const context = await browser.newContext(options);
  await context.tracing.start({ screenshots: true, snapshots: true });
  return context.newPage();
}
async function capture(page) {
  const name = `browser-${++caseNumber}`;
  await page.screenshot({ path: path.join(artifacts, name + '.png'), fullPage: true });
  await page.context().tracing.stop({ path: path.join(artifacts, name + '.zip') });
  await page.context().close();
}

let server, browser, base;
before(async () => {
  fs.mkdirSync(artifacts, { recursive: true });
  server = spawn(process.env.PYTHON || 'python3', ['-u', '-m', 'portfolio_demo.agent_server', '--port', '0'], {
    cwd: path.resolve(__dirname, '..'), stdio: ['ignore', 'pipe', 'pipe'],
  });
  base = await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('Server startup timed out')), 10000);
    server.on('error', reject);
    server.on('exit', code => { clearTimeout(timer); reject(new Error(`Server exited: ${code}`)); });
    server.stderr.on('data', chunk => fs.appendFileSync(path.join(artifacts, 'server.log'), chunk));
    server.stderr.on('data', chunk => {
      const match = chunk.toString().match(/http:\/\/127\.0\.0\.1:\d+/);
      if (match) { clearTimeout(timer); resolve(match[0]); }
    });
  });
  browser = await chromium.launch({ headless: true, channel: process.env.PLAYWRIGHT_CHANNEL || undefined });
});
after(async () => { await browser?.close(); server?.kill('SIGINT'); });

test('browser selects a branch and preserves missing history', async () => {
  const page = await openPage({ viewport: { width: 390, height: 844 } });
  try {
    await page.goto(base);
    await page.waitForFunction(() => document.querySelector('#status').textContent === 'Showing local sample data');
    await page.selectOption('#branch', 'BRANCH003');
    await page.waitForFunction(() => document.querySelector('#growth').textContent === 'No baseline');
    assert.equal(await page.locator('#share').textContent(), '20.0%');
    assert.equal(await page.locator('#rows tr.selected').count(), 1);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  } finally { await capture(page); }
});

test('failed metrics clear stale values and retry recovers', async () => {
  const page = await openPage();
  try {
    await page.goto(base);
    await page.waitForFunction(() => document.querySelector('#total').textContent === '100.0');
    await page.route('**/api/metrics?**', route => route.fulfill({status: 503, contentType:'application/json', body:'{"error":"Temporarily unavailable"}'}));
    await page.selectOption('#year', '2024');
    await page.locator('#retry').waitFor({ state:'visible' });
    assert.equal(await page.locator('#total').textContent(), '—');
    assert.equal(await page.locator('#rows tr').count(), 0);
    await page.unroute('**/api/metrics?**');
    await page.click('#retry');
    await page.waitForFunction(() => document.querySelector('#total').textContent === '100.0');
  } finally { await capture(page); }
});

test('empty dataset shows an explicit empty state', async () => {
  const page = await openPage();
  try {
    await page.route('**/api/years', route => route.fulfill({status:200,contentType:'application/json',body:'{"years":[],"synthetic":true}'}));
    await page.goto(base);
    await page.waitForFunction(() => document.querySelector('#status').textContent === 'No sample years available');
    assert.equal(await page.locator('#year').isDisabled(), true);
    assert.equal(await page.locator('#rows tr').count(), 0);
  } finally { await capture(page); }
});


test('agent streams SQL evidence and preserves missing history', async () => {
  const page = await openPage();
  try {
    await page.goto(base);
    await page.locator('#agent-panel').waitFor({ state: 'visible' });
    await page.click('#ask');
    await page.waitForFunction(() => document.querySelector('#agent-status').textContent === 'Complete · synthetic data');
    const evidence = await page.locator('#agent-evidence').textContent();
    assert.match(evidence, /BRANCH003/);
    assert.match(evidence, /20.0%/);
    assert.match(evidence, /No baseline/);
    await page.fill('#question', 'Revenue in 2024 and 2025?');
    await page.click('#ask');
    await page.waitForFunction(() => document.querySelector('#agent-answer').textContent.includes('one year'));
    assert.equal(await page.locator('#agent-evidence').textContent(), '');
  } finally { await capture(page); }
});

test('agent stream failure clears evidence and permits retry', async () => {
  const page = await openPage();
  try {
    await page.goto(base);
    await page.locator('#agent-panel').waitFor({ state: 'visible' });
    await page.route('**/api/agent/stream', route => route.fulfill({
      status: 200, contentType: 'text/event-stream',
      body: 'event: error\ndata: {"message":"Request timed out. Please retry."}\n\n',
    }));
    await page.click('#ask');
    await page.waitForFunction(() => document.querySelector('#agent-status').textContent.startsWith('Unable to complete:'));
    assert.equal(await page.locator('#agent-evidence').textContent(), '');
    assert.equal(await page.locator('#ask').isDisabled(), false);
    await page.unroute('**/api/agent/stream');
    await page.click('#ask');
    await page.waitForFunction(() => document.querySelector('#agent-status').textContent === 'Complete · synthetic data');
  } finally { await capture(page); }
});
