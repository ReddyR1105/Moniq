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

test('Gmail settings and registered account balance updates preserve the synthetic demo', async ({page}) => {
  const demoBalance = await page.getByTestId('balance').innerText()
  await navigate(page,'Settings')
  await expect(page.getByRole('button',{name:'Connect Gmail',exact:true})).toBeDisabled()
  await expect(page.getByRole('button',{name:'Sync Now',exact:true})).toBeVisible()
  await expect(page.getByRole('button',{name:'Disconnect Gmail',exact:true})).toBeVisible()
  await page.getByRole('button',{name:'Open personal workspace',exact:true}).click()
  await expect(page.getByRole('button',{name:'Use synthetic demo',exact:true})).toBeVisible()
  const origin = {Origin:'http://127.0.0.1:5174'}
  expect((await page.request.delete('/api/data',{headers:origin})).status()).toBe(204)
  await page.reload()
  await page.getByLabel('Personal account name',{exact:true}).fill('Checking test account')
  await page.getByLabel('Account or card last four',{exact:true}).fill('1234')
  await page.getByLabel('Starting balance ($)',{exact:true}).fill('10')
  await page.getByRole('button',{name:'Register account',exact:true}).click()
  await expect(page.locator('.toast')).toContainText('Personal account saved')
  await navigate(page,'Overview')
  await expect(page.getByTestId('balance')).toHaveText('$10.00')
  for (const entry of [{description:'Campus job payroll',amount:'400',kind:'income',balance:'$410.00'}, {description:'Chick-fil-A',amount:'15',kind:'expense',balance:'$395.00'}]) {
    await page.getByRole('button',{name:'Add transaction',exact:true}).click()
    const dialog = page.getByRole('dialog')
    await dialog.getByLabel('Registered account',{exact:true}).selectOption({label:'Checking test account'})
    await dialog.getByLabel('Description',{exact:true}).fill(entry.description)
    await dialog.getByLabel('Amount ($)',{exact:true}).fill(entry.amount)
    await dialog.getByLabel('Transaction type',{exact:true}).selectOption(entry.kind)
    await dialog.getByRole('button',{name:'Confirm & save transaction',exact:true}).click()
    await expect(dialog).toHaveCount(0)
    await expect(page.getByTestId('balance')).toHaveText(entry.balance)
  }
  await expect(page.getByRole('button',{name:'Reset Demo',exact:true})).toHaveCount(0)
  await page.getByRole('button',{name:'Open synthetic demo',exact:true}).click()
  await expect(page.getByTestId('balance')).toHaveText(demoBalance)
})

