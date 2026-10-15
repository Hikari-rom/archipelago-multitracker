import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import DashboardV2 from '../../src/v2/views/DashboardV2.vue'
import { installMock } from '../../src/lib/api'
import { tracker } from '../../src/stores/tracker'
import { mk } from '../helpers'

const NOW = 1_800_000_000_000
const ago = (m: number) => NOW / 1000 - m * 60

beforeEach(() => {
  installMock({ getSlot: async (n) => ({ ...mk({ name: n }), items_list: [], hints_in_my_world: [], hints_mine_elsewhere: [], in_logic_locations: [] }), markSeen: async () => ({ seen: 0 }) })
  tracker.nowMs = NOW
  tracker.activeMinutes = 30
  tracker.loaded = true
})
afterEach(() => {
  tracker.slots = []
  tracker.activity = { pinned: null, dismissed: {} }
  localStorage.clear()
})

const slots = () => [
  mk({ name: 'isaac', game: 'The Binding of Isaac Repentance', logic: { state: 'ok', count: 58, message: null }, checks: { done: 0, total: 361, remaining: 361 } }),
  mk({ name: 'celeste', game: 'Celeste (Open World)', last_check_at: ago(12), logic: { state: 'ok', count: 7, message: null }, items: { received: 1, new: 1 } }),
  mk({ name: 'jak3', game: 'Jak 3', logic: { state: 'ok', count: 34, message: null }, hints: { mine_elsewhere: 0, in_my_world: 1, in_my_world_in_logic: 1 } }),
  mk({ name: 'mkwii', game: 'Mario Kart Wii', logic: { state: 'unavailable', count: 0, message: null } }),
]

describe('DashboardV2 · Cartes', () => {
  it('totals, actives first, then "Où avancer"', async () => {
    tracker.slots = slots()
    tracker.activity = { pinned: { name: 'isaac', at: ago(20) }, dismissed: {} }
    const w = mount(DashboardV2, { props: { slots: tracker.slots, owner: '*', chips: [] } })
    await flushPromises()
    expect(w.text()).toContain('99 en logique')
    const actives = w.findAll('[data-active-card]').map((c) => c.attributes('data-active-card'))
    expect(actives).toEqual(['isaac', 'celeste'])
    expect(w.text()).toContain('◉ Actif · choisi')
    expect(w.text()).toContain('Où avancer · 2 jeux')
    const tiles = w.findAll('[data-tile]').map((t) => t.attributes('data-tile'))
    expect(tiles).toEqual(['jak3', 'mkwii'])
    expect(w.find('[data-tile="mkwii"]').text()).toContain('—')
    expect(w.find('[data-tile="jak3"]').text()).toContain('◆1')
  })
  it('"Activer" pins the game; "Plus actif" offers undo', async () => {
    tracker.slots = slots()
    const w = mount(DashboardV2, { props: { slots: tracker.slots, owner: '*', chips: [] } })
    await w.find('[data-tile="jak3"] button[data-activate]').trigger('click')
    expect(tracker.activity.pinned?.name).toBe('jak3')
    await w.find('[data-active-card="celeste"] button[data-dismiss]').trigger('click')
    expect(tracker.activity.dismissed.celeste).toBe(ago(12))
  })
  it('layout switch is remembered under the v2 key', async () => {
    tracker.slots = slots()
    const w = mount(DashboardV2, { props: { slots: tracker.slots, owner: '*', chips: [] } })
    await w.find('button[data-layout="focus"]').trigger('click')
    expect(localStorage.getItem('amt-v2-layout')).toBe('focus')
    expect(localStorage.getItem('amt-layout')).toBeNull()
  })
})
