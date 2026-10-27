// Indices page: sorting, filtering and texts of the hints table (GET /api/hints).
import type { HintAccess, HintRow } from './types'

export const ACCESS_LABEL: Record<HintAccess['state'], string> = {
  ok: 'Accessible',
  blocked: 'Bloqué',
  pending: 'En calcul',
  unknown: 'Inconnu',
  found: 'Trouvé',
}
const ACCESS_RANK: Record<HintAccess['state'], number> = { ok: 0, blocked: 1, pending: 2, unknown: 3, found: 4 }

/** Hint status set by the players (AP 0.6): priority first. */
export const STATUS_LABEL: Record<string, string> = {
  priority: 'Prioritaire',
  unspecified: '—',
  no_priority: 'Sans priorité',
  avoid: 'À éviter',
  found: 'Trouvé',
}
const STATUS_RANK: Record<string, number> = { priority: 0, unspecified: 1, no_priority: 2, avoid: 3, found: 4 }

const MAX_LISTED = 5

function list(names: string[]): string {
  const shown = names.slice(0, MAX_LISTED).join(', ')
  return names.length > MAX_LISTED ? `${shown}… (+${names.length - MAX_LISTED})` : shown
}

/** Why the check cannot be done yet (or why we do not know), in one line. */
export function accessDetail(a: HintAccess): string {
  if (a.state === 'pending' || a.state === 'unknown') return a.reason ?? ''
  if (a.state !== 'blocked') return ''
  const b = a.blockers
  if (!b) return 'Il manque des items'
  if (b.kind === 'single') return b.items.length === 1 ? `Il manque : ${b.items[0]}` : `Un seul de ces items suffit : ${list(b.items)}`
  if (b.kind === 'set') return `Il manque : ${list(b.items.map(([n, c]) => (c > 1 ? `${n} ×${c}` : n)))}`
  if (b.kind === 'many') return 'Il manque plusieurs items'
  return 'Hors logique, même avec tous les items restants'
}

export type HintColumn = 'receiver' | 'item' | 'finder' | 'location' | 'status' | 'access' | 'found' | 'dir' | 'other'

export const COLUMN_LABEL: Record<HintColumn, string> = {
  receiver: 'Pour',
  item: 'Item',
  finder: 'Chez',
  location: 'Location',
  status: 'Priorité',
  access: 'Accessible',
  found: 'Trouvé',
  dir: 'Sens',
  other: 'Avec',
}

/** Who has to do the check: one of `mine` (a tracked slot of the selection) or someone else. */
export function doneBy(h: HintRow, mine: Set<string>): 'me' | 'other' {
  return h.finder_slot && mine.has(h.finder_slot) ? 'me' : 'other'
}

function text(v: string | null | undefined): string {
  return (v ?? '').toLocaleLowerCase('fr')
}

/** Sort key of a row for a column; `context`: the slot of the group (layout « par slot »). */
export function sortValue(h: HintRow, key: string, context?: string): string | number {
  switch (key) {
    case 'receiver':
      return text(h.receiver)
    case 'item':
      return text(h.item)
    case 'finder':
      return text(h.finder)
    case 'location':
      return text(h.location)
    case 'status':
      return STATUS_RANK[h.status ?? 'unspecified'] ?? 1
    case 'access':
      return ACCESS_RANK[h.access.state] * 1000 + (h.access.state === 'blocked' ? blockerRank(h) : 0)
    case 'found':
      return h.found ? 1 : 0
    case 'dir':
      return context && h.finder_slot === context ? 0 : 1
    case 'other':
      return text(context && h.finder_slot === context ? h.receiver : h.finder)
    default:
      return 0
  }
}

/** Blocked hints closest to being doable first: one item missing, then a few, then unknown. */
function blockerRank(h: HintRow): number {
  const b = h.access.blockers
  if (!b) return 500
  if (b.kind === 'single') return 1
  if (b.kind === 'set') return 10 + b.items.reduce((n, [, c]) => n + c, 0)
  return b.kind === 'many' ? 600 : 700
}

export function sortHints(rows: HintRow[], key: string, dir: 1 | -1, context?: string): HintRow[] {
  const tie = (a: HintRow, b: HintRow) =>
    (sortValue(a, 'access') as number) - (sortValue(b, 'access') as number) ||
    (sortValue(a, 'status') as number) - (sortValue(b, 'status') as number) ||
    text(a.item).localeCompare(text(b.item), 'fr')
  return [...rows].sort((a, b) => {
    const x = sortValue(a, key, context)
    const y = sortValue(b, key, context)
    const c = typeof x === 'number' && typeof y === 'number' ? x - y : String(x).localeCompare(String(y), 'fr')
    return c * dir || tie(a, b)
  })
}

export function matchesQuery(h: HintRow, q: string): boolean {
  const n = q.trim().toLocaleLowerCase('fr')
  if (!n) return true
  return [h.item, h.location, h.finder, h.receiver, h.finder_game, h.receiver_game, h.entrance].some((v) => text(v).includes(n))
}

export type HintsFilter = 'all' | 'mine' | 'world' | 'ok'
export const FILTER_LABEL: Record<HintsFilter, string> = {
  all: 'Tous',
  mine: 'Mes items',
  world: 'Dans mes mondes',
  ok: 'Accessibles',
}

/** Rows of the selected slots, after the page's filters. */
export function filterHints(rows: HintRow[], mine: Set<string>, opts: { filter: HintsFilter; query: string; hideFound: boolean }): HintRow[] {
  return rows.filter((h) => {
    if (!h.slots.some((n) => mine.has(n))) return false
    if (opts.hideFound && h.access.state === 'found') return false
    if (opts.filter === 'mine' && !(h.receiver_slot && mine.has(h.receiver_slot))) return false
    if (opts.filter === 'world' && doneBy(h, mine) !== 'me') return false
    if (opts.filter === 'ok' && h.access.state !== 'ok') return false
    return matchesQuery(h, opts.query)
  })
}

/** Layout « par slot »: one group per selected slot (a hint between two of them is in both). */
export function groupBySlot(rows: HintRow[], slots: { name: string; game: string }[]) {
  return slots
    .map((s) => {
      const own = rows.filter((h) => h.slots.includes(s.name))
      return {
        name: s.name,
        game: s.game,
        rows: own,
        ok: own.filter((h) => h.access.state === 'ok').length,
        blocked: own.filter((h) => h.access.state === 'blocked').length,
      }
    })
    .filter((g) => g.rows.length)
}
