// Locations in logic grouped by region of the game (Focus panel, card details).
import type { LogicLocation } from '../../lib/types'

export interface RegionGroup { name: string; count: number; hinted: number; locations: LogicLocation[] }
export const OTHER_REGION = 'Autres'

export function regionsOf(locs: LogicLocation[]): RegionGroup[] {
  const by = new Map<string, LogicLocation[]>()
  for (const l of locs) {
    const k = l.region || OTHER_REGION
    by.set(k, [...(by.get(k) ?? []), l])
  }
  return [...by.entries()]
    .map(([name, ls]) => ({
      name,
      count: ls.length,
      hinted: ls.filter((l) => l.hint).length,
      locations: [...ls.filter((l) => l.hint), ...ls.filter((l) => !l.hint)],
    }))
    .sort((a, b) =>
      (a.name === OTHER_REGION ? 1 : 0) - (b.name === OTHER_REGION ? 1 : 0) ||
      b.count - a.count || b.hinted - a.hinted || a.name.localeCompare(b.name))
}
