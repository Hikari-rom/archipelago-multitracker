import { afterEach, describe, expect, it, vi } from 'vitest'
import * as p from '../../src/v2/lib/prefs'

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
  })
  it('round-trips and uses v2 keys only', () => {
    p.saveLayout('focus')
    p.saveSort('percent')
    p.saveHideDone(true)
    p.saveThemeChoice('plan')
    p.saveSkyAnimated(false)
    p.saveHideReached(true)
    expect(p.loadLayout()).toBe('focus')
    expect(p.loadSort()).toBe('percent')
    expect(p.loadHideDone()).toBe(true)
    expect(p.loadThemeChoice()).toBe('plan')
    expect(p.loadSkyAnimated()).toBe(false)
    expect(p.loadHideReached()).toBe(true)
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
})
