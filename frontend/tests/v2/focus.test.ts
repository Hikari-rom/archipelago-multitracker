import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import FocusList from '../../src/v2/components/FocusList.vue'
import DashboardV2 from '../../src/v2/views/DashboardV2.vue'
import { installMock } from '../../src/lib/api'
import { tracker } from '../../src/stores/tracker'
import { mk } from '../helpers'

beforeEach(() => {
  installMock({ getSlot: async (n) => ({ ...mk({ name: n }), items_list: [], hints_in_my_world: [], hints_mine_elsewhere: [], in_logic_locations: [] }), markSeen: async () => ({ seen: 0 }) })
  tracker.loaded = true
})
afterEach(() => {
  tracker.slots = []
  tracker.activity = { pinned: null, dismissed: {} }
  localStorage.clear()
})

describe('Focus', () => {
  it('list click shows the game and makes it active', async () => {
    tracker.slots = [mk({ name: 'a', game: 'A' }), mk({ name: 'ww', game: 'The Wind Waker HD', logic: { state: 'ok', count: 58, message: null } })]
    localStorage.setItem('amt-v2-layout', 'focus')
    const w = mount(DashboardV2, { props: { slots: tracker.slots, owner: '*', chips: [] } })
    await flushPromises()
    await w.find('[data-focus-row="ww"]').trigger('click')
    expect(tracker.activity.pinned?.name).toBe('ww')
    expect(w.find('[data-focus-panel]').attributes('data-focus-panel')).toBe('ww')
    expect(w.find('[data-focus-row="ww"]').attributes('aria-current')).toBe('true')
  })
  it('rows: number, tags, remaining', () => {
    const s = [mk({ name: 'a', game: 'A', logic: { state: 'ok', count: 3, message: null }, items: { received: 2, new: 2 }, checks: { done: 1, total: 10, remaining: 9 } })]
    const t = mount(FocusList, { props: { slots: s, current: null } }).text()
    expect(t).toContain('3')
    expect(t).toContain('★2')
    expect(t).toContain('9 rest.')
  })
})

describe('FocusList marker', () => {
  it('marks the current row', () => {
    const s = [mk({ name: 'a', game: 'A' }), mk({ name: 'b', game: 'B' })]
    const w = mount(FocusList, { props: { slots: s, current: 'b' } })
    expect(w.find('[data-focus-row="b"]').attributes('aria-current')).toBe('true')
    expect(w.find('[data-focus-row="a"]').attributes('aria-current')).toBeUndefined()
  })
})

describe('Phone', () => {
  afterEach(() => vi.unstubAllGlobals())
  it('carousel shows active games, "Détails" opens the sheet', async () => {
    vi.stubGlobal('matchMedia', (q: string) => ({ matches: q.includes('max-width: 699px'), media: q, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {} }))
    tracker.slots = [mk({ name: 'a', game: 'A' }), mk({ name: 'b', game: 'B' })]
    tracker.activity = { pinned: { name: 'a', at: Date.now() / 1000 }, dismissed: {} }
    const w = mount(DashboardV2, { props: { slots: tracker.slots, owner: '*', chips: [] }, attachTo: document.body })
    await flushPromises()
    expect(w.find('[data-carousel-card="a"]').exists()).toBe(true)
    expect(w.find('[data-focus-row="b"]').exists()).toBe(true)
    await w.find('[data-details]').trigger('click')
    await flushPromises()
    expect(document.body.querySelector('[aria-label="Fermer"]')).not.toBeNull()
    w.unmount()
  })
  it('Focus: the list count matches the "Où avancer" count with 2 active games, and says "toucher"', async () => {
    vi.stubGlobal('matchMedia', (q: string) => ({ matches: q.includes('max-width: 699px'), media: q, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {} }))
    const now = Date.now() / 1000
    tracker.slots = ['a', 'b', 'c', 'd'].map((n) => mk({ name: n, game: n.toUpperCase(), last_check_at: n < 'c' ? now - 60 : null }))
    tracker.activity = { pinned: null, dismissed: {} }
    localStorage.setItem('amt-v2-layout', 'focus')
    const w = mount(DashboardV2, { props: { slots: tracker.slots, owner: '*', chips: [] }, attachTo: document.body })
    await flushPromises()
    const rows = w.findAll('[data-focus-row]').length
    expect(w.text()).toContain(`${rows} jeux · toucher = afficher et rendre actif`)
    expect(w.text()).toContain(`Où avancer · ${rows}`)
    expect(w.text()).not.toContain('Toucher = rendre actif')
    w.unmount()
  })
})
