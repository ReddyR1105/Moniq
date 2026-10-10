import { test, expect, type Page } from '@playwright/test'

test('guided demo completes all eight steps using the actual interface', async ({page}) => {
  const failures: string[] = []
  page.on('pageerror', e => failures.push(e.message))
  page.on('response', r => {if (r.url().includes('/api/') && r.status() >= 500) failures.push(`${r.status()} ${r.url()}`)})
  await page.getByRole('button',{name:'Start guided demo',exact:true}).first().click()
  const guide = page.getByRole('region',{name:'Guided demo'})
  for (let step=0;step<8;step++) {
    await expect(guide.locator('.guide-number')).toHaveText(`${step+1}/8`)
    await guide.getByRole('button',{name:'Open step',exact:false}).click()
    if (step === 1) {
      await page.getByRole('button',{name:'Simulate a purchase alert',exact:true}).click()
      await page.getByRole('button',{name:'Confirm & save transaction',exact:true}).click()
      await expect(page.getByRole('dialog')).toHaveCount(0)
    }
    if (step === 2) await expect(page.locator('.transactions-table')).toContainText('Chick-fil-A')
    if (step === 3) {
      await page.getByLabel('Food monthly limit',{exact:true}).fill('260')
      await page.locator('.budget-card').filter({has:page.getByLabel('Food monthly limit',{exact:true})}).getByRole('button',{name:'Save',exact:true}).click()
      await expect(page.locator('.toast')).toContainText('Food budget saved')
    }
    if (step === 6) {
      await page.getByRole('button',{name:'How much did I spend this week?',exact:true}).click()
      await expect(page.locator('.chat-message.assistant')).toContainText('since Monday')
    }
    if (step === 4) {
      await page.getByRole('button',{name:'Run scenario',exact:true}).click()
      await expect(page.getByTestId('scenario-difference')).toContainText('-$150.00')
    }
    if (step === 5) await expect(page.locator('.deal-card').first()).toBeVisible()
    if (step === 7) {
      page.once('dialog', d => d.accept())
      await page.getByRole('button',{name:'Reset Demo',exact:true}).click()
      await expect(page.getByLabel('Name',{exact:true})).toHaveValue('Alex Morgan')
    }
    await guide.getByRole('button',{name:step === 7 ? 'Finish guided demo' : 'Next demo step',exact:true}).click()
  }
  await expect(guide).toHaveCount(0)
  expect(failures).toEqual([])
})

test('every page fits mobile and deals filters preserve bookmarks', async ({page}) => {
  await page.setViewportSize({width:390,height:844})
  for (const name of ['Overview','Transactions','Budgets','AI Insights','Student Deals','Subscriptions','AI Assistant','Settings']) {
    await navigate(page,name)
    await expect(page.locator('h1')).toBeVisible()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), name).toBeTruthy()
    await expect(page.getByRole('alert')).toHaveCount(0)
  }
  await navigate(page,'Student Deals')
  await expect(page.locator('.deal-card').first()).toBeVisible()
  await page.locator('.deal-card').first().getByRole('button').click()
  await page.getByRole('button',{name:/Saved \(1\)/}).click()
  await expect(page.locator('.deal-card')).toHaveCount(1)
  await page.reload()
  await page.getByRole('button',{name:/Saved \(1\)/}).click()
  await expect(page.locator('.deal-card')).toHaveCount(1)
})

async function navigate(page: Page, name: string) {
  if (await page.getByRole('button',{name:'Open navigation',exact:true}).isVisible()) await page.getByRole('button',{name:'Open navigation',exact:true}).click()
  await page.getByRole('navigation',{name:'Main navigation'}).getByRole('button',{name,exact:true}).click()
}

test.beforeEach(async ({request, page}) => {
  await request.post('http://127.0.0.1:8001/api/demo/reset')
  await page.goto('/')
  await expect(page.getByTestId('balance')).toBeVisible()
})

