import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import HistoryV2 from '../../src/v2/views/HistoryV2.vue'
import { installMock } from '../../src/lib/api'
import type { HistoryPage, SentCheck } from '../../src/lib/types'
import { tracker } from '../../src/stores/tracker'
import { mk } from '../helpers'

const t = (d: number, h: number, m: number) => new Date(2026, 9, d, h, m).getTime() / 1000
const check = (p: Partial<SentCheck>): SentCheck => ({
  slot: 'celeste', game: 'Celeste (Open World)', location_id: 1, location: 'Old Site A - Room s2', checked_at: null, checked_after: null,
  item: 'Sand of Hours', receiver: 'romain_zeldaph', receiver_game: 'The Legend of Zelda - Phantom Hourglass', to_self: false,
  progression: true, useful: false, trap: false, ...p,
})
const page: HistoryPage<SentCheck> = {
  kind: 'sent', total: 3, offset: 0, scout_checked: true,
  slots: [{ name: 'celeste', game: 'Celeste (Open World)', checks: { done: 42, total: 729 }, sent: { known: 42, to_others: 41 }, received: 1 }],
  items: [
    check({ checked_at: t(15, 0, 6), location: 'A' }),
    check({ checked_at: t(14, 23, 58), location: 'B', item: null }),
    check({ checked_at: null, location: 'C', to_self: true, receiver: 'celeste' }),
  ],
}

afterEach(() => {
  tracker.slots = []
  window.scrollTo(0, 0)
})

function setup(p: HistoryPage<SentCheck>) {
  installMock({ getSlot: async () => { throw new Error('no') }, markSeen: async () => ({ seen: 0 }), history: async () => p })
  tracker.nowMs = new Date(2026, 9, 15, 0, 30).getTime()
  tracker.slots = [mk({ name: 'celeste', game: 'Celeste (Open World)' })]
  return mount(HistoryV2, { props: { slots: tracker.slots, owner: '*', chips: [] } })
}

describe('HistoryV2', () => {
  it('sent checks grouped by day, unknown content, per-game table', async () => {
    const w = setup(page)
    await flushPromises()
    const days = w.findAll('[data-day]').map((d) => d.attributes('data-day'))
    expect(days).toEqual(["Aujourd'hui", 'Hier', 'Avant le suivi'])
    expect(w.text()).toContain('contenu inconnu')
    expect(w.text()).toContain('pour moi')
    expect(w.text()).toContain('PROG')
    expect(w.find('[data-history-table]').text()).toContain('42 / 729')
    expect(w.findAll('[role="tab"]').map((x) => x.text())).toEqual(['Checks envoyés · 3', 'Items reçus'])
  })

  it('does not depend on the API order', async () => {
    const w = setup({ ...page, items: [...page.items].reverse() })
    await flushPromises()
    expect(w.findAll('[data-day]').map((d) => d.attributes('data-day'))).toEqual(["Aujourd'hui", 'Hier', 'Avant le suivi'])
  })

  it('loads 50 rows per page and fetches the next page when the end of the list comes into view', async () => {
    const all = Array.from({ length: 120 }, (_, i) => check({ location_id: i, location: `L${i}`, checked_at: t(15, 0, 0) - i * 60 }))
    const limits: number[] = []
    installMock({
      getSlot: async () => { throw new Error('no') }, markSeen: async () => ({ seen: 0 }),
      history: async (_k, _s, limit) => (limits.push(limit), { ...page, total: all.length, items: all.slice(0, limit) }),
    })
    tracker.nowMs = new Date(2026, 9, 15, 0, 30).getTime()
    tracker.slots = [mk({ name: 'celeste', game: 'Celeste (Open World)' })]
    const w = mount(HistoryV2, { props: { slots: tracker.slots, owner: '*', chips: [] } })
    await flushPromises()
    expect(limits).toEqual([50])
    expect(w.findAll('li[data-index]').length).toBeLessThan(51) // only the rows on screen are mounted
    window.scrollTo(0, 50 * 33)
    window.dispatchEvent(new Event('scroll'))
    await flushPromises()
    expect(limits).toEqual([50, 100])
    expect(w.text()).toContain('pages de 50')
  })
})
