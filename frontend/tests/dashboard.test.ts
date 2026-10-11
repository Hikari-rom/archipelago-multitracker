import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ProgressSplit from '../src/components/ProgressSplit.vue'
import RecentFeed from '../src/components/RecentFeed.vue'
import { barParts, feedItems, sortBy, totals } from '../src/lib/dashboard'
import type { RecentItem } from '../src/lib/types'
import { tracker } from '../src/stores/tracker'
import { mk } from './helpers'

const logic = (count: number, state: 'ok' | 'unavailable' = 'ok') => ({ state, count, message: null })
const checks = (done: number, total: number) => ({ done, total, remaining: total - done })

describe('dashboard', () => {
  const slots = [
    mk({ name: 'big', checks: checks(0, 500), logic: logic(40) }), // 8 %
    mk({ name: 'small', checks: checks(10, 50), logic: logic(20) }), // 40 %
    mk({ name: 'none', checks: checks(0, 100), logic: logic(0, 'unavailable') }),
    mk({ name: 'zero', checks: checks(5, 100), logic: logic(0) }),
    mk({ name: 'done', checks: checks(30, 30), logic: logic(0), goal: true }),
  ]
  const names = (l: { name: string }[]) => l.map((s) => s.name)

  it('sorts by checks in logic, as a number or as a share of the game', () => {
    expect(names(sortBy('count', slots))).toEqual(['big', 'small', 'zero', 'none', 'done'])
    expect(names(sortBy('percent', slots))).toEqual(['small', 'big', 'zero', 'none', 'done'])
    expect(names(sortBy('auto', slots))[0]).toBe('big')
  })

  it('totals of the selected slots (finished games add no checks in logic)', () => {
    const s = [...slots, mk({ name: 'g', checks: checks(1, 2), logic: logic(1), goal: true, items: { received: 3, new: 2 } })]
    expect(totals(s)).toEqual({ done: 46, total: 782, inLogic: 60, newItems: 2 })
  })

  it('bar parts: done in green, then in logic in blue, never over 100 %', () => {
    expect(barParts(25, 25, 100)).toEqual({ done: 25, logic: 25 })
    expect(barParts(90, 50, 100)).toEqual({ done: 90, logic: 10 })
    expect(barParts(0, 0, 0)).toEqual({ done: 0, logic: 0 })
    const w = mount(ProgressSplit, { props: { done: 1, logic: 2, total: 4, label: 'x' } })
    expect(w.findAll('[role=img] > div').map((d) => d.attributes('style'))).toEqual(['width: 25%;', 'width: 50%;'])
    expect(w.attributes('aria-label')).toBe('x')
  })

  it('feed shows the items of the selected slots only', async () => {
    const item = (slot: string, index: number, name: string): RecentItem => ({
      index, name, slot, game: 'Game ' + slot, sender: 'Alice', own: false, origin: 'other', location: 'L',
      progression: true, useful: false, trap: false, new: false, received_at: Date.now() / 1000 - index * 60,
    })
    tracker.recent = [item('a', 1, 'Hookshot'), item('b', 2, 'Bow'), item('a', 3, 'Fire')]
    expect(feedItems(tracker.recent, new Set(['a']), 5).map((i) => i.name)).toEqual(['Hookshot', 'Fire'])
    const w = mount(RecentFeed, { props: { slots: [mk({ name: 'a' })] } })
    expect(w.text()).toContain('Hookshot')
    expect(w.text()).toContain('pour Game a (a) · de Alice')
    expect(w.text()).not.toContain('Bow')
    tracker.recent = []
    await w.vm.$nextTick()
    expect(w.text()).toContain('Aucun item reçu')
  })
})

describe('featured (active) games', () => {
  it('go first, most recent first, the others keep their order', async () => {
    const { splitFeatured } = await import('../src/lib/dashboard')
    const now = Date.now()
    const ago = (min: number) => now / 1000 - min * 60
    const slots = [
      mk({ name: 'a' }),
      mk({ name: 'b', last_check_at: ago(20) }),
      mk({ name: 'c', last_check_at: ago(90) }),
      mk({ name: 'd', last_check_at: ago(2) }),
      mk({ name: 'e', last_check_at: ago(1), goal: true }),
    ]
    const r = splitFeatured(slots, now, 30)
    expect(r.featured.map((s) => s.name)).toEqual(['d', 'b'])
    expect(r.rest.map((s) => s.name)).toEqual(['a', 'c', 'e'])
  })

  it('a featured game shows its details until the user hides them', async () => {
    const { isOpen, setFeatured, toggleOpen } = await import('../src/stores/tracker')
    tracker.open = {}
    setFeatured(['x'])
    expect(isOpen('x')).toBe(true)
    expect(isOpen('y')).toBe(false)
    toggleOpen('x')
    expect(isOpen('x')).toBe(false)
    setFeatured([])
    tracker.open = {}
    expect(isOpen('x')).toBe(false)
  })
})
