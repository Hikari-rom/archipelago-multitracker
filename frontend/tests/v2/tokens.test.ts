import { describe, expect, it } from 'vitest'
import { applyV2Theme, CARD_OPAQUE, resolveTheme, TOKENS, type ResolvedTheme } from '../../src/v2/lib/tokens'

function rgb(c: string, over?: number[]): number[] {
  const hex = /^#([0-9a-f]{6})$/i.exec(c)
  if (hex) return [0, 2, 4].map((i) => parseInt(hex[1].slice(i, i + 2), 16))
  const m = /^rgba\((\d+),\s*(\d+),\s*(\d+),\s*([\d.]+)\)$/.exec(c)
  if (!m || !over) throw new Error('unparsable colour ' + c)
  const a = Number(m[4])
  return [1, 2, 3].map((i, k) => Math.round(Number(m[i]) * a + over[k] * (1 - a)))
}
const lum = (c: number[]) => {
  const v = c.map((x) => {
    x /= 255
    return x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4
  })
  return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]
}
const ratio = (a: number[], b: number[]) => {
  const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p)
  return (x + 0.05) / (y + 0.05)
}

describe('v2 tokens', () => {
  for (const theme of ['nuit', 'plan'] as ResolvedTheme[]) {
    const t = TOKENS[theme]
    const card = rgb(CARD_OPAQUE[theme])
    it(`${theme}: text tokens reach AA on the card`, () => {
      for (const k of ['foreground', 'muted-foreground', 'logic', 'done', 'hint', 'new', 'error', 'primary'] as const)
        expect(ratio(rgb(t[k]), card), k).toBeGreaterThanOrEqual(4.5)
    })
    it(`${theme}: tinted badges reach AA`, () => {
      for (const [fg, bg] of [['good-foreground', 'good'], ['warn-foreground', 'warn'], ['info-foreground', 'info']] as const)
        expect(ratio(rgb(t[fg]), rgb(t[bg], card)), fg).toBeGreaterThanOrEqual(4.5)
      expect(ratio(rgb(t['primary-foreground']), rgb(t.primary)), 'primary button').toBeGreaterThanOrEqual(4.5)
    })
  }
  it('resolves auto from the system', () => {
    expect(resolveTheme('auto', true)).toBe('nuit')
    expect(resolveTheme('auto', false)).toBe('plan')
    expect(resolveTheme('plan', true)).toBe('plan')
    expect(resolveTheme('nuit', false)).toBe('nuit')
  })
  it('applies variables and the v1 dark flag', () => {
    const el = document.createElement('html')
    applyV2Theme('nuit', el)
    expect(el.dataset.v2).toBe('nuit')
    expect(el.dataset.theme).toBe('dark')
    expect(el.style.getPropertyValue('--logic')).toBe(TOKENS.nuit.logic)
    applyV2Theme('plan', el)
    expect(el.dataset.theme).toBe('light')
    expect(el.style.getPropertyValue('--logic')).toBe(TOKENS.plan.logic)
  })
})
