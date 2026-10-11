import { defineConfig } from '@playwright/test'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const recording = process.env.MONIQ_RECORD_DEMO === '1'
const browserChannel = process.env.MONIQ_BROWSER || (process.platform === 'win32' && !process.env.CI ? 'msedge' : 'chromium')
export default defineConfig({
  testDir: './e2e',
  testIgnore: '**/hosted.spec.ts',
  fullyParallel: false,
  workers: 1,
  timeout: 60000,
  reporter: [['list'], ['json', {outputFile: '../.runtime/browser-results.json'}]],
  use: { baseURL: 'http://127.0.0.1:5174',
    channel: browserChannel === 'chromium' ? undefined : browserChannel,
    headless: true, trace: 'retain-on-failure', screenshot: 'only-on-failure',
    viewport: {width:1440,height:1000},
    video: recording ? {mode:'on',size:{width:1440,height:1000}} : 'off',
  },
  webServer: [
    {command: `${process.platform === 'win32' ? '.venv\\Scripts\\python.exe' : '.venv/bin/python'} -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8001`,
      cwd: root, url: 'http://127.0.0.1:8001/api/health', reuseExistingServer: false, timeout:60000,
      env: {MONIQ_GMAIL_DISABLED:'true',SCENARIO_DATABASE_URL:'sqlite:///./.runtime/browser-upgrade.db',DATABASE_URL: 'sqlite:///./.runtime/browser.db', PERSONAL_DATABASE_URL:'sqlite:///./.runtime/browser-personal.db', GMAIL_TOKEN_DIR:'./.runtime/browser-gmail', PERSONAL_MODEL_DIR:'./.runtime/browser-personal-models', MODEL_DIR: './.runtime/browser-models', CORS_ORIGINS:'http://127.0.0.1:5174', GMAIL_CLIENT_ID:'', GMAIL_CLIENT_SECRET:'', GMAIL_TOKEN_ENCRYPTION_KEY:''}},
    {command: 'npm run dev -- --port 5174', url:'http://127.0.0.1:5174', reuseExistingServer:false, timeout:60000,
      env: {MONIQ_API_TARGET:'http://127.0.0.1:8001'}},
  ],
})
