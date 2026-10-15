// Screenshots of the v2 at /v2 (run against the mock dev server: VITE_MOCK=1 npx vite --port 38290).
// Usage: node scripts/screenshot-v2.mjs [baseUrl] [outDir]
import { chromium } from '@playwright/test'
import { existsSync, mkdirSync } from 'node:fs'

const base = process.argv[2] ?? 'http://127.0.0.1:38290'
const out = process.argv[3] ?? '../test-output/screenshots/v2'
mkdirSync(out, { recursive: true })
const executablePath = ['/usr/bin/chromium', '/usr/bin/chromium-browser'].find((p) => existsSync(p))
const browser = await chromium.launch(executablePath ? { executablePath } : {})
const shots = [
  ['dashboard-cards', '/v2', { 'amt-v2-layout': 'cards' }],
  ['dashboard-focus', '/v2', { 'amt-v2-layout': 'focus' }],
  ['history', '/v2#history', {}],
  ['goals', '/v2#goals', {}],
]
for (const [device, viewport] of [['desktop', { width: 1440, height: 900 }], ['phone', { width: 390, height: 844 }]]) {
  for (const theme of ['nuit', 'plan']) {
    for (const [name, path, prefs] of shots) {
      const ctx = await browser.newContext({ viewport, reducedMotion: 'reduce' })
      await ctx.addInitScript((p) => { for (const [k, v] of Object.entries(p)) localStorage.setItem(k, v) }, { 'amt-v2-theme': theme, ...prefs })
      const page = await ctx.newPage()
      await page.goto(base + path, { waitUntil: 'networkidle' })
      await page.waitForTimeout(1200)
      await page.screenshot({ path: `${out}/${device}-${theme}-${name}.png`, fullPage: true })
      await ctx.close()
    }
  }
}
await browser.close()
console.log(`screenshots in ${out}`)
