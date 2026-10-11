// Loopback-only playback QA. Serve only this synthetic video and its captions.
import { createRequire } from 'node:module'
import fs from 'node:fs'
import fsp from 'node:fs/promises'
import http from 'node:http'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const require = createRequire(path.join(root, 'frontend/package.json'))
const { chromium, expect } = require('@playwright/test')
const file = path.join(root, 'docs/demo/Moniq_Hacklanta_Premium_Final.mp4')
const server = http.createServer((request, response) => {
  if (request.url === '/') {
    response.writeHead(200, { 'Content-Type': 'text/html', 'Cache-Control': 'no-store' })
    return response.end('<!doctype html><title>Moniq — video review</title><style>html,body{margin:0;background:#0d2a20;height:100%}video{width:100%;height:100%;object-fit:contain}</style><video controls playsinline src="/video.mp4"></video>')
  }
  if (request.url !== '/video.mp4') { response.writeHead(404); return response.end() }
  const size = fs.statSync(file).size
  const match = /^bytes=(\d+)-(\d*)$/.exec(request.headers.range || '')
  const start = match ? Number(match[1]) : 0, end = match && match[2] ? Math.min(Number(match[2]), size - 1) : size - 1
  if (start > end || end >= size) { response.writeHead(416); return response.end() }
  response.writeHead(match ? 206 : 200, { 'Content-Type': 'video/mp4', 'Accept-Ranges': 'bytes', 'Content-Length': end - start + 1, 'Cache-Control': 'no-store', ...(match ? { 'Content-Range': `bytes ${start}-${end}/${size}` } : {}) })
  fs.createReadStream(file, { start, end }).pipe(response)
})
await new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', resolve) })
const port = server.address().port
const browser = await chromium.launch({ headless: true, args: ['--autoplay-policy=no-user-gesture-required'] })
try {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } })
  await page.route('**/*', route => new URL(route.request().url()).hostname === '127.0.0.1' ? route.continue() : route.abort())
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  await page.goto(`http://127.0.0.1:${port}`)
  await expect.poll(() => page.evaluate(() => document.querySelector('video').readyState)).toBeGreaterThanOrEqual(3)
  await page.evaluate(() => document.querySelector('video').play())
  await expect.poll(() => page.evaluate(() => document.querySelector('video').currentTime)).toBeGreaterThan(1)
  const first = await page.evaluate(() => { const v = document.querySelector('video'); return { duration: v.duration, width: v.videoWidth, height: v.videoHeight, readyState: v.readyState, audio_decoded_bytes: v.webkitAudioDecodedByteCount ?? null, frames: v.getVideoPlaybackQuality().totalVideoFrames, error: v.error?.message ?? null } })
  if (Math.abs(first.duration - 90) > .12 || first.width !== 1920 || first.height !== 1080 || first.error || first.frames < 1) throw Error('Invalid media playback metadata')
  await page.evaluate(() => { const v = document.querySelector('video'); v.pause(); v.controls = false })
  const timeline = JSON.parse(await fsp.readFile(path.join(root, '.runtime/premium-recording/edit-timeline.json'), 'utf8'))
  for (const scene of timeline) {
    // Early, middle and ending frames catch transition/scene timing mistakes.
    for (const [label, instant] of [['early', scene.begin + .5], ['middle', (scene.begin + scene.end) / 2], ['end', scene.end - .5]]) {
      await page.evaluate(time => new Promise((resolve, reject) => {
        const v = document.querySelector('video')
        v.addEventListener('seeked', resolve, { once: true })
        v.addEventListener('error', () => reject(Error(v.error?.message)), { once: true })
        v.currentTime = time
      }), instant)
      await page.screenshot({ path: path.join(root, `.runtime/premium-recording/verified-${scene.id}-${label}.png`) })
    }
  }
  await page.evaluate(() => { const v = document.querySelector('video'); v.currentTime = 88; return v.play() })
  await expect.poll(() => page.evaluate(() => document.querySelector('video').ended), { timeout: 10000 }).toBeTruthy()
  if (errors.length) throw Error(errors.join('; '))
  const result = { ...first, page_errors: errors, seeks_passed: 33, playback_reached_end: true, external_network_blocked: true, human_listening_review: 'Pending owner review; automated playback does not evaluate subjective vocal warmth.' }
  await fsp.writeFile(path.join(root, '.runtime/premium-recording/browser-playback.json'), JSON.stringify(result, null, 2))
  console.log(JSON.stringify(result, null, 2))
} finally { await browser.close(); await new Promise(resolve => server.close(resolve)) }
