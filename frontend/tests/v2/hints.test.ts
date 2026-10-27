import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { accessDetail, filterHints, groupBySlot, sortHints } from '../../src/lib/hints'
import type { HintRow, HintsResponse } from '../../src/lib/types'
import { hintsListeners, tracker } from '../../src/stores/tracker'
import HintsV2 from '../../src/v2/views/HintsV2.vue'
import { mk } from '../helpers'

function row(p: Partial<HintRow> & { item: string }): HintRow {
  return {
    location: 'Somewhere', finder: 'Friend', finder_slot: 'Friend', finder_game: 'Game C', receiver: 'Me_A', receiver_slot: 'Me_A',
    receiver_game: 'Game A', found: false, status: 'unspecified', progression: true, useful: false, trap: false,
    finder_tracked: false, receiver_tracked: true, slots: ['Me_A'], access: { state: 'ok' }, ...p,
  }
}

const rows: HintRow[] = [
  row({ item: 'Hookshot', location: 'Chest 1', access: { state: 'blocked', blockers: { kind: 'set', items: [['Power Star', 3], ['Key', 1]] } } }),
  row({ item: 'Bow', location: 'Chest 2', status: 'priority' }),
  row({ item: 'Bomb', finder: 'Me_A', finder_slot: 'Me_A', receiver: 'Other', receiver_slot: 'Other', receiver_tracked: false, finder_tracked: true,
        access: { state: 'blocked', blockers: { kind: 'single', items: ['Ladder'] } } }),
  row({ item: 'Old Boot', found: true, access: { state: 'found' }, progression: false }),
  row({ item: 'Sword', finder: 'Me_A', finder_slot: 'Me_A', receiver: 'Me_B', receiver_slot: 'Me_B', slots: ['Me_A', 'Me_B'], finder_tracked: true,
        access: { state: 'unknown', reason: 'calcul en cours' } }),
  row({ item: 'Elsewhere', slots: ['Me_C'], receiver: 'Me_C', receiver_slot: 'Me_C' }),
]

afterEach(() => {
  vi.unstubAllGlobals()
  localStorage.clear()
  tracker.hintsLayout = 'registre'
})

describe('hints helpers', () => {
  it('says what is missing', () => {
    expect(accessDetail(rows[0].access)).toBe('Il manque : Power Star ×3, Key')
    expect(accessDetail(rows[2].access)).toBe('Il manque : Ladder')
    expect(accessDetail({ state: 'blocked', blockers: { kind: 'single', items: ['A', 'B'] } })).toBe('Un seul de ces items suffit : A, B')
    expect(accessDetail({ state: 'blocked', blockers: { kind: 'none' } })).toContain('Hors logique')
    expect(accessDetail({ state: 'ok' })).toBe('')
  })

  it('sorts by access (closest first), then priority; and by any column', () => {
    expect(sortHints(rows.slice(0, 5), 'access', 1).map((h) => h.item)).toEqual(['Bow', 'Bomb', 'Hookshot', 'Sword', 'Old Boot'])
    expect(sortHints(rows.slice(0, 5), 'item', -1).map((h) => h.item)).toEqual(['Sword', 'Old Boot', 'Hookshot', 'Bow', 'Bomb'])
    expect(sortHints(rows.slice(0, 3), 'status', 1)[0].item).toBe('Bow')
  })

  it('filters by slot, direction, access and text', () => {
    const mine = new Set(['Me_A', 'Me_B'])
    const f = (filter: 'all' | 'mine' | 'world' | 'ok', query = '', hideFound = true) => filterHints(rows, mine, { filter, query, hideFound }).map((h) => h.item)
    expect(f('all')).toEqual(['Hookshot', 'Bow', 'Bomb', 'Sword'])
    expect(f('all', '', false)).toContain('Old Boot')
    expect(f('mine')).toEqual(['Hookshot', 'Bow', 'Sword'])
    expect(f('world')).toEqual(['Bomb', 'Sword'])
    expect(f('ok')).toEqual(['Bow'])
    expect(f('all', 'chest 2')).toEqual(['Bow'])
    const g = groupBySlot(filterHints(rows, mine, { filter: 'all', query: '', hideFound: true }), [{ name: 'Me_A', game: 'Game A' }, { name: 'Me_B', game: 'Game B' }])
    expect(g.map((x) => [x.name, x.rows.length, x.ok, x.blocked])).toEqual([['Me_A', 4, 1, 2], ['Me_B', 1, 0, 0]])
  })
})

describe('HintsV2', () => {
  const resp: HintsResponse = { hints: rows, foreign: { enabled: true, max: 12, followed: [{ name: 'Friend', game: 'Game C', status: 'connected', logic: { state: 'ok' } }], capped: [] } }
  const slots = [mk({ name: 'Me_A', game: 'Game A' }), mk({ name: 'Me_B', game: 'Game B' })]

  function stub(body: HintsResponse) {
    const fn = vi.fn(async () => new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } }))
    vi.stubGlobal('fetch', fn)
    return fn
  }

  it('registre: counts, sortable headers, filters', async () => {
    stub(resp)
    const w = mount(HintsV2, { props: { slots, owner: '*', chips: [] } })
    await flushPromises()
    expect(w.find('[data-hints-counts]').text()).toContain('4 à trouver')
    expect(w.text()).toContain('chez 1 autre slot')
    expect(w.findAll('[data-hint]').map((r) => r.attributes('data-hint'))).toEqual(['Bow', 'Bomb', 'Hookshot', 'Sword'])
    expect(w.find('[data-hint="Hookshot"]').text()).toContain('Il manque : Power Star ×3, Key')
    const itemHeader = w.findAll('th').find((t) => t.text().startsWith('Item'))!
    await itemHeader.find('button').trigger('click')
    expect(itemHeader.attributes('aria-sort')).toBe('ascending')
    expect(w.findAll('[data-hint]').map((r) => r.attributes('data-hint'))).toEqual(['Bomb', 'Bow', 'Hookshot', 'Sword'])
    expect(JSON.parse(localStorage.getItem('amt-v2-hints-sort')!)).toEqual({ key: 'item', dir: 1 })
    await w.find('[data-filter="ok"]').trigger('click')
    expect(w.findAll('[data-hint]').map((r) => r.attributes('data-hint'))).toEqual(['Bow'])
    w.unmount()
  })

  it('deux sens and par slot; refetch on the SSE event', async () => {
    vi.useFakeTimers()
    const fetch = stub(resp)
    tracker.hintsLayout = 'sens'
    const w = mount(HintsV2, { props: { slots, owner: '*', chips: [] } })
    await flushPromises()
    const tables = w.findAll('table')
    expect(tables.map((t) => t.attributes('aria-label'))).toEqual(['Tes items chez les autres', 'Dans tes mondes'])
    expect(tables[1].findAll('[data-hint]').map((r) => r.attributes('data-hint'))).toEqual(['Bomb', 'Sword'])
    tracker.hintsLayout = 'slots'
    await flushPromises()
    expect(w.findAll('[data-hints-slot]').map((d) => d.attributes('data-hints-slot'))).toEqual(['Me_A', 'Me_B'])
    expect(w.find('[data-hints-slot="Me_A"]').text()).toContain('Dans ce monde')
    expect(fetch).toHaveBeenCalledTimes(1)
    for (const fn of [...hintsListeners]) fn()
    vi.advanceTimersByTime(500)
    await flushPromises()
    expect(fetch).toHaveBeenCalledTimes(2)
    w.unmount()
    expect(hintsListeners.size).toBe(0)
    vi.useRealTimers()
  })
})
