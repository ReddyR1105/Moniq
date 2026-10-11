import { defineConfig } from '@playwright/test'
import local from './playwright.public.config'

const supplied = process.env.MONIQ_PUBLIC_BASE_URL
if (!supplied) throw new Error('Set MONIQ_PUBLIC_BASE_URL to the approved, deployed HTTPS Moniq origin.')
const origin = new URL(supplied)
if (origin.protocol !== 'https:' || origin.username || origin.password || origin.pathname !== '/' || origin.search || origin.hash) {
  throw new Error('The deployed verification URL must be a credential-free HTTPS origin.')
}

export default defineConfig({
  ...local,
  use: { ...local.use, baseURL: origin.origin },
  webServer: undefined,
  reporter: [['list'], ['json', { outputFile: '../.runtime/deployed-browser-results.json' }]],
  outputDir: '../.runtime/deployed-test-results',
})
