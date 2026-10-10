import { describe, expect, it } from 'vitest'
import { initialState, reduce } from '../src/lib/state'
import { mk } from './helpers'

describe('reduce', () => {
  it('snapshot then slot update', () => {
    let s = reduce(initialState(), { type: 'snapshot', slots: [mk({ name: 'a' }), mk({ name: 'b' })], server: 'srv' })
    expect(s.loaded).toBe(true)
    expect(s.server).toBe('srv')
    expect(s.slots).toHaveLength(2)
    const before = s
    s = reduce(s, { type: 'slot', slot: mk({ name: 'b', items: { received: 3, new: 3 } }) })
    expect(s.slots.map((x) => x.name)).toEqual(['a', 'b'])
    expect(s.slots[1].items.new).toBe(3)
    expect(before.slots[1].items.new).toBe(0)
    s = reduce(s, { type: 'slot', slot: mk({ name: 'c' }) })
    expect(s.slots).toHaveLength(3)
  })
  it('snapshot replaces everything and keeps server if absent', () => {
    let s = reduce(initialState(), { type: 'snapshot', slots: [mk({ name: 'a' })], server: 'srv' })
    s = reduce(s, { type: 'snapshot', slots: [mk({ name: 'z' })] })
    expect(s.slots.map((x) => x.name)).toEqual(['z'])
    expect(s.server).toBe('srv')
  })
})
