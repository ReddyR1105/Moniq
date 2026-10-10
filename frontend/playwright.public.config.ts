import { defineConfig } from '@playwright/test'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
export default defineConfig({
  testDir: './e2e', testMatch: 'public-demo.spec.ts', outputDir:'../.runtime/public-test-results', workers: 1, timeout: 60000,
  reporter: [['list'], ['json', {outputFile: '../.runtime/public-browser-results.json'}]],
  use: {baseURL: 'http://127.0.0.1:8003', headless: true, viewport: {width:1440,height:1000},
    screenshot: 'only-on-failure', trace: 'retain-on-failure'},
  webServer: {command: `${process.platform === 'win32' ? '.venv\\Scripts\\python.exe' : '.venv/bin/python'} -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8003`,
    cwd: root, url: 'http://127.0.0.1:8003/api/health', reuseExistingServer: false, timeout:60000,
    env: {MONIQ_PUBLIC_DEMO:'true', MONIQ_SERVE_FRONTEND:'true', MONIQ_COOKIE_SECURE:'false', MONIQ_PUBLIC_ORIGIN:'http://127.0.0.1:8003'}},
})
