// "Objectifs" page and the goal line of the dashboard cards.
import type { GoalCounter, GoalNeedHint, GoalNeedItem, Objective, SlotSummary } from './types'

/** The counter shown on a card: the first one not reached yet (or the last one when all are). */
export function mainCounter(o: Objective | null | undefined): GoalCounter | null {
  if (!o || !o.counters.length) return null
  return o.counters.find((c) => c.current < c.target) ?? o.counters[o.counters.length - 1]
}

/** Share of the goal done, 0 to 1: counters (capped) and known steps, the goal step excluded. 1 once reached. */
export function goalProgress(s: Pick<SlotSummary, 'goal' | 'objective'>): number {
  if (s.goal) return 1
  const o = s.objective
  if (!o) return 0
  const parts = [
    ...o.counters.map((c) => Math.min(1, c.current / c.target)),
    ...o.steps.slice(0, -1).filter((st) => st.done !== null).map((st) => (st.done ? 1 : 0)),
  ]
  return parts.length ? parts.reduce((a, b) => a + b, 0) / parts.length : 0
}

/** Games not finished first, the most advanced first; then finished games; games without description last. */
export function sortByGoal(slots: SlotSummary[]): SlotSummary[] {
  const group = (s: SlotSummary) => (s.goal ? 1 : s.objective ? 0 : 2)
  return slots
    .map((s, i) => ({ s, i, p: goalProgress(s) }))
    .sort((a, b) => group(a.s) - group(b.s) || b.p - a.p || a.i - b.i)
    .map((x) => x.s)
}

export function counterText(c: GoalCounter): string {
  return `${c.current} / ${c.target}`
}

export const SOURCE_LABELS: Record<string, string> = {
  slot_data: 'options lues dans le slot_data du serveur',
  yaml: 'options lues dans le yaml du joueur',
  'slot_data + yaml': 'options lues dans le slot_data du serveur et le yaml du joueur',
  'mod + slot_data': 'options lues dans le slot_data, victoires lues dans le profil du mod',
}

/** An item the victory needs (D41): « Dark Eco Crystal ×3 ». */
export function needLabel(n: Pick<GoalNeedItem, 'name' | 'count'>): string {
  return n.count > 1 ? `${n.name} ×${n.count}` : n.name
}

/** Copies the victory still needs, all items together. */
export function needsCount(o: Objective | null | undefined): number {
  const n = o?.needs
  return n?.kind === 'set' ? n.items.reduce((sum, i) => sum + i.count, 0) : 0
}

export const NEED_ACCESS: Record<GoalNeedHint['access'], string> = {
  ok: 'check faisable maintenant',
  blocked: 'check pas encore en logique',
  pending: 'logique en cours de calcul',
  unknown: 'accès inconnu',
  found: 'trouvé',
}
