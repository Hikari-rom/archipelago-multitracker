import { describe, expect, it } from 'vitest'
import { formatWhen, historyItems } from '../src/lib/history'
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
})
