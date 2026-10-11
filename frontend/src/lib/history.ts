import type { ItemEntry } from './types'

export type HistoryFilter = 'all' | 'progression' | 'useful'
export const HISTORY_PAGE = 50

/** Newest first; items received before the app tracked the slot (no time) keep the server order, at the end. */
export function historyItems(items: ItemEntry[], filter: HistoryFilter): ItemEntry[] {
  const keep =
    filter === 'progression' ? (i: ItemEntry) => i.progression : filter === 'useful' ? (i: ItemEntry) => i.useful : () => true
  return items.filter(keep).sort((a, b) => b.index - a.index)
}

const two = (n: number) => String(n).padStart(2, '0')
const hm = (d: Date) => `${two(d.getHours())}:${two(d.getMinutes())}`
const MONTHS = ['janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.']

/** "à l'instant", "il y a 12 min", "aujourd'hui 14:02", "hier 21:14", "3 oct. 09:30" or "avant le suivi". */
export function formatWhen(ts: number | null | undefined, nowMs = Date.now()): string {
  if (ts == null) return 'avant le suivi'
  const ms = ts * 1000
  const diff = nowMs - ms
  if (diff < 60_000) return "à l'instant"
  if (diff < 3_600_000) return `il y a ${Math.floor(diff / 60_000)} min`
  const d = new Date(ms)
  const today = new Date(nowMs)
  const yesterday = new Date(nowMs - 86_400_000)
  const same = (x: Date, y: Date) => x.toDateString() === y.toDateString()
  if (same(d, today)) return `aujourd'hui ${hm(d)}`
  if (same(d, yesterday)) return `hier ${hm(d)}`
  return `${d.getDate()} ${MONTHS[d.getMonth()]} ${hm(d)}`
}

/** Time of an item of the history; items received while the app was not watching the slot come with a range. */
export function formatReceived(item: Pick<ItemEntry, 'received_at' | 'received_after'>, nowMs = Date.now()): string {
  if (item.received_at != null && item.received_after != null)
    return `${formatWhen(item.received_after, nowMs)} → ${formatWhen(item.received_at, nowMs)}`
  return formatWhen(item.received_at, nowMs)
}
export function receivedTitle(item: Pick<ItemEntry, 'received_at' | 'received_after'>): string {
  if (item.received_at == null) return "Reçu avant que l'app suive ce slot : heure inconnue"
  if (item.received_after != null) return "Reçu pendant que l'app ne suivait pas ce slot (app arrêtée, room endormie…), entre ces deux moments"
  return ''
}

/** Difference between the server clock (epoch seconds from /api/slots) and this device's clock, in ms. Times
 * shown are server times, so "active" and "il y a 3 min" are computed on the server clock. */
export function clockOffset(serverNow: number | null | undefined, localMs = Date.now()): number {
  return typeof serverNow === 'number' && Number.isFinite(serverNow) ? serverNow * 1000 - localMs : 0
}

const KEY = 'amt-active-minutes'
export const ACTIVE_CHOICES = [10, 30, 60, 120]
export function loadActiveMinutes(): number {
  try {
    const v = Number(localStorage.getItem(KEY))
    if (ACTIVE_CHOICES.includes(v)) return v
  } catch {
    /* ignore */
  }
  return 30
}
export function saveActiveMinutes(v: number): void {
  try {
    localStorage.setItem(KEY, String(v))
  } catch {
    /* ignore */
  }
}
