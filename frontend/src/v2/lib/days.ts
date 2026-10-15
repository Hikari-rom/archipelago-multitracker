// History page of the v2: entries grouped by day (device time), the source game shown once per run.
import { MONTHS } from '../../lib/history'

export interface DayRow<T> { entry: T; showSource: boolean }
export interface DayGroup<T> { key: string; label: string; rows: DayRow<T>[] }
export const BEFORE_TRACKING = 'Avant le suivi'

export function dayLabel(epochSeconds: number, nowMs: number): string {
  const d = new Date(epochSeconds * 1000)
  const today = new Date(nowMs)
  const yesterday = new Date(today.getFullYear(), today.getMonth(), today.getDate() - 1)
  if (d.toDateString() === today.toDateString()) return "Aujourd'hui"
  if (d.toDateString() === yesterday.toDateString()) return 'Hier'
  const base = `${d.getDate()} ${MONTHS[d.getMonth()]}`
  return d.getFullYear() === today.getFullYear() ? base : `${base} ${d.getFullYear()}`
}

export function groupByDay<T>(entries: T[], at: (e: T) => number | null, source: (e: T) => string, nowMs: number): DayGroup<T>[] {
  const groups: DayGroup<T>[] = []
  const before: T[] = []
  for (const e of entries) {
    const t = at(e)
    if (t == null) {
      before.push(e)
      continue
    }
    const key = new Date(t * 1000).toDateString()
    let g = groups[groups.length - 1]
    if (!g || g.key !== key) groups.push((g = { key, label: dayLabel(t, nowMs), rows: [] }))
    g.rows.push({ entry: e, showSource: true })
  }
  if (before.length) groups.push({ key: 'before', label: BEFORE_TRACKING, rows: before.map((entry) => ({ entry, showSource: true })) })
  for (const g of groups)
    g.rows.forEach((r, i) => (r.showSource = i === 0 || source(g.rows[i - 1].entry) !== source(r.entry)))
  return groups
}

export type Category = 'PROG' | 'UTILE' | 'PIÈGE'
// One colour mapping for the item badges, shared by the History page and the detail tabs.
export const CATEGORY_CLASS: Record<Category, string> = {
  PROG: 'bg-prog/15 text-prog',
  UTILE: 'bg-info text-info-foreground',
  PIÈGE: 'bg-warn text-warn-foreground',
}

/** Where a received item comes from, as shown in History and the detail tabs. */
export function itemOrigin(i: { origin?: string; sender?: string; location?: string | null; own?: boolean }): string {
  const who = i.origin === 'start' ? 'inventaire de départ' : i.origin === 'server' ? 'donné par le serveur' : i.own ? 'trouvé par toi' : `de ${i.sender}`
  return i.location && i.origin !== 'start' ? `${who} · ${i.location}` : who
}
export function category(i: { progression: boolean; useful: boolean; trap: boolean }): Category | null {
  if (i.trap) return 'PIÈGE'
  if (i.progression) return 'PROG'
  if (i.useful) return 'UTILE'
  return null
}
