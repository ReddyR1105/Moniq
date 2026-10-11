import { test, expect, type Page } from '@playwright/test'

async function nav(page: Page, name: string) {
  const menu = page.getByRole('button', { name: 'Open navigation', exact: true })
  if ((page.viewportSize()?.width ?? 1920) <= 760) {
    await expect(menu).toBeVisible()
    await menu.tap()
    await expect(page.locator('.sidebar')).toHaveClass(/open/)
  }
  await page.getByRole('navigation', { name: 'Main navigation' }).getByRole('button', { name, exact: true }).tap()
}

test('PWA manifest, genuine icons and Chromium installability metadata @public', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByTestId('balance')).toBeVisible()
  await page.evaluate(() => navigator.serviceWorker.ready)
  const response = await page.request.get('/manifest.webmanifest')
  expect(response.ok()).toBeTruthy()
  const manifest = await response.json()
  expect(manifest.name).toBe('Moniq — Spending, Made Smarter.')
  expect([manifest.id, manifest.start_url, manifest.scope, manifest.display]).toEqual(['/', '/', '/', 'standalone'])
  for (const icon of manifest.icons) {
    expect((await page.request.get(icon.src)).headers()['content-type']).toContain('image/png')
    const dimensions = await page.evaluate(async (src: string) => {
      const img = new Image(); img.src = src; await img.decode(); return `${img.naturalWidth}x${img.naturalHeight}`
    }, icon.src)
    expect(dimensions).toBe(icon.sizes)
  }
  await expect(page.locator('link[rel=apple-touch-icon]')).toHaveAttribute('href', '/icons/apple-touch-icon.png')
  await expect(page.locator('meta[name=viewport]')).toHaveAttribute('content', /viewport-fit=cover/)
  const cdp = await page.context().newCDPSession(page)
  const data = await cdp.send('Page.getAppManifest')
  expect(data.errors).toEqual([])
  const status = await cdp.send('Page.getInstallabilityErrors')
  expect(status.installabilityErrors).toEqual([])
})

test('service worker caches static assets only and keeps financial/API navigation online @public', async ({ page, context }) => {
  await page.goto('/')
  await expect(page.getByTestId('balance')).toBeVisible()
  await page.evaluate(() => navigator.serviceWorker.ready)
  await page.reload()
  const api = await page.request.get('/api/export')
  expect(api.headers()['cache-control']).toBe('no-store')
  await page.evaluate(async () => { await fetch('/api/dashboard'); await fetch('/api/export'); await fetch('/api/gmail/status') })
  const keys = await page.evaluate(async () => {
    const requests = await Promise.all((await caches.keys()).map(async name => (await (await caches.open(name)).keys()).map(request => request.url)))
    return requests.flat().map(url => new URL(url).pathname)
  })
  expect(keys.length).toBeGreaterThan(4)
  expect(keys.every(path => /^(\/assets\/[^/]+\.(js|css)|\/icons\/[^/]+\.png|\/icon\.svg|\/offline\.html)$/.test(path))).toBeTruthy()
  expect(keys.some(path => path.startsWith('/api'))).toBeFalsy()
  await context.setOffline(true)
  expect(await page.evaluate(async () => { try { await fetch('/api/dashboard'); return 'cached' } catch { return 'network-only' } })).toBe('network-only')
  await page.goto('/offline-check')
  await expect(page.getByRole('heading', { name: 'Moniq needs a connection.' })).toBeVisible()
  expect(await page.evaluate(async () => { try { await fetch('/api/export'); return true } catch { return false } })).toBeFalsy()
  await context.setOffline(false)
  await page.goto('/')
  await expect(page.getByTestId('balance')).toBeVisible()
})