test('connected Gmail controls review mocked alerts and update actual personal balances', async ({page}) => {
  let connected = false, synced = false, accountId = 0
  const reviewed = new Set<number>()
  const today = new Intl.DateTimeFormat('en-CA',{timeZone:'America/New_York'}).format(new Date())
  const alerts = [
    {id:901,subject:'Synthetic confirmed paycheck',event_type:'income',merchant:'Campus job payroll',amount:400,category:'income'},
    {id:902,subject:'Synthetic purchase alert',event_type:'purchase',merchant:'Chick-fil-A',amount:15,category:'food'},
  ]
  await page.route('**/api/gmail/**',async route => {
    const url = new URL(route.request().url())
    const path = url.pathname
    if (path === '/api/gmail/status') return route.fulfill({json:{configured:true,connected,tokens_present:connected,connection_error:null,email:connected?'synthetic@example.test':null,scope:'https://www.googleapis.com/auth/gmail.readonly'}})
    if (path === '/api/gmail/connect') {connected=true; return route.fulfill({json:{authorization_url:'http://127.0.0.1:5174/?gmail=connected#settings'}})}
    if (path === '/api/gmail/sync') {synced=true; return route.fulfill({json:{queued:2,more_available:false}})}
    if (path === '/api/gmail/items') return route.fulfill({json:synced?alerts.map(a=>({...a,sender:'Synthetic Bank <alerts@example.test>',date:today,last_four:'1234',confidence:.95,reasons:[],account_id:accountId,status:reviewed.has(a.id)?'confirmed':'review'})):[]})
    if (path.endsWith('/confirm')) {
      const payload = route.request().postDataJSON()
      expect(payload.posted_confirmed).toBe(true)
      expect(payload.account_id).toBe(accountId)
      const saved = await page.request.post('/api/transactions',{headers:{Origin:'http://127.0.0.1:5174'},data:payload})
      expect(saved.status()).toBe(201)
      reviewed.add(Number(path.split('/')[4]))
      return route.fulfill({json:{status:'confirmed',transaction:await saved.json()}})
    }
    if (path === '/api/gmail/disconnect') {connected=false; return route.fulfill({json:{connected:false,message:'Local tokens removed. Confirmed records remain.'}})}
    return route.continue()
  })
  await navigate(page,'Settings')
  await page.getByRole('button',{name:'Open personal workspace',exact:true}).click()
  await expect(page.getByRole('button',{name:'Use synthetic demo',exact:true})).toBeVisible()
  expect((await page.request.delete('/api/data',{headers:{Origin:'http://127.0.0.1:5174'}})).status()).toBe(204)
  await page.reload()
  await page.getByLabel('Personal account name',{exact:true}).fill('Gmail checking test')
  await page.getByLabel('Account or card last four',{exact:true}).fill('1234')
  await page.getByRole('button',{name:'Register account',exact:true}).click()
  await expect(page.locator('.toast')).toContainText('Personal account saved')
  accountId = (await (await page.request.get('/api/gmail/accounts')).json()).find((a:{name:string})=>a.name==='Gmail checking test').id
  await page.getByRole('button',{name:'Connect Gmail',exact:true}).click()
  await expect(page.getByRole('button',{name:'Reconnect Gmail',exact:true})).toBeEnabled()
  await page.getByRole('button',{name:'Sync Now',exact:true}).click()
  await expect(page.locator('.gmail-review')).toHaveCount(2)
  expect((await (await page.request.get('/api/dashboard')).json()).balance).toBe(10)
  for (const [subject,balance] of [['Synthetic confirmed paycheck',410],['Synthetic purchase alert',395]] as const) {
    const item = page.locator('.gmail-review').filter({has:page.getByRole('heading',{name:subject,exact:true})})
    await expect(item.getByRole('button',{name:'Confirm email transaction',exact:true})).toBeDisabled()
    await item.getByRole('checkbox').check()
    await item.getByRole('button',{name:'Confirm email transaction',exact:true}).click()
    await expect(item).toHaveCount(0)
    expect((await (await page.request.get('/api/dashboard')).json()).balance).toBe(balance)
  }
  await page.getByRole('button',{name:'Disconnect Gmail',exact:true}).click()
  await expect(page.getByRole('button',{name:'Sync Now',exact:true})).toBeDisabled()
  expect((await (await page.request.get('/api/dashboard')).json()).balance).toBe(395)
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
  // Calendar-aligned charges in the rolling demo seed can have only two occurrences.
  // Supply a complete recurring history for this review instead of assuming three seed candidates.
  const merchant = 'Browser review subscription'
  const { as_of } = await (await page.request.get('/api/dashboard')).json()
  const [year, month] = (as_of as string).split('-').map(Number)
  for (const offset of [3, 2, 1]) {
    const date = new Date(Date.UTC(year, month - 1 - offset, 1)).toISOString().slice(0, 10)
    const response = await page.request.post('/api/transactions', { data: {
      date, merchant, description: merchant, amount: '5.99', kind: 'expense', category: 'subscriptions', account_id: 1,
    } })
    expect(response.status()).toBe(201)
  }
  await navigate(page,'Subscriptions')
  const detected = await (await page.request.get('/api/subscriptions')).json()
  expect(detected.items).toEqual(expect.arrayContaining([
    expect.objectContaining({merchant, evidence_count: 3, status: 'candidate'}),
  ]))
  await expect(page.locator('.subscription-row')).toHaveCount(detected.items.length)
  await page.getByRole('button',{name:`Confirm ${merchant}`,exact:true}).click()
  await expect(page.locator('.subscription-row').filter({hasText:merchant})).toContainText('Confirmed')
  await page.getByRole('button',{name:`Mark ${merchant} incorrect`,exact:true}).click()
  await expect(page.locator('.subscription-row').filter({hasText:merchant})).toContainText('Excluded')
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
  await page.screenshot({path:'../.runtime/verification-overview.png',fullPage:true})
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
