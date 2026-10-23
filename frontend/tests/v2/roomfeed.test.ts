import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import MoreMenu from '../../src/v2/components/MoreMenu.vue'
import AppV2 from '../../src/v2/AppV2.vue'
import { installMock } from '../../src/lib/api'
import type { MockApi } from '../../src/lib/api'
import type { RoomFeedCheck, RoomFeedStatus, RoomFeedSummary } from '../../src/lib/types'
import { onRoomCheck, useRoomFeed } from '../../src/v2/lib/roomfeed'
import { roomfeedListeners, setView, tracker } from '../../src/stores/tracker'
import { mockRoomFeedActivity, mockRoomFeedChecks, mockRoomFeedSummary } from '../../src/mock/fixtures'
import { mk } from '../helpers'

const status: RoomFeedStatus = { enabled: true, state: 'listening', error: null, seed: 'S1' }
const summary: RoomFeedSummary = { room: { done: 1, total: 2, slots: 1, goals: 0, playing: 0 }, players: [] }

function mockFeed(over: Partial<MockApi> = {}) {
  const getRoomFeed = vi.fn(async () => status)
  const getRoomFeedSummary = vi.fn(async () => summary)
  installMock({ getSlot: async () => { throw new Error('no') }, markSeen: async () => ({ seen: 0 }), getRoomFeed, getRoomFeedSummary, ...over })
  return { getRoomFeed, getRoomFeedSummary }
}

afterEach(() => {
  tracker.slots = []
  tracker.loaded = false
  tracker.roomDashboard = false
  setView('dashboard')
  vi.useRealTimers()
})

describe('#room view', () => {
  it('hash maps to the room view', () => {
    location.hash = '#room'
    window.dispatchEvent(new HashChangeEvent('hashchange'))
    expect(tracker.view).toBe('room')
    location.hash = ''
    window.dispatchEvent(new HashChangeEvent('hashchange'))
    expect(tracker.view).toBe('dashboard')
  })
  it('AppV2 shows the placeholder with the disabled message', async () => {
    tracker.loaded = true
    tracker.slots = [mk({ name: 'a' })]
    mockFeed({ getRoomFeed: async () => ({ enabled: false }) })
    setView('room')
    const w = mount(AppV2)
    await flushPromises()
    expect(w.text()).toContain('Room complète')
    expect(w.text()).toContain('désactivé')
    w.unmount()
  })
})

describe('MoreMenu room entry', () => {
  const open = async (w: ReturnType<typeof mount>) => {
    await w.find('button[aria-label="Plus"]').trigger('keydown', { key: 'Enter' })
    await flushPromises()
  }
  const labels = () => [...document.body.querySelectorAll('[role="menuitem"]')].map((e) => e.textContent?.trim())
  it('only when the dashboard is enabled', async () => {
    tracker.roomDashboard = false
    const off = mount(MoreMenu, { attachTo: document.body })
    await open(off)
    expect(labels()).toEqual(['Journal', 'Configuration', 'Revenir à la v1'])
    off.unmount()
    tracker.roomDashboard = true
    const on = mount(MoreMenu, { attachTo: document.body })
    await open(on)
    expect(labels()).toEqual(['Journal', 'Configuration', 'Room complète', 'Revenir à la v1'])
    on.unmount()
  })
})

