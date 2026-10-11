import { reactive } from 'vue'
import * as api from '../lib/api'
import { roomFromLocation } from '../lib/config'
import { clockOffset, loadActiveMinutes } from '../lib/history'

import { initialState, reduce, type TrackerEvent } from '../lib/state'
import type { RecentItem, SlotDetail, SseState } from '../lib/types'

export const tracker = reactive({
  ...initialState(),
  sse: 'connecting' as SseState,
  loadError: '' as string,
  roomUrl: '' as string,
  roomError: '' as string,
  view: viewFromHash(),
  /** room link from "#config?room=..." (pre-fills the Configuration page) */
  prefillRoom: typeof location !== 'undefined' ? roomFromLocation(location.hash, location.search) : '',
  roomSleeping: false,
  /** ticks every 30 s: "active" slots and relative times expire on their own */
  nowMs: Date.now(),
  /** a slot is "active" when it checked a location in the last N minutes (setting of this device) */
  activeMinutes: loadActiveMinutes(),
  details: {} as Record<string, SlotDetail>,
  /** details shown or hidden by the user (overrides the default: hidden, except for featured slots) */
  open: {} as Record<string, boolean>,
  /** active slots shown first in a full-width card, details shown by default (set by the dashboard) */
  featured: {} as Record<string, boolean>,
  detailError: {} as Record<string, string>,
  /** true during the short window after "Marquer comme vu" (dashboard order frozen) */
  seenFreeze: false,
  /** latest items received by the slots (dashboard feed), newest first */
  recent: [] as RecentItem[],
})

export type View = 'dashboard' | 'config' | 'logs'

