import { defineConfig } from '@playwright/test'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..')
export default defineConfig({
  testDir:'./e2e',testMatch:'hosted.spec.ts',workers:1,timeout:60000,outputDir:'../.runtime/hosted-test-results',
  reporter:[['list'],['json',{outputFile:'../.runtime/hosted-browser-results.json'}]],
  use:{baseURL:'https://127.0.0.1:8005',ignoreHTTPSErrors:true,headless:true,viewport:{width:1440,height:1000},trace:'retain-on-failure',screenshot:'only-on-failure'},
  webServer:{command:`${process.platform==='win32'?'.venv\\Scripts\\python.exe':'.venv/bin/python'} scripts/serve-hosted-test.py`,cwd:root,
    url:'https://127.0.0.1:8005/api/health',ignoreHTTPSErrors:true,reuseExistingServer:false,timeout:60000,
    env:{MONIQ_SYNTHETIC_TEST_SERVER:'1',MONIQ_HOSTED_APP:'true'}},
})
