import { afterEach, describe, expect, it, vi } from 'vitest'
import * as p from '../../src/v2/lib/prefs'
import { INFO_KEYS } from '../../src/v2/lib/display'

afterEach(() => {
  localStorage.clear()
  vi.restoreAllMocks()
})

describe('v2 prefs', () => {
  it('defaults', () => {
    expect(p.loadLayout()).toBe('cards')
    expect(p.loadSort()).toBe('auto')
    expect(p.loadHideDone()).toBe(false)
    expect(p.loadThemeChoice()).toBe('nuit')
    expect(p.loadSkyAnimated()).toBe(true)
    expect(p.loadHideReached()).toBe(false)
    expect(p.loadTicker()).toBe('off')
  })
  it('round-trips and uses v2 keys only', () => {
    p.saveLayout('focus')
    p.saveSort('percent')
    p.saveHideDone(true)
    p.saveThemeChoice('plan')
    p.saveSkyAnimated(false)
    p.saveHideReached(true)
    p.saveTicker('ruban')
    expect(p.loadLayout()).toBe('focus')
    expect(p.loadSort()).toBe('percent')
    expect(p.loadHideDone()).toBe(true)
    expect(p.loadThemeChoice()).toBe('plan')
    expect(p.loadSkyAnimated()).toBe(false)
    expect(p.loadHideReached()).toBe(true)
    expect(p.loadTicker()).toBe('ruban')
    expect(Object.keys(localStorage).every((k) => k.startsWith('amt-v2-'))).toBe(true)
  })
  it('ignores invalid values and storage errors', () => {
    localStorage.setItem('amt-v2-layout', 'compact')
    localStorage.setItem('amt-v2-theme', 'dark')
    expect(p.loadLayout()).toBe('cards')
    expect(p.loadThemeChoice()).toBe('nuit')
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    expect(p.loadSort()).toBe('auto')
    expect(() => p.saveSort('count')).not.toThrow()
  })
  it('display: Complet by default, round-trips a custom set', () => {
    expect(p.loadDisplay()).toEqual({ preset: 'complet', shown: [...INFO_KEYS] })
    p.saveDisplay({ preset: 'custom', shown: ['slot', 'goal'] })
    expect(p.loadDisplay()).toEqual({ preset: 'custom', shown: ['slot', 'goal'] })
    expect(localStorage.getItem('amt-v2-display')).not.toBeNull()
  })
  it('display: a named preset is rebuilt from the preset, not from the stored list', () => {
    localStorage.setItem('amt-v2-display', JSON.stringify({ preset: 'essentiel', shown: ['slot'] }))
    expect(p.loadDisplay()).toEqual({ preset: 'essentiel', shown: ['newItems', 'hints', 'goal'] })
  })
  it('display: custom sets are cleaned and recognised', () => {
    localStorage.setItem('amt-v2-display', JSON.stringify({ preset: 'custom', shown: ['goal', 'nope', 'goal', 'slot'] }))
    expect(p.loadDisplay()).toEqual({ preset: 'custom', shown: ['slot', 'goal'] })
    localStorage.setItem('amt-v2-display', JSON.stringify({ preset: 'custom', shown: ['goal', 'hints', 'newItems'] }))
    expect(p.loadDisplay().preset).toBe('essentiel')
  })
  it('display: garbage and blocked storage give Complet', () => {
    for (const v of ['{', '"x"', 'null', '{"preset":"custom","shown":"slot"}', '{"preset":"dense"}']) {
      localStorage.setItem('amt-v2-display', v)
      expect(p.loadDisplay().preset).toBe('complet')
    }
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    expect(p.loadDisplay().preset).toBe('complet')
    expect(() => p.saveDisplay({ preset: 'custom', shown: [] })).not.toThrow()
  })
})
