import { describe, expect, it } from 'vitest'
import { applyPreset, INFO_KEYS, joinShown, normalizeShown, PRESETS, presetOf, toggleInfo } from '../../src/v2/lib/display'

describe('display presets', () => {
  it('match the spec table', () => {
    expect(PRESETS.essentiel).toEqual(['newItems', 'hints', 'goal'])
    expect(PRESETS.standard).toEqual(['done', 'newItems', 'hints', 'regions', 'goal', 'progress', 'recent'])
    expect(PRESETS.complet).toEqual(INFO_KEYS)
    expect(INFO_KEYS).toHaveLength(11)
  })
  it('applyPreset returns a copy', () => {
    const p = applyPreset('essentiel')
    expect(p).toEqual({ preset: 'essentiel', shown: ['newItems', 'hints', 'goal'] })
    p.shown.push('slot')
    expect(PRESETS.essentiel).toHaveLength(3)
  })
  it('presetOf ignores order and names custom sets', () => {
    expect(presetOf(['goal', 'newItems', 'hints'])).toBe('essentiel')
    expect(presetOf(['goal'])).toBe('custom')
    expect(presetOf([])).toBe('custom')
  })
  it('normalizeShown drops unknown keys and duplicates, keeps the INFO_KEYS order', () => {
    expect(normalizeShown(['goal', 'nope', 'slot', 'goal', 3])).toEqual(['slot', 'goal'])
  })
})

describe('toggleInfo', () => {
  it('leaving a preset makes it custom, coming back names it again', () => {
    const off = toggleInfo(applyPreset('essentiel'), 'hints', false)
    expect(off).toEqual({ preset: 'custom', shown: ['newItems', 'goal'] })
    expect(toggleInfo(off, 'hints', true)).toEqual(applyPreset('essentiel'))
  })
  it('reaches another preset', () => {
    let p = applyPreset('essentiel')
    for (const k of ['done', 'regions', 'progress', 'recent'] as const) p = toggleInfo(p, k, true)
    expect(p.preset).toBe('standard')
  })
  it('is idempotent', () => {
    expect(toggleInfo(applyPreset('complet'), 'slot', true)).toEqual(applyPreset('complet'))
  })
})

describe('joinShown', () => {
  it('joins the shown parts with a middle dot', () => {
    expect(joinShown(['checks en logique', 'romain_tww', '4 / 10 faits'])).toBe('checks en logique · romain_tww · 4 / 10 faits')
    expect(joinShown(['checks en logique', false, null, undefined, ''])).toBe('checks en logique')
    expect(joinShown([false, false])).toBe('')
  })
})