test('judge walkthrough: alert → classification → budget → assistant → forecast → deals', async ({page}) => {
  const consoleErrors: string[] = []
  page.on('pageerror', e => consoleErrors.push(e.message))
  const before = await page.getByTestId('monthly-expenses').innerText()
  await page.getByRole('button',{name:'Try purchase alert',exact:true}).click()
  await page.getByRole('button',{name:'Simulate a purchase alert',exact:true}).click()
  await expect(page.getByRole('dialog').getByLabel('Merchant',{exact:true})).toHaveValue('Chick-fil-A')
  await expect(page.getByRole('dialog').getByLabel('Category',{exact:true})).toHaveValue('food')
  await page.getByRole('button',{name:'Confirm & save transaction',exact:true}).click()
  await expect(page.getByRole('dialog')).toHaveCount(0)
  const expected = (Number(before.replace(/[$,]/g,'')) + 15.75).toLocaleString('en-US',{style:'currency',currency:'USD'})
  await expect(page.getByTestId('monthly-expenses')).toHaveText(expected)
  await navigate(page,'Budgets')
  await expect(page.getByLabel('Food monthly limit',{exact:true})).toBeVisible()
  await navigate(page,'AI Assistant')
  await page.getByRole('button',{name:'How much did I spend this week?'}).click()
  await expect(page.locator('.chat-message.assistant')).toContainText('since Monday')
  await navigate(page,'AI Insights')
  await page.getByRole('button',{name:'Run scenario',exact:true}).click()
  await expect(page.getByTestId('scenario-difference')).toContainText('-$150.00')
  await navigate(page,'Student Deals')
  await expect(page.locator('.deal-card').first()).toBeVisible()
  await expect(page.locator('.sample-disclosure')).toContainText('synthetic examples')
  await page.locator('.deal-card').first().getByRole('button').click()
  await expect(page.getByRole('button',{name:/Saved \(1\)/})).toBeVisible()
  expect(consoleErrors).toEqual([])
})

test('CSV import, correction, deletion, and immediate budget update', async ({page}) => {
  await navigate(page,'Transactions')
  await page.getByRole('button',{name:'Import CSV',exact:true}).click()
  const file = Buffer.from('When,Details,Amount,Kind\n2026-10-09,Browser test cafe,-12.34,expense\n')
  await page.getByRole('dialog').locator('input[type=file]').setInputFiles({name:'sample.csv',mimeType:'text/csv',buffer:file})
  await expect(page.getByRole('dialog').getByText('1 rows found.',{exact:false})).toBeVisible()
  await page.getByRole('dialog').getByLabel('Description column').selectOption('Details')
  await page.getByRole('dialog').getByLabel('Date column').selectOption('When')
  await page.getByRole('button',{name:'Import transactions',exact:true}).click()
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await page.getByLabel('Search transactions').fill('Browser test cafe')
  await page.getByRole('button',{name:'Edit Browser test cafe',exact:true}).click()
  await page.getByRole('dialog').getByLabel('Category',{exact:true}).selectOption('food')
  await page.getByRole('button',{name:'Save changes',exact:true}).click()
  await expect(page.locator('.transactions-table')).toContainText('Food')
  page.once('dialog', dialog => dialog.accept())
  await page.getByRole('button',{name:'Delete Browser test cafe',exact:true}).click()
  await expect(page.getByText('No matching transactions',{exact:true})).toBeVisible()
})

test('all eight pages render and budget/profile changes persist', async ({page}) => {
  for (const name of ['Transactions','Budgets','AI Insights','Student Deals','Subscriptions','AI Assistant','Settings']) {
    await navigate(page,name)
    await expect(page.locator('h1')).toBeVisible()
    await expect(page.getByRole('alert')).toHaveCount(0)
  }
  await page.getByLabel('Name',{exact:true}).fill('Taylor Student')
  await page.getByRole('button',{name:'Save profile',exact:true}).click()
  await expect(page.locator('.toast')).toContainText('Profile saved')
  await page.reload()
  await expect(page.getByLabel('Name',{exact:true})).toHaveValue('Taylor Student')
  await navigate(page,'Budgets')
  await page.getByLabel('Food monthly limit',{exact:true}).fill('250')
  await page.locator('.budget-card').filter({has:page.getByLabel('Food monthly limit',{exact:true})}).getByRole('button',{name:'Save',exact:true}).click()
  await expect(page.locator('.toast')).toContainText('Food budget saved')
  await page.reload()
  await expect(page.getByLabel('Food monthly limit',{exact:true})).toHaveValue('250')
})

