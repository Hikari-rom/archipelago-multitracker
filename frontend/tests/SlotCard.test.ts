import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import SlotCard from '../src/components/SlotCard.vue'
import { tracker } from '../src/stores/tracker'
import { mk } from './helpers'

afterEach(() => vi.unstubAllGlobals())

describe('SlotCard', () => {
  const s = mk({
    name: 'Romain/Celeste', game: 'Celeste (Open World)',
    items: { received: 4, new: 2 },
    hints: { mine_elsewhere: 0, in_my_world: 1, in_my_world_in_logic: 1 },
    logic: { state: 'ok', count: 14, message: null },
  })

  it('renders badge, chips and counters', () => {
    const w = mount(SlotCard, { props: { summary: s } })
    expect(w.text()).toContain('Celeste (Open World)')
    expect(w.text()).toContain('Tu peux avancer : 14 checks en logique')
    expect(w.text()).toContain('1 location hintée en logique')
    expect(w.text()).toContain('2 nouveaux items')
  })

  it('shows unavailable message', () => {
    const w = mount(SlotCard, { props: { summary: mk({ name: 'k', logic: { state: 'unavailable', count: 0, message: 'pas dispo' } }) } })
    expect(w.text()).toContain('Logique indisponible pour ce jeu')
    expect(w.text()).toContain('pas dispo')
  })

  it('"Marquer comme vu" POSTs and clears the counter', async () => {
    tracker.slots = [JSON.parse(JSON.stringify(s))]
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ seen: 4 }), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)
    const w = mount(SlotCard, { props: { summary: tracker.slots[0] } })
    await w.find('button.btn').trigger('click')
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalled())
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/slots/Romain%2FCeleste/seen')
    expect(init.method).toBe('POST')
    await vi.waitFor(() => expect(tracker.slots[0].items.new).toBe(0))
  })

  it('toggle has aria-expanded', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('x')))
    const w = mount(SlotCard, { props: { summary: s } })
    const t = w.find('button.toggle')
    expect(t.attributes('aria-expanded')).toBe('false')
    await t.trigger('click')
    expect(t.attributes('aria-expanded')).toBe('true')
  })
})
