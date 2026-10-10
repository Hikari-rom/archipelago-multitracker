import { reactive } from 'vue'
import * as api from '../lib/api'
import { roomFromLocation } from '../lib/config'

import { initialState, reduce, type TrackerEvent } from '../lib/state'
import type { SlotDetail, SseState } from '../lib/types'

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
  details: {} as Record<string, SlotDetail>,
  open: {} as Record<string, boolean>,
  detailError: {} as Record<string, string>,
  /** true during the short window after "Marquer comme vu" (dashboard order frozen) */
  seenFreeze: false,
})

function viewFromHash(): 'dashboard' | 'config' {
  return typeof location !== 'undefined' && /^#config(\?|$)/.test(location.hash) ? 'config' : 'dashboard'
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
function pruneDetails(snapshot: boolean): void {
  for (const n of Object.keys(tracker.details)) {
    const s = tracker.slots.find((x) => x.name === n)
    const d = tracker.details[n]
    const stale = !s || (s.seed_name != null && d.seed_name != null && s.seed_name !== d.seed_name)
    if (stale || (snapshot && !tracker.open[n])) {
      delete tracker.details[n]
      detailSeq.set(n, (detailSeq.get(n) ?? 0) + 1) // invalidate in-flight requests
    }
  }
}

export function setView(v: 'dashboard' | 'config'): void {
  tracker.view = v
  try {
    if (v === 'config') location.hash = 'config'
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
  } catch {
    /* ignore */
  }
}

export function dispatch(ev: TrackerEvent): void {
  Object.assign(tracker, reduce(tracker, ev))
  pruneDetails(ev.type === 'snapshot')
  if (ev.type === 'slot' && tracker.open[ev.slot.name]) scheduleDetail(ev.slot.name)
  if (ev.type === 'snapshot') {
    for (const n of Object.keys(tracker.open)) if (tracker.open[n]) scheduleDetail(n)
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
  const v = !tracker.open[name]
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
  const d = tracker.details[name]
  if (d) {
    d.items.new = 0
    d.items_list.forEach((i) => (i.new = false))
  }
  clearTimeout(freezeTimer)
  freezeTimer = setTimeout(() => (tracker.seenFreeze = false), SEEN_FREEZE_MS)
  if (tracker.open[name]) void loadDetail(name)
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

export async function start(): Promise<void> {
  stop()
  connect()
  try {
    const r = await api.getSlots()
    dispatch({ type: 'snapshot', slots: r.slots, server: r.server })
    tracker.roomUrl = r.room_url ?? ''
    tracker.roomError = r.room_error ?? ''
    tracker.roomSleeping = !!r.room_sleeping
  } catch (e) {
    tracker.loadError = e instanceof Error ? e.message : String(e)
  }
}

export function stop(): void {
  clearTimeout(retryTimer)
  backoff = 3000
  es?.close()
  es = null
}

if (import.meta.hot) import.meta.hot.dispose(() => stop())
