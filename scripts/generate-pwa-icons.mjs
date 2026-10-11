// Rasterize Moniq's existing vector identity; no external image assets.
import { createRequire } from 'node:module'
import { readFile, mkdir, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const require = createRequire(path.join(root, 'frontend', 'package.json'))
const { chromium } = require('playwright')
const source = await readFile(path.join(root, 'frontend/public/icon.svg'), 'utf8')
const out = path.join(root, 'frontend/public/icons')
await mkdir(out, { recursive: true })
const browser = await chromium.launch()
try {
  const page = await browser.newPage()
  for (const [name, size, maskable] of [['icon-192', 192, false], ['icon-512', 512, false], ['icon-maskable-512', 512, true], ['apple-touch-icon', 180, false]]) {
    const base64 = await page.evaluate(async ({ source, size, maskable }) => {
      const canvas = document.createElement('canvas'); canvas.width = canvas.height = size
      const context = canvas.getContext('2d'); context.fillStyle = '#136c53'; context.fillRect(0, 0, size, size)
      const img = new Image(); img.src = `data:image/svg+xml;base64,${btoa(source)}`; await img.decode()
      const padding = maskable ? size * .18 : 0
      context.drawImage(img, padding, padding, size - 2 * padding, size - 2 * padding)
      return canvas.toDataURL('image/png').split(',')[1]
    }, { source, size, maskable })
    await writeFile(path.join(out, `${name}.png`), Buffer.from(base64, 'base64'))
  }
} finally { await browser.close() }
console.log('Generated four Moniq PNG icons from the existing SVG.')
