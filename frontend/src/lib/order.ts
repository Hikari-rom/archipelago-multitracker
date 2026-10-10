import type { SlotSummary } from './types'

/**
 * Keep the displayed order stable while `frozen`: slots keep their position from
 * `prevOrder`, unknown (new) slots are appended in sorted order. Data is always the latest.
 */
export function stableOrder(prevOrder: string[], sorted: SlotSummary[], frozen: boolean): SlotSummary[] {
  if (!frozen) return sorted
  const pos = new Map(prevOrder.map((n, i) => [n, i]))
  const known = sorted.filter((s) => pos.has(s.name)).sort((a, b) => pos.get(a.name)! - pos.get(b.name)!)
  const added = sorted.filter((s) => !pos.has(s.name))
  return [...known, ...added]
}