function viewFromHash(): View {
  if (typeof location === 'undefined') return 'dashboard'
  if (/^#config(\?|$)/.test(location.hash)) return 'config'
  return location.hash === '#logs' ? 'logs' : 'dashboard'
}
if (typeof window !== 'undefined') {
  // "#config" typed in the address bar of an open page
  window.addEventListener('hashchange', () => {
    tracker.view = viewFromHash()
    const room = roomFromLocation(location.hash, location.search)
    if (room) tracker.prefillRoom = room
  })
}

const timers = new Map<string, ReturnType<typeof setTimeout>>()
const detailSeq = new Map<string, number>()
let freezeTimer: ReturnType<typeof setTimeout> | undefined
export const SEEN_FREEZE_MS = 1500

/** Drop cached details that belong to another seed (or whose card is closed on a snapshot). */
/** Details shown: the user's choice, or shown by default for a featured (active) slot. */
export function isOpen(name: string): boolean {
  return tracker.open[name] ?? !!tracker.featured[name]
}

/** Dashboard: the slots shown in the featured area; their details are loaded when they become featured. */
export function setFeatured(names: string[]): void {
  const before = tracker.featured
  tracker.featured = Object.fromEntries(names.map((n) => [n, true]))
  for (const n of names) if (!before[n] && isOpen(n) && !tracker.details[n]) void loadDetail(n)
}

function pruneDetails(snapshot: boolean): void {
  for (const n of Object.keys(tracker.details)) {
    const s = tracker.slots.find((x) => x.name === n)
    const d = tracker.details[n]
    const stale = !s || (s.seed_name != null && d.seed_name != null && s.seed_name !== d.seed_name)
    if (stale || (snapshot && !isOpen(n))) {
      delete tracker.details[n]
      detailSeq.set(n, (detailSeq.get(n) ?? 0) + 1) // invalidate in-flight requests
    }
  }
}

export function setView(v: View): void {
  tracker.view = v
  try {
    if (v !== 'dashboard') location.hash = v
    else if (location.hash) history.replaceState(null, '', location.pathname + location.search)
  } catch {
    /* ignore */
  }
}

/** Reload /api/slots (server, room link, room error) e.g. after saving the config. */
export async function refreshMeta(): Promise<void> {
  try {
    const r = await api.getSlots()
    tracker.server = r.server
    tracker.roomUrl = r.room_url ?? ''
    tracker.roomError = r.room_error ?? ''
    tracker.roomSleeping = !!r.room_sleeping
    syncClock(r.now)
  } catch {
    /* ignore */
  }
}

export function dispatch(ev: TrackerEvent): void {
  const before = ev.type === 'slot' ? tracker.slots.find((s) => s.name === ev.slot.name) : undefined
  Object.assign(tracker, reduce(tracker, ev))
  if (ev.type === 'snapshot' || !before || before.items.received !== ev.slot.items.received || before.items.new !== ev.slot.items.new)
    scheduleRecent()
  pruneDetails(ev.type === 'snapshot')
  if (ev.type === 'slot' && isOpen(ev.slot.name)) scheduleDetail(ev.slot.name)
  if (ev.type === 'snapshot') {
    for (const s of tracker.slots) if (isOpen(s.name)) scheduleDetail(s.name)
  }
}

let recentTimer: ReturnType<typeof setTimeout> | undefined
let recentSeq = 0
/** Reload the feed of received items (grouped: items often arrive in bursts). */
export function scheduleRecent(delay = 1000): void {
  clearTimeout(recentTimer)
  recentTimer = setTimeout(() => void loadRecent(), delay)
}
export async function loadRecent(): Promise<void> {
  const seq = ++recentSeq
  try {
    const r = await api.getRecentItems()
    if (seq === recentSeq && Array.isArray(r.items)) tracker.recent = r.items
  } catch {
    /* the feed keeps its last content; the next change retries */
  }
}

export function scheduleDetail(name: string, delay = 300): void {
  clearTimeout(timers.get(name))
  timers.set(
    name,
    setTimeout(() => void loadDetail(name), delay),
  )
}

export async function loadDetail(name: string): Promise<void> {
  const seq = (detailSeq.get(name) ?? 0) + 1
  detailSeq.set(name, seq)
  try {
    const d = await api.getSlot(name)
    if (detailSeq.get(name) !== seq) return // a newer request superseded this one
    tracker.details[name] = d
    delete tracker.detailError[name]
  } catch (e) {
    if (detailSeq.get(name) !== seq) return
    tracker.detailError[name] = e instanceof Error ? e.message : String(e)
  }
}

export function toggleOpen(name: string): void {
  const v = !isOpen(name)
  tracker.open[name] = v
  if (v) {
    delete tracker.detailError[name]
    const s = tracker.slots.find((x) => x.name === name)
    const d = tracker.details[name]
    if (d && s && s.seed_name != null && d.seed_name != null && s.seed_name !== d.seed_name) {
      delete tracker.details[name]
    }
    void loadDetail(name)
  }
}

export async function markSeen(name: string): Promise<void> {
  tracker.seenFreeze = true
  clearTimeout(freezeTimer)
  freezeTimer = setTimeout(() => (tracker.seenFreeze = false), SEEN_FREEZE_MS)
  await api.markSeen(name)
  // invalidate any detail request started before markSeen resolved
  detailSeq.set(name, (detailSeq.get(name) ?? 0) + 1)
  const s = tracker.slots.find((x) => x.name === name)
  if (s) s.items.new = 0
  tracker.recent.forEach((i) => i.slot === name && (i.new = false))
  const d = tracker.details[name]
  if (d) {
    d.items.new = 0
    d.items_list.forEach((i) => (i.new = false))
  }
  clearTimeout(freezeTimer)
  freezeTimer = setTimeout(() => (tracker.seenFreeze = false), SEEN_FREEZE_MS)
  if (isOpen(name)) void loadDetail(name)
}

let es: EventSource | null = null
let retryTimer: ReturnType<typeof setTimeout> | undefined
let backoff = 3000
const BACKOFF_MAX = 30000

function parse(e: Event): any | null {
  try {
    return JSON.parse((e as MessageEvent).data)
  } catch (err) {
    console.warn('Événement SSE malformé ignoré', err)
    return null
  }
}

export function connect(): void {
  if (typeof EventSource === 'undefined') return
  es?.close()
  clearTimeout(retryTimer)
  const cur = new EventSource('/api/events')
  es = cur
  cur.onopen = () => {
    backoff = 3000
    tracker.sse = 'open'
    tracker.loadError = ''
  }
  cur.onerror = () => {
    tracker.sse = 'reconnecting'
    if (cur.readyState === EventSource.CLOSED) {
      // HTTP error: the browser will not retry by itself
      cur.close()
      if (es === cur) es = null
      const delay = backoff
      backoff = Math.min(backoff * 2, BACKOFF_MAX)
      retryTimer = setTimeout(connect, delay)
    }
  }
  cur.addEventListener('snapshot', (e) => {
    const d = parse(e)
    if (d && Array.isArray(d.slots)) dispatch({ type: 'snapshot', slots: d.slots })
  })
  cur.addEventListener('room', (e) => {
    const d = parse(e)
    if (!d) return
    tracker.server = typeof d.server === 'string' ? d.server : ''
    tracker.roomUrl = d.room_url ?? ''
    tracker.roomError = d.room_error ?? ''
    tracker.roomSleeping = !!d.room_sleeping
  })
  cur.addEventListener('slot', (e) => {
    const d = parse(e)
    if (d && d.slot) dispatch({ type: 'slot', slot: d.slot })
  })
}

let clock: ReturnType<typeof setInterval> | undefined
let offset = 0
function syncClock(serverNow: number | undefined): void {
  offset = clockOffset(serverNow)
  tracker.nowMs = Date.now() + offset
}

export async function start(): Promise<void> {
  stop()
  connect()
  clock = setInterval(() => (tracker.nowMs = Date.now() + offset), 30_000)
  try {
    const r = await api.getSlots()
    dispatch({ type: 'snapshot', slots: r.slots, server: r.server })
    tracker.roomUrl = r.room_url ?? ''
    tracker.roomError = r.room_error ?? ''
    tracker.roomSleeping = !!r.room_sleeping
    syncClock(r.now)
  } catch (e) {
    tracker.loadError = e instanceof Error ? e.message : String(e)
  }
}

export function stop(): void {
  clearTimeout(retryTimer)
  clearInterval(clock)
  clearTimeout(recentTimer)
  backoff = 3000
  es?.close()
  es = null
}

if (import.meta.hot) import.meta.hot.dispose(() => stop())
