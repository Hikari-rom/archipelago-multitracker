import { describe, expect, it } from 'vitest'
import { BEFORE_TRACKING, category, dayLabel, groupByDay } from '../../src/v2/lib/days'

// local time: build timestamps from Date parts so the test does not depend on the timezone
const at = (y: number, mo: number, d: number, h: number, mi: number) => new Date(y, mo, d, h, mi).getTime() / 1000
const NOW = new Date(2026, 9, 15, 0, 30).getTime()

describe('days', () => {
  it('labels', () => {
    expect(dayLabel(at(2026, 9, 15, 0, 6), NOW)).toBe("Aujourd'hui")
    expect(dayLabel(at(2026, 9, 14, 23, 58), NOW)).toBe('Hier')
    expect(dayLabel(at(2026, 9, 3, 12, 0), NOW)).toBe('3 oct.')
    expect(dayLabel(at(2025, 11, 31, 12, 0), NOW)).toBe('31 déc. 2025')
  })
  it('groups newest first, untimed entries last, source shown once per run', () => {
    type E = { t: number | null; src: string }
    const es: E[] = [
      { t: at(2026, 9, 15, 0, 6), src: 'Slay the Spire' },
      { t: at(2026, 9, 14, 23, 58), src: 'Jak' },
      { t: at(2026, 9, 14, 23, 55), src: 'Jak' },
      { t: at(2026, 9, 14, 23, 15), src: 'Celeste' },
      { t: null, src: 'Celeste' },
      { t: null, src: 'Celeste' },
    ]
    const g = groupByDay(es, (e) => e.t, (e) => e.src, NOW)
    expect(g.map((d) => [d.label, d.rows.length])).toEqual([["Aujourd'hui", 1], ['Hier', 3], [BEFORE_TRACKING, 2]])
    expect(g[1].rows.map((r) => r.showSource)).toEqual([true, false, true])
    expect(g[2].rows.map((r) => r.showSource)).toEqual([true, false])
  })
  it('untimed entries in the middle still go to the last group', () => {
    const g = groupByDay([{ t: null }, { t: at(2026, 9, 15, 0, 1) }], (e) => e.t, () => 'x', NOW)
    expect(g.map((d) => d.label)).toEqual(["Aujourd'hui", BEFORE_TRACKING])
  })
  it('category', () => {
    expect(category({ progression: true, useful: false, trap: false })).toBe('PROG')
    expect(category({ progression: false, useful: true, trap: false })).toBe('UTILE')
    expect(category({ progression: true, useful: false, trap: true })).toBe('PIÈGE')
    expect(category({ progression: false, useful: false, trap: false })).toBeNull()
  })
})
