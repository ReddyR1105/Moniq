// Capture the working application in a new synthetic-only workspace.
import { createRequire } from 'node:module'
import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const require = createRequire(path.join(root, 'frontend/package.json'))
const { chromium, expect } = require('@playwright/test')
const output = path.join(root, '.runtime/premium-recording')
const plan = JSON.parse(await fs.readFile(path.join(output, 'narration-plan.json'), 'utf8'))
const fast = process.env.MONIQ_PREMIUM_FAST === '1'
const browser = await chromium.launch({ headless: true })
const context = await browser.newContext({ baseURL: 'http://127.0.0.1:5175', viewport: { width: 1440, height: 720 }, recordVideo: { dir: output, size: { width: 1440, height: 720 } }, reducedMotion: 'reduce' })
await context.route('**/*', route => new URL(route.request().url()).hostname === '127.0.0.1' ? route.continue() : route.abort())
const page = await context.newPage(), video = page.video(), failures = [], timeline = []
const recordingStarted = Date.now()
let activeScene, sceneStarted
async function untilBoundary(index, offset = 0) {
  if (fast) return
  const seconds = activeScene.boundaries[index].start + offset
  await page.waitForTimeout(Math.max(0, seconds * 1000 - (Date.now() - sceneStarted)))
}
page.on('pageerror', error => failures.push(error.message))
async function click(name) {
  const target = page.getByRole('button', { name, exact: true })
  await target.scrollIntoViewIfNeeded()
  const box = await target.boundingBox()
  if (box) await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: 8 })
  await target.click()
  await page.waitForTimeout(160)
}
async function nav(name) {
  await page.getByRole('navigation', { name: 'Main navigation' }).getByRole('button', { name, exact: true }).click()
  await expect(page.locator('h1')).toBeVisible()
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.waitForTimeout(250)
}
async function email(event, balance) {
  if (event === 'paycheck') await untilBoundary(1)
  await click(event === 'paycheck' ? 'Simulate $400 paycheck email' : 'Simulate $15 purchase email')
  const card = page.locator('.gmail-review')
  await card.scrollIntoViewIfNeeded()
  await expect(card).toContainText('Simulated')
  await page.waitForTimeout(700)
  await untilBoundary(event === 'purchase' ? 2 : 1, event === 'purchase' ? 0 : 2)
  await card.getByRole('checkbox').check()
  await card.getByRole('button', { name: 'Confirm email transaction', exact: true }).click()
  await expect(page.getByTestId('balance')).toHaveText(balance)
  await page.evaluate(() => window.scrollTo(0, 0))
}
async function startScenario() {
  await nav('Circles')
  await page.getByLabel('Starting synthetic checking balance ($)', { exact: true }).fill('10')
  page.once('dialog', dialog => dialog.accept()); await click('Start isolated walkthrough')
  await expect(page.getByText('ISOLATED SYNTHETIC SCENARIO', { exact: true })).toBeVisible()
  await nav('Overview'); await expect(page.getByTestId('balance')).toHaveText('$10.00')
}
const actions = {
  intro: async () => {},
  gmail: async () => {
    await click('Return to synthetic demo')
    await expect(page.getByText('DEMO MODE', { exact: true })).toBeVisible()
    await nav('Settings'); await page.getByRole('heading', { name: 'Gmail financial alerts', exact: true }).scrollIntoViewIfNeeded()
    await expect(page.getByRole('button', { name: 'Connect Gmail', exact: true })).toBeDisabled()
    await page.waitForTimeout(2200)
    await startScenario()
  },
  paycheck: async () => { await nav('Overview'); await email('paycheck', '$410.00') },
  purchase: async () => email('purchase', '$395.00'),
  smartapprove: async () => {
    await nav('Settings')
    await page.getByRole('heading', { name: 'SmartApprove · Trusted Senders', exact: true }).scrollIntoViewIfNeeded()
    await expect(page.getByLabel('Enable automatic approval for this sender')).not.toBeChecked()
    await untilBoundary(2, -.4)
    await nav('Circles'); await click('Process controlled $40 alert')
    await expect(page.locator('.toast')).toContainText('$355.00')
    await nav('Settings'); await page.getByText(/auto-approved/).last().scrollIntoViewIfNeeded()
  },
  circles: async () => {
    await nav('Circles'); await untilBoundary(1); await click('New circle'); await click('Create circle')
    await expect(page.getByRole('dialog')).toHaveCount(0)
    const tx = await (await page.request.get('/api/transactions')).json()
    const dinner = tx.find(row => row.amount === -40 && row.source === 'gmail-auto')
    if (!dinner) throw Error('Missing actual controlled dinner transaction')
    await page.getByLabel('Expense to split').selectOption(String(dinner.id))
    await click('Split with Friends'); await click('Save shared expense')
    await expect(page.getByTestId('circle-receivable')).toHaveText('$20.00')
    await page.locator('.circle-expense').scrollIntoViewIfNeeded()
  },
  repayment: async () => {
    await click('Mark as paid / partial repayment')
    await page.getByLabel('Record an actual bank cash movement').check()
    await page.getByLabel('I confirmed this repayment happened.', { exact: true }).check()
    await click('Save repayment'); await expect(page.getByTestId('circle-receivable')).toHaveText('$0.00')
    const d = await (await page.request.get('/api/dashboard')).json()
    if (d.balance !== 375 || d.income !== 400 || d.expenses !== 35) throw Error('Invalid recorded bookkeeping')
    await nav('Overview'); await expect(page.getByTestId('balance')).toHaveText('$375.00')
    await untilBoundary(2)
    const income = page.locator('.stat-grid > .panel').filter({ hasText: 'Income this month' }).locator('strong')
    await income.scrollIntoViewIfNeeded()
    await expect(income).toHaveText('$400.00')
  },
  forecast: async () => {
    await nav('Budgets'); await page.waitForTimeout(1100); await nav('AI Insights')
    await page.getByLabel('Purchase ($)', { exact: true }).fill('100'); await click('Run scenario')
    await expect(page.getByTestId('scenario-difference')).toContainText('-$100.00')
    await page.locator('.forecast-chart').scrollIntoViewIfNeeded()
  },
  goals: async () => {
    await nav('Settings'); await page.getByLabel('Planned monthly contribution ($)', { exact: true }).fill('100')
    await click('Save contribution plan'); await expect(page.getByText(/Estimated completion:/)).toBeVisible()
    await page.getByLabel('Recorded contribution ($)', { exact: true }).fill('25'); await click('Record goal contribution')
    await expect(page.getByText(/recorded contribution$/)).toBeVisible()
  },
  assistant: async () => { await nav('AI Assistant'); await click('When was my last confirmed paycheck?'); await expect(page.locator('.chat-message.assistant').last()).toContainText('$400.00') },
  closing: async () => { await nav('Overview'); await expect(page.getByTestId('balance')).toHaveText('$375.00') },
}
try {
  const status = await (await page.request.get('/api/gmail/status')).json()
  if (status.connected || status.configured) throw Error('Recording must disable real Gmail')
  await page.goto('/#circles')
  await startScenario()
  const started = recordingStarted
  for (const scene of plan.scenes) {
    const begin = (Date.now() - started) / 1000
    activeScene = scene; sceneStarted = Date.now()
    console.log('SCENE ' + scene.id)
    await actions[scene.id]()
    if (failures.length) throw Error(failures.join('; '))
    const minimum = fast ? .4 : scene.boundaries.at(-1).end + .45
    await page.waitForTimeout(Math.max(400, minimum * 1000 - (Date.now() - started - begin * 1000)))
    timeline.push({ id: scene.id, start: begin, end: (Date.now() - started) / 1000 })
    await page.screenshot({ path: path.join(output, 'scene-' + scene.id + '.png') })
  }
  await context.close(); await video.saveAs(path.join(output, 'browser.webm'))
  // Playwright video starts before the first scene; retain its real timestamp offset.
  await fs.writeFile(path.join(output, 'capture-timeline.json'), JSON.stringify({ fast, scenes: timeline, recorded_seconds: (Date.now() - started) / 1000 }, null, 2))
  console.log('Capture complete; all displayed figures asserted against actual backend responses.')
} finally { await browser.close() }