describe('useRoomFeed', () => {
  beforeEach(() => vi.useFakeTimers())
  const host = () => {
    let api!: ReturnType<typeof useRoomFeed>
    const w = mount(defineComponent({ setup() { api = useRoomFeed(); return () => h('div') } }))
    return { w, api }
  }

  it('loads status and summary on mount, refetches (debounced) on roomfeed events, unregisters on unmount', async () => {
    const m = mockFeed()
    const { w, api } = host()
    await flushPromises()
    expect(m.getRoomFeed).toHaveBeenCalledTimes(1)
    expect(api.status.value).toEqual(status)
    expect(api.summary.value).toEqual(summary)
    expect(api.loading.value).toBe(false)
    for (const fn of roomfeedListeners.state) { fn({ type: 'roomfeed' }); fn({ type: 'roomfeed' }) }
    await vi.advanceTimersByTimeAsync(900)
    expect(m.getRoomFeed).toHaveBeenCalledTimes(1)
    await vi.advanceTimersByTimeAsync(200)
    expect(m.getRoomFeed).toHaveBeenCalledTimes(2)
    expect(m.getRoomFeedSummary).toHaveBeenCalledTimes(2)
    w.unmount()
    expect(roomfeedListeners.state.size).toBe(0)
  })

  it('does not ask for the summary when disabled; keeps the error', async () => {
    const m = mockFeed({ getRoomFeed: async () => ({ enabled: false }) })
    const { w, api } = host()
    await flushPromises()
    expect(api.status.value).toEqual({ enabled: false })
    expect(api.summary.value).toBeNull()
    expect(m.getRoomFeedSummary).not.toHaveBeenCalled()
    w.unmount()
    mockFeed({ getRoomFeed: async () => { throw new Error('boom') } })
    const h2 = host()
    await flushPromises()
    expect(h2.api.error.value).toBe('boom')
    h2.w.unmount()
  })
})

describe('onRoomCheck', () => {
  it('receives forwarded check events until unmount', () => {
    const got: unknown[] = []
    const w = mount(defineComponent({ setup() { onRoomCheck((d) => got.push(d)); return () => h('div') } }))
    const ev = { type: 'roomfeed_check', checks: [{ key: '1:2' } as RoomFeedCheck] }
    for (const fn of roomfeedListeners.check) fn(ev)
    expect(got).toEqual([ev])
    w.unmount()
    expect(roomfeedListeners.check.size).toBe(0)
  })
})

describe('room feed mock', () => {
  it('summary: 6 players, about 30 slots, a tracked player with 3 slots and one BK slot', () => {
    const s = mockRoomFeedSummary()
    expect(s.players).toHaveLength(6)
    expect(s.room.slots).toBe(30)
    const me = s.players.filter((p) => p.me)
    expect(me).toHaveLength(1)
    expect(me[0].slots).toHaveLength(3)
    expect(s.players.flatMap((p) => p.slots).filter((x) => x.bk === true)).toHaveLength(1)
    expect(new Set(s.players.flatMap((p) => p.slots.map((x) => x.presence))).size).toBeGreaterThan(2)
  })
  it('checks: 300 over 3 days, 20 catch-up of which 5 undated, filters and paging honoured', () => {
    const all = mockRoomFeedChecks({ limit: 500 })
    expect(all.total).toBe(300)
    expect(all.items.filter((c) => c.src === 'catchup')).toHaveLength(20)
    expect(all.items.filter((c) => c.src === 'catchup' && c.after === null)).toHaveLength(5)
    expect(new Set(all.items.map((c) => c.key)).size).toBe(300)
    const page = mockRoomFeedChecks({ limit: 10, offset: 5 })
    expect(page.items.map((c) => c.key)).toEqual(all.items.slice(5, 15).map((c) => c.key))
    const alice = mockRoomFeedChecks({ player: 'Alice', limit: 500 })
    expect(alice.total).toBeGreaterThan(0)
    expect(alice.items.every((c) => c.sender_player === 'Alice')).toBe(true)
    const game = mockRoomFeedChecks({ game: 'Hades', limit: 500 })
    expect(game.items.every((c) => c.sender_game === 'Hades')).toBe(true)
  })
  it('activity: 48 hours and 30 days, restricted to a player', () => {
    const h = mockRoomFeedActivity('hour')
    expect(h.buckets).toHaveLength(48)
    expect(mockRoomFeedActivity('day').buckets).toHaveLength(30)
    expect(h.undated).toBeGreaterThanOrEqual(5)
    const total = h.buckets.reduce((n, b) => n + b.count, 0)
    expect(total).toBeGreaterThan(0)
    const bob = mockRoomFeedActivity('hour', 'Bob')
    expect(bob.buckets.reduce((n, b) => n + b.count, 0)).toBeLessThan(total)
    expect(bob.buckets.every((b) => Object.keys(b.by_player).every((k) => k === 'Bob'))).toBe(true)
  })
})
