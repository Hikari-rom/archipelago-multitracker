import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import CompactList from '../src/components/CompactList.vue'
import HistoryView from '../src/components/HistoryView.vue'
import SlotCard from '../src/components/SlotCard.vue'
import { installMock } from '../src/lib/api'
import { compactMain, splitFeatured } from '../src/lib/dashboard'
import { formatChecked, sentText } from '../src/lib/history'
import { isActive, NO_OVERRIDES, sortSlots } from '../src/lib/logic'
import type { HistoryPage, SentCheck } from '../src/lib/types'
import { pinActive, setInactive, tracker } from '../src/stores/tracker'
import { mk } from './helpers'

const NOW = 1_800_000_000_000
const ago = (min: number) => NOW / 1000 - min * 60

afterEach(() => {
  tracker.activity = { pinned: null, dismissed: {} }
  tracker.slots = []
})

describe('active game chosen by hand', () => {
  const played = mk({ name: 'played', last_check_at: ago(5) })
  const older = mk({ name: 'older', last_check_at: ago(20) })
  const idle = mk({ name: 'idle', last_check_at: null })

  it('pinned game is active; once chosen, the others need a newer check', () => {
    const ov = { pinned: { name: 'idle', at: ago(10) }, dismissed: {} }
    expect(isActive(idle, NOW, 30, ov)).toBe(true)
    expect(isActive(played, NOW, 30, ov)).toBe(true) // checked after the choice
    expect(isActive(older, NOW, 30, ov)).toBe(false) // its last check is older than the choice
    expect(splitFeatured([older, played, idle], NOW, 30, ov).featured.map((s) => s.name)).toEqual(['idle', 'played'])
    expect(sortSlots([older, played, idle], NOW, 30, ov).map((s) => s.name)).toEqual(['played', 'idle', 'older'])
  })

  it('a game set inactive comes back with its next check', () => {
    const ov = { pinned: null, dismissed: { played: ago(5) } }
    expect(isActive(played, NOW, 30, NO_OVERRIDES)).toBe(true)
    expect(isActive(played, NOW, 30, ov)).toBe(false)
    expect(isActive({ ...played, last_check_at: ago(1) }, NOW, 30, ov)).toBe(true)
  })

  it('compact layout shows one game: chosen, else most recent active, else the first', () => {
    expect(compactMain([older, played, idle], NOW, 30)?.name).toBe('played')
    expect(compactMain([older, played, idle], NOW, 30, { pinned: { name: 'idle', at: ago(1) }, dismissed: {} })?.name).toBe('idle')
    expect(compactMain([mk({ name: 'a' }), mk({ name: 'b' })], NOW, 30)?.name).toBe('a')
    expect(compactMain([], NOW, 30)).toBeNull()
  })

  it('card buttons pin and unpin; the compact list pins on click', async () => {
    tracker.slots = [played]
    tracker.nowMs = NOW
    const card = mount(SlotCard, { props: { summary: played } })
    await card.get('button.set-inactive').trigger('click')
    expect(tracker.activity.dismissed.played).toBe(played.last_check_at)
    await card.vm.$nextTick()
    await card.get('button.set-active').trigger('click')
    expect(tracker.activity.pinned?.name).toBe('played')
    expect(card.text()).toContain('Actif · choisi')
    setInactive('played')
    expect(tracker.activity.pinned).toBeNull()
    const list = mount(CompactList, { props: { slots: [played, idle], current: 'played' } })
    expect(list.get('[aria-current=true]').attributes('data-slot-name')).toBe('played')
    await list.get('[data-slot-name=idle]').trigger('click')
    expect(tracker.activity.pinned?.name).toBe('idle')
    pinActive('played')
    expect(tracker.activity.pinned?.name).toBe('played')
  })
})

describe('history page', () => {
  it('per-slot counts and times', () => {
    expect(sentText({ checks: { done: 10 }, sent: { known: 10, to_others: 7 } })).toBe('7')
    expect(sentText({ checks: { done: 10 }, sent: { known: 6, to_others: 4 } })).toBe('4 (+ 4 au contenu inconnu)')
    expect(formatChecked({ checked_at: null, checked_after: null }, NOW)).toBe('avant le suivi')
    expect(formatChecked({ checked_at: ago(3), checked_after: null }, NOW)).toBe('il y a 3 min')
  })

  it('lists the checks sent, with what they held and for whom', async () => {
    const check = (p: Partial<SentCheck>): SentCheck => ({
      slot: 'a', game: 'Game A', location_id: 1, location: 'Room 1', checked_at: ago(2), checked_after: null,
      item: 'Hookshot', receiver: 'Bob', receiver_game: 'Zelda', to_self: false, progression: true, useful: false,
      trap: false, ...p,
    })
    const asked: string[][] = []
    installMock({
      getSlot: async () => { throw new Error('unused') },
      markSeen: async () => ({ seen: 0 }),
      history: async (kind, slots) => {
        asked.push([kind, ...slots])
        const page: HistoryPage<SentCheck> = {
          kind: 'sent', total: 3, offset: 0, scout_checked: true,
          items: [check({}), check({ location_id: 2, location: 'Room 2', item: 'Bow', to_self: true, receiver: 'a', progression: false }),
            check({ location_id: 3, location: 'Room 3', item: null, receiver: null, receiver_game: null, to_self: null })],
          slots: [
            { name: 'a', game: 'Game A', checks: { done: 3, total: 9 }, sent: { known: 2, to_others: 1 }, received: 4 },
            { name: 'b', game: 'Game B', checks: { done: 0, total: 5 }, sent: { known: 0, to_others: 0 }, received: 0 },
          ],
        }
        return page
      },
    })
    const w = mount(HistoryView, { props: { slots: [mk({ name: 'a' }), mk({ name: 'b' })] } })
    await flushPromises()
    expect(asked[0]).toEqual(['sent', 'a', 'b'])
    const rows = w.findAll('li').map((li) => li.text().replace(/\s+/g, ' '))
    expect(rows[0]).toContain('Room 1 → ★Hookshot pour Bob (Zelda)')
    expect(rows[1]).toContain('Room 2 → Bow pour toi')
    expect(rows[2]).toContain('contenu inconnu')
    expect(w.text()).toContain('1 (+ 1 au contenu inconnu)')
    await w.get('tbody button').trigger('click') // filter on the first game
    await flushPromises()
    expect(asked.at(-1)).toEqual(['sent', 'a'])
  })
})

describe('history page reloads', () => {
  it('only when the slots change, not on every new summary object', async () => {
    let calls = 0
    installMock({
      getSlot: async () => { throw new Error('unused') },
      markSeen: async () => ({ seen: 0 }),
      history: async () => {
        calls++
        return { kind: 'sent', total: 0, offset: 0, items: [], slots: [], scout_checked: true }
      },
    })
    const w = mount(HistoryView, { props: { slots: [mk({ name: 'a' })] } })
    await flushPromises()
    expect(calls).toBe(1)
    await w.setProps({ slots: [mk({ name: 'a' })] }) // same slot, new object (live update without change)
    await flushPromises()
    expect(calls).toBe(1)
    await w.setProps({ slots: [mk({ name: 'a' }), mk({ name: 'b' })] })
    await flushPromises()
    expect(calls).toBe(2)
  })
})
