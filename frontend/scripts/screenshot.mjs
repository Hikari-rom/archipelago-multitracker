// Screenshots of the v1 of a running instance (default http://127.0.0.1:42753, page /v1) at mobile and desktop sizes,
// light and dark. Usage: node scripts/screenshot.mjs [url] [outDir]
// Uses the system Chromium (/usr/bin/chromium) when Playwright's own browser is not installed.
import { chromium } from '@playwright/test'
import { existsSync, mkdirSync } from 'node:fs'

const url = process.argv[2] ?? 'http://127.0.0.1:42753'
const out = process.argv[3] ?? '../test-output/screenshots/live'
mkdirSync(out, { recursive: true })
const executablePath = ['/usr/bin/chromium', '/usr/bin/chromium-browser'].find((p) => existsSync(p))
const browser = await chromium.launch(executablePath ? { executablePath } : {})
for (const [name, viewport] of [['mobile', { width: 390, height: 844 }], ['desktop', { width: 1280, height: 900 }]]) {
  for (const scheme of ['light', 'dark']) {
    const page = await browser.newPage({ viewport, colorScheme: scheme })
    await page.goto(`${url}/v1`, { waitUntil: 'networkidle' })
    await page.waitForTimeout(1500)
    await page.screenshot({ path: `${out}/${name}-${scheme}.png`, fullPage: true })
    const details = page.getByRole('button', { name: /Voir les détails/ }).first()
    if (await details.count()) {
      await details.click()
      await page.waitForTimeout(1500)
      await page.screenshot({ path: `${out}/${name}-${scheme}-detail.png`, fullPage: true })
    }
    await page.close()
    const cfgPage = await browser.newPage({ viewport, colorScheme: scheme })
    await cfgPage.goto(`${url}/v1#config`, { waitUntil: 'networkidle' })
    await cfgPage.waitForTimeout(1000)
    await cfgPage.screenshot({ path: `${out}/${name}-${scheme}-config.png`, fullPage: true })
    await cfgPage.close()
  }
}
await browser.close()
console.log(`screenshots in ${out}`)