test('mobile touch email approvals, Circles repayment and goals update the public ledger @public', async ({ browser, baseURL }) => {
  test.setTimeout(90000)
  const context = await browser.newContext({ baseURL, viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true })
  const page = await context.newPage()
  try {
    await page.goto('/#circles')
    await page.getByLabel('Starting synthetic checking balance ($)', { exact: true }).fill('10')
    page.once('dialog', d => d.accept())
    await page.getByRole('button', { name: 'Start isolated walkthrough', exact: true }).tap()
    await expect(page.locator('h1')).toHaveText('Moniq Circles')
    await nav(page, 'Overview')
    await expect(page.getByTestId('balance')).toHaveText('$10.00')
    for (const [button, result] of [['Simulate $400 paycheck email', '$410.00'], ['Simulate $15 purchase email', '$395.00']]) {
      await page.getByRole('button', { name: button, exact: true }).tap()
      const item = page.locator('.gmail-review')
      await expect(item.getByRole('button', { name: 'Confirm email transaction' })).toBeDisabled()
      await item.getByRole('checkbox').tap()
      await item.getByRole('button', { name: 'Confirm email transaction' }).tap()
      await expect(page.getByTestId('balance')).toHaveText(result)
    }
    await nav(page, 'Circles')
    await page.getByRole('button', { name: 'Process controlled $40 alert', exact: true }).tap()
    await expect(page.locator('.toast')).toContainText('Estimated cash is $355')
    await page.getByRole('button', { name: 'New circle', exact: true }).tap()
    await page.getByRole('button', { name: 'Create circle', exact: true }).tap()
    await page.getByLabel('Expense to split').selectOption({ label: 'Chick-fil-A · $40.00 · #3' })
    await page.getByRole('button', { name: 'Split with Friends', exact: true }).tap()
    await page.getByRole('button', { name: 'Save shared expense', exact: true }).tap()
    await expect(page.getByTestId('circle-receivable')).toHaveText('$20.00')
    await page.getByRole('button', { name: 'Mark as paid / partial repayment', exact: true }).tap()
    await page.getByLabel('Record an actual bank cash movement').tap()
    await page.getByLabel('I confirmed this repayment happened.', { exact: true }).tap()
    await page.getByRole('button', { name: 'Save repayment', exact: true }).tap()
    await expect(page.getByTestId('circle-receivable')).toHaveText('$0.00')
    const data = await (await page.request.get('/api/dashboard')).json()
    expect([data.balance, data.income, data.expenses]).toEqual([375, 400, 35])
    await nav(page, 'Settings')
    await expect(page.getByRole('button', { name: 'Connect Gmail', exact: true })).toHaveCount(0)
    await page.getByLabel('Planned monthly contribution ($)', { exact: true }).fill('100')
    await page.getByRole('button', { name: 'Save contribution plan', exact: true }).tap()
    await expect(page.getByText(/Estimated completion:/)).toBeVisible()
    await page.getByLabel('Recorded contribution ($)', { exact: true }).fill('25')
    await page.getByRole('button', { name: 'Record goal contribution', exact: true }).tap()
    expect((await (await page.request.get('/api/dashboard')).json()).balance).toBe(375)
    await nav(page, 'AI Assistant')
    await page.getByRole('button', { name: 'When was my last confirmed paycheck?', exact: true }).tap()
    await expect(page.locator('.chat-message.assistant')).toContainText('$400.00')
    await nav(page, 'Overview')
    await expect(page.getByTestId('balance')).toHaveText('$375.00')
    await page.evaluate(() => { (document.activeElement as HTMLElement)?.blur(); window.scrollTo(0, 0) })
    await page.screenshot({ path: '../.runtime/mobile-pwa-overview.png', fullPage: true })
  } finally { await context.close() }
})

test('mobile installation hint uses the browser prompt and provides iPhone instructions @public', async ({ browser, baseURL }) => {
  const context = await browser.newContext({ baseURL, viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true })
  const page = await context.newPage()
  try {
    await page.goto('/#settings')
    const hint = page.getByRole('region', { name: 'Install Moniq', exact: true })
    await expect(hint).toBeVisible()
    await page.evaluate(() => {
      const event = new Event('beforeinstallprompt')
      Object.assign(event, { prompt: async () => ({ outcome: 'accepted' }) })
      window.dispatchEvent(event)
    })
    await hint.getByRole('button', { name: 'Install Moniq', exact: true }).tap()
    await expect(hint).toHaveCount(0)
    const iphone = await context.newPage()
    await iphone.addInitScript(() => Object.defineProperty(navigator, 'userAgent', { get: () => 'Mozilla/5.0 (iPhone) AppleWebKit/605.1.15 Version/18.0 Mobile Safari/604.1' }))
    await iphone.goto('/#settings')
    await expect(iphone.getByRole('region', { name: 'Install Moniq', exact: true })).toContainText('In Safari, open Share, then Add to Home Screen')
    await iphone.getByRole('region', { name: 'Install Moniq', exact: true }).scrollIntoViewIfNeeded()
    await iphone.screenshot({ path: '../.runtime/mobile-pwa-install.png' })
  } finally { await context.close() }
})

test('360 to 428px mobile navigation, charts, forms and budgets remain usable @public', async ({ browser, baseURL }) => {
  test.setTimeout(90000)
  const context = await browser.newContext({ baseURL, viewport: { width: 360, height: 800 }, isMobile: true, hasTouch: true })
  const page = await context.newPage()
  try {
    await page.goto('/')
    for (const width of [360, 390, 428]) {
      await page.setViewportSize({ width, height: 844 })
      for (const name of ['Overview', 'Transactions', 'Budgets', 'AI Insights', 'Circles', 'AI Assistant', 'Settings']) {
        await nav(page, name)
        await expect(page.locator('h1')).toBeVisible()
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${name} at ${width}px`).toBeTruthy()
      }
    }
    await nav(page, 'Budgets')
    await expect(page.locator('.budget-card').first()).toBeVisible()
    await nav(page, 'AI Insights')
    await page.getByRole('button', { name: 'Run scenario', exact: true }).tap()
    await expect(page.getByTestId('scenario-difference')).toContainText('-$150.00')
    await expect(page.locator('.recharts-surface').first()).toBeVisible()
    const button = await page.getByRole('button', { name: 'Run scenario', exact: true }).boundingBox()
    expect(button!.height).toBeGreaterThanOrEqual(44)
  } finally { await context.close() }
})
