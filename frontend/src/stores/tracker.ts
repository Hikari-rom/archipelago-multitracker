import { reactive } from 'vue'
import * as api from '../lib/api'

import { initialState, reduce, type TrackerEvent } from '../lib/state'
import type { SlotDetail, SseState } from '../lib/types'

export const tracker = reactive({
  ...initialState(),
  sse: 'connecting' as SseState,
  loadError: '' as string,
  details: {} as Record<string, SlotDetail>,
  open: {} as Record<string, boolean>,
})

const timers = new Map<string, ReturnType<typeof setTimeout>>()

export function dispatch(ev: TrackerEvent): void {
  Object.assign(tracker, reduce(tracker, ev))
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
  try {
    tracker.details[name] = await api.getSlot(name)
  } catch {
    /* keep stale detail */
  }
}

export function toggleOpen(name: string): void {
  const v = !tracker.open[name]
  tracker.open[name] = v
  if (v) void loadDetail(name)
}

export async function markSeen(name: string): Promise<void> {
  await api.markSeen(name)
  const s = tracker.slots.find((x) => x.name === name)
  if (s) s.items.new = 0
  const d = tracker.details[name]
  if (d) {
    d.items.new = 0
    d.items_list.forEach((i) => (i.new = false))
  }
}

let es: EventSource | null = null

export async function start(): Promise<void> {
  try {
    const r = await api.getSlots()
    dispatch({ type: 'snapshot', slots: r.slots, server: r.server })
  } catch (e) {
    tracker.loadError = e instanceof Error ? e.message : String(e)
  }
  if (typeof EventSource === 'undefined') return
  es = new EventSource('/api/events')
  es.onopen = () => {
    tracker.sse = 'open'
    tracker.loadError = ''
  }
  es.onerror = () => {
    tracker.sse = 'reconnecting'
  }
  es.addEventListener('snapshot', (e) => {
    const d = JSON.parse((e as MessageEvent).data)
    dispatch({ type: 'snapshot', slots: d.slots })
  })
  es.addEventListener('slot', (e) => {
    const d = JSON.parse((e as MessageEvent).data)
    dispatch({ type: 'slot', slot: d.slot })
  })
}

export function stop(): void {
  es?.close()
  es = null
}