test('subscription review, export, data deletion, and demo reset', async ({page}) => {
  await navigate(page,'Subscriptions')
  await expect(page.locator('.subscription-row')).toHaveCount(3)
  await page.getByRole('button',{name:'Confirm Spotify premium',exact:true}).click()
  await expect(page.locator('.subscription-row').filter({hasText:'Spotify premium'})).toContainText('Confirmed')
  await page.getByRole('button',{name:'Mark Spotify premium incorrect',exact:true}).click()
  await expect(page.locator('.subscription-row').filter({hasText:'Spotify premium'})).toContainText('Excluded')
  await navigate(page,'Settings')
  const downloadPromise = page.waitForEvent('download')
  await page.getByRole('link',{name:'Export JSON',exact:true}).click()
  expect((await downloadPromise).suggestedFilename()).toBe('moniq-data.json')
  page.once('dialog', dialog => dialog.accept())
  await page.getByRole('button',{name:'Delete all data',exact:true}).click()
  await expect(page.getByText('Profile deleted',{exact:true})).toBeVisible()
  await page.reload()
  await expect(page.getByText('Profile deleted',{exact:true})).toBeVisible()
  page.once('dialog', dialog => dialog.accept())
  await page.getByRole('button',{name:'Reset Demo',exact:true}).click()
  await expect(page.getByLabel('Name',{exact:true})).toHaveValue('Alex Morgan')
})

test('mobile layout, navigation, keyboard dialog, and screenshot', async ({page}) => {
  await page.setViewportSize({width:390,height:844})
  await expect(page.getByTestId('balance')).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy()
  await page.screenshot({path:'../.runtime/mobile-overview.png',fullPage:true})
  await navigate(page,'AI Insights')
  await expect(page.getByRole('button',{name:'Run scenario',exact:true})).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy()
  await navigate(page,'Transactions')
  await page.getByRole('button',{name:'Add transaction',exact:true}).click()
  await expect(page.getByRole('dialog')).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await page.setViewportSize({width:1440,height:1000})
  await navigate(page,'Overview')
  await expect(page.locator('.recharts-pie')).toBeVisible()
  await page.screenshot({path:'../docs/moniq-overview.png',fullPage:true})
})

test('students can add and edit upcoming tuition or income schedules', async ({page}) => {
  await navigate(page,'AI Insights')
  await page.getByRole('button',{name:'Add schedule',exact:true}).click()
  const defaultDate = await page.getByLabel('Next due date',{exact:true}).inputValue()
  const today = new Intl.DateTimeFormat('en-CA',{timeZone:'America/New_York'}).format(new Date())
  expect(defaultDate > today).toBeTruthy()
  await page.getByLabel('Schedule merchant or source',{exact:true}).fill('One-time tuition demo')
  await page.getByLabel('Schedule amount ($)',{exact:true}).fill('120')
  const due = new Date(); due.setDate(due.getDate()+3)
  const day = due.toISOString().slice(0,10)
  await page.getByLabel('Next due date',{exact:true}).fill(day)
  await page.getByLabel('Repeat interval').selectOption('0')
  await page.getByRole('button',{name:'Save schedule',exact:true}).click()
  await expect(page.locator('.toast')).toContainText('Schedule saved')
  await expect(page.locator('.schedule-list').filter({has:page.getByRole('button',{name:'Edit One-time tuition demo schedule',exact:true})})).toContainText('$120.00')
  await page.getByRole('button',{name:'Edit One-time tuition demo schedule',exact:true}).click()
  await page.getByLabel('Schedule amount ($)',{exact:true}).fill('100')
  await page.getByRole('button',{name:'Save schedule',exact:true}).click()
  await expect(page.locator('.schedule-list').filter({has:page.getByRole('button',{name:'Edit One-time tuition demo schedule',exact:true})})).toContainText('$100.00')
  page.once('dialog', dialog => dialog.accept())
  await page.getByRole('button',{name:'Delete One-time tuition demo schedule',exact:true}).click()
  await expect(page.getByRole('button',{name:'Edit One-time tuition demo schedule',exact:true})).toHaveCount(0)
})
