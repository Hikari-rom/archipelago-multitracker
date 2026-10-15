import { describe, expect, it } from 'vitest'
import { OTHER_REGION, regionsOf } from '../../src/v2/lib/regions'
import type { LogicLocation } from '../../src/lib/types'

const L = (id: number, region: string | null, hint = false): LogicLocation => ({
  id, name: `loc ${id}`, region, hint: hint ? { item: 'Hookshot', receiver: 'kuro', progression: true } : null,
})

describe('regionsOf', () => {
  it('groups by region, biggest first, hinted locations first inside', () => {
    const r = regionsOf([L(1, 'Great Sea'), L(2, 'Windfall'), L(3, 'Windfall', true), L(4, null), L(5, 'Windfall')])
    expect(r.map((g) => [g.name, g.count, g.hinted])).toEqual([['Windfall', 3, 1], ['Great Sea', 1, 0], [OTHER_REGION, 1, 0]])
    expect(r[0].locations.map((l) => l.id)).toEqual([3, 2, 5])
  })
  it('ties: hinted regions first, then name', () => {
    const r = regionsOf([L(1, 'B'), L(2, 'A'), L(3, 'C', true)])
    expect(r.map((g) => g.name)).toEqual(['C', 'A', 'B'])
  })
  it('empty', () => expect(regionsOf([])).toEqual([]))
})
