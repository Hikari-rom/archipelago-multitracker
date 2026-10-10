import { describe, expect, it } from 'vitest'
import { stableOrder } from '../src/lib/order'
import { mk } from './helpers'

const names = (l: { name: string }[]) => l.map((s) => s.name)

describe('stableOrder', () => {
  const sorted = [mk({ name: 'c' }), mk({ name: 'a' }), mk({ name: 'b' }), mk({ name: 'd' })]
  it('returns sorted when not frozen', () => {
    expect(names(stableOrder(['a', 'b', 'c'], sorted, false))).toEqual(['c', 'a', 'b', 'd'])
  })
  it('keeps previous order when frozen, appends new slots', () => {
    expect(names(stableOrder(['a', 'b', 'c'], sorted, true))).toEqual(['a', 'b', 'c', 'd'])
  })
  it('drops removed slots and uses latest data', () => {
    const fresh = [mk({ name: 'b', items: { received: 2, new: 2 } }), mk({ name: 'a' })]
    const r = stableOrder(['a', 'x', 'b'], fresh, true)
    expect(names(r)).toEqual(['a', 'b'])
    expect(r[1].items.new).toBe(2)
  })
})
