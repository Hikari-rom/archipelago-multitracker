// Dashboard: totals of the selected slots, sort modes, two-colour progress bars, feed of received items.
import { isActive, NO_OVERRIDES, sortSlots, type ActivityOverrides } from './logic'
import type { RecentItem, SlotSummary } from './types'

export interface Totals {
  done: number
  total: number
  inLogic: number
  newItems: number
}

const inLogic = (s: SlotSummary) => (s.logic.state === 'ok' ? s.logic.count : 0)

export function totals(slots: SlotSummary[]): Totals {
  const t: Totals = { done: 0, total: 0, inLogic: 0, newItems: 0 }
  for (const s of slots) {
    t.done += s.checks.done
    t.total += s.checks.total
    t.inLogic += s.goal ? 0 : inLogic(s)
    t.newItems += s.items.new
  }
  return t
}

export interface BarParts {
  /** percentages of the bar width */
  done: number
  logic: number
}

/** Green part = checks done, blue part = checks in logic, both out of the game's total. */
export function barParts(done: number, logic: number, total: number): BarParts {
  if (total <= 0) return { done: 0, logic: 0 }
  const d = Math.min(100, (done / total) * 100)
  return { done: d, logic: Math.min(100 - d, (logic / total) * 100) }
}

export function percent(n: number, total: number): number {
  return total > 0 ? Math.round((n / total) * 100) : 0
}

export type SortMode = 'auto' | 'count' | 'percent'
export const SORT_LABELS: Record<SortMode, string> = { auto: 'Conseillé', count: 'En logique', percent: '% en logique' }

/** Checks in logic out of the game's total; null when the logic is not known (sorted after the others). */
export function logicShare(s: SlotSummary): number | null {
  if (s.logic.state !== 'ok') return null
  return s.checks.total > 0 ? s.logic.count / s.checks.total : 0
}

/** "auto": the recommended order (see sortSlots). "count" / "percent": most checks in logic first, as a number
 * or as a share of the game; games without logic, then finished games, at the end; ties keep the "auto" order. */
export function sortBy(
  mode: SortMode,
  slots: SlotSummary[],
  nowMs = Date.now(),
  activeMinutes?: number,
  ov: ActivityOverrides = NO_OVERRIDES,
): SlotSummary[] {
  const auto = sortSlots(slots, nowMs, activeMinutes, ov)
  if (mode === 'auto') return auto
  const value = (s: SlotSummary): number => {
    if (s.goal) return -2
    const v = mode === 'count' ? (s.logic.state === 'ok' ? s.logic.count : null) : logicShare(s)
    return v ?? -1
  }
  const rank = new Map(auto.map((s, i) => [s.name, i]))
  return [...auto].sort((a, b) => value(b) - value(a) || rank.get(a.name)! - rank.get(b.name)!)
}

const SORT_KEY = 'amt-sort'
export function loadSortMode(): SortMode {
  try {
    const v = localStorage.getItem(SORT_KEY)
    if (v === 'auto' || v === 'count' || v === 'percent') return v
  } catch {
    /* ignore */
  }
  return 'auto'
}
export function saveSortMode(v: SortMode): void {
  try {
    localStorage.setItem(SORT_KEY, v)
  } catch {
    /* ignore */
  }
}

/** Active games (a location checked in the last minutes, or chosen by hand) go first, in full-width cards: the
 * game chosen by hand, then the most recent first; the other games keep the chosen order. */
export function splitFeatured(
  slots: SlotSummary[],
  nowMs: number,
  activeMinutes?: number,
  ov: ActivityOverrides = NO_OVERRIDES,
) {
  const pinnedFirst = (s: SlotSummary) => (ov.pinned?.name === s.name ? 0 : 1)
  const featured = slots
    .filter((s) => isActive(s, nowMs, activeMinutes, ov))
    .sort((a, b) => pinnedFirst(a) - pinnedFirst(b) || (b.last_check_at ?? 0) - (a.last_check_at ?? 0))
  const names = new Set(featured.map((s) => s.name))
  return { featured, rest: slots.filter((s) => !names.has(s.name)) }
}

export const FEED_SHORT = 5
/** on a phone (< 700 px) the short feed shows fewer items, so the active game stays near the top */
export const FEED_PHONE = 3
export const FEED_LONG = 30

/** Feed of the selected slots (already newest first from the server). */
export function feedItems(items: RecentItem[], slotNames: Set<string>, limit: number): RecentItem[] {
  return items.filter((i) => slotNames.has(i.slot)).slice(0, limit)
}

export type Layout = 'cards' | 'compact'
export const LAYOUT_LABELS: Record<Layout, string> = { cards: 'Cartes', compact: 'Compact' }
const LAYOUT_KEY = 'amt-layout'
export function loadLayout(): Layout {
  try {
    if (localStorage.getItem(LAYOUT_KEY) === 'compact') return 'compact'
  } catch {
    /* ignore */
  }
  return 'cards'
}
export function saveLayout(v: Layout): void {
  try {
    localStorage.setItem(LAYOUT_KEY, v)
  } catch {
    /* ignore */
  }
}

/** Compact layout: the one game shown in full. The game chosen by hand, else the active game with the most recent
 * check, else the first game of the list (already sorted). */
export function compactMain(
  slots: SlotSummary[],
  nowMs: number,
  activeMinutes?: number,
  ov: ActivityOverrides = NO_OVERRIDES,
): SlotSummary | null {
  return splitFeatured(slots, nowMs, activeMinutes, ov).featured[0] ?? slots[0] ?? null
}
