import { describe, expect, it } from 'vitest'
import { clockOffset, formatReceived, formatWhen, historyItems, loadActiveMinutes, receivedTitle, saveActiveMinutes } from '../src/lib/history'
import type { ItemEntry } from '../src/lib/types'

const item = (index: number, p: Partial<ItemEntry> = {}): ItemEntry => ({
  index, name: `I${index}`, sender: 'S', own: false, location: 'L', progression: false, useful: false, trap: false,
  new: false, received_at: null, ...p,
})

describe('history', () => {
  it('newest first and filters', () => {
    const items = [item(0), item(1, { progression: true, received_at: 10 }), item(2, { useful: true, received_at: 20 })]
    expect(historyItems(items, 'all').map((i) => i.index)).toEqual([2, 1, 0])
    expect(historyItems(items, 'progression').map((i) => i.index)).toEqual([1])
    expect(historyItems(items, 'useful').map((i) => i.index)).toEqual([2])
  })
  it('formats times', () => {
    const now = new Date(2026, 9, 11, 14, 30).getTime()
    const at = (d: Date) => d.getTime() / 1000
    expect(formatWhen(null, now)).toBe('avant le suivi')
    expect(formatWhen(now / 1000 - 20, now)).toBe("à l'instant")
    expect(formatWhen(now / 1000 - 12 * 60, now)).toBe('il y a 12 min')
    expect(formatWhen(at(new Date(2026, 9, 11, 9, 5)), now)).toBe("aujourd'hui 09:05")
    expect(formatWhen(at(new Date(2026, 9, 10, 21, 14)), now)).toBe('hier 21:14')
    expect(formatWhen(at(new Date(2026, 9, 3, 9, 30)), now)).toBe('3 oct. 09:30')
  })
  it('edge cases: clock ahead, hour boundary', () => {
    const now = new Date(2026, 9, 11, 14, 30).getTime()
    expect(formatWhen(now / 1000 + 90, now)).toBe("à l'instant") // server clock ahead of this device
    expect(formatWhen(now / 1000 - 59 * 60, now)).toBe('il y a 59 min')
    expect(formatWhen(now / 1000 - 60 * 60, now)).toBe("aujourd'hui 13:30")
  })
  it('items received while the app was away show a range', () => {
    const now = new Date(2026, 9, 11, 14, 30).getTime()
    const at = new Date(2026, 9, 11, 8, 0).getTime() / 1000
    const after = new Date(2026, 9, 10, 22, 15).getTime() / 1000
    expect(formatReceived({ received_at: at, received_after: after }, now)).toBe("hier 22:15 → aujourd'hui 08:00")
    expect(formatReceived({ received_at: at, received_after: null }, now)).toBe("aujourd'hui 08:00")
    expect(receivedTitle({ received_at: null })).toMatch(/avant que l'app suive/)
    expect(receivedTitle({ received_at: at, received_after: after })).toMatch(/ne suivait pas/)
    expect(receivedTitle({ received_at: at })).toBe('')
  })
  it('server clock offset and active-minutes setting', () => {
    expect(clockOffset(1000, 990_000)).toBe(10_000)
    expect(clockOffset(undefined, 5)).toBe(0)
    expect(clockOffset(Number.NaN, 5)).toBe(0)
    localStorage.setItem('amt-active-minutes', 'abc')
    expect(loadActiveMinutes()).toBe(30)
    saveActiveMinutes(60)
    expect(loadActiveMinutes()).toBe(60)
    localStorage.setItem('amt-active-minutes', '45')
    expect(loadActiveMinutes()).toBe(30)
  })
})
