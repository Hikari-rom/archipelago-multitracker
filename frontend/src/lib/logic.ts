import type { Hint, LogicLocation, SlotSummary } from './types'

/** "BK" (stuck): logic computed, nothing in logic, game not finished. Waiting for items from the others. */
export const isBK = (s: SlotSummary): boolean =>
  s.logic.state === 'ok' && s.logic.count === 0 && !s.goal && s.checks.remaining > 0

export type BadgeVariant = 'good' | 'neutral' | 'muted' | 'pending'
export interface Badge {
  text: string
  variant: BadgeVariant
  secondary?: string
}

export function logicBadge(s: SlotSummary): Badge {
  const l = s.logic
  if (l.state === 'ok') {
    if (l.count > 0) {
      return {
        text: `Tu peux avancer : ${l.count} ${l.count === 1 ? 'check' : 'checks'} en logique`,
        variant: 'good',
        secondary: l.message ?? undefined,
      }
    }
    return { text: "Rien en logique pour l'instant", variant: 'neutral', secondary: l.message ?? undefined }
  }
  if (l.state === 'pending') {
    if (s.status !== 'connected') return { text: 'En attente de connexion', variant: 'pending' }
    return { text: 'Calcul de la logique…', variant: 'pending' }
  }
  return {
    text: 'Logique indisponible pour ce jeu',
    variant: 'muted',
    secondary: l.message ?? undefined,
  }
}

/** Short, readable connection problem for a card (the raw error stays available as a tooltip). */
export function connectionMessage(s: Pick<SlotSummary, 'status' | 'error'>, roomSleeping: boolean): string {
  if (s.status === 'connected') return ''
  if (roomSleeping) return 'Room endormie : connexion automatique dès qu\'elle se réveille.'
  const e = s.error || ''
  if (!e) return ''
  if (e.startsWith('connexion refusée')) return e
  if (/ConnectionError|ConnectionRefused|TimeoutError|OSError|adresse du serveur inconnue/.test(e))
    return 'Serveur injoignable, nouvel essai automatique.'
  return e.length > 160 ? e.slice(0, 157) + '…' : e
}

export function logicUnavailable(s: SlotSummary): boolean {
  return s.logic.state === 'unavailable' || s.logic.state === 'error'
}

export function hasSomethingToDo(s: SlotSummary): boolean {
  return (
    (s.logic.state === 'ok' && s.logic.count > 0) ||
    s.items.new > 0 ||
    s.hints.in_my_world_in_logic > 0
  )
}

export const DEFAULT_ACTIVE_MINUTES = 30

/** The player's own say on "active" (this device): one game chosen by hand, games set inactive by hand. */
export interface ActivityOverrides {
  /** game chosen as active ("Définir comme actif"), and when (epoch seconds) */
  pinned: { name: string; at: number } | null
  /** games set inactive by hand ("Plus actif"): their last check at that moment (0: none). They become active
   * again with their next check. */
  dismissed: Record<string, number>
}
export const NO_OVERRIDES: ActivityOverrides = { pinned: null, dismissed: {} }

/** "Active" = the slot checked a location recently (the server's client status cannot tell, see DECISIONS D11),
 * unless set inactive by hand since; the game chosen by hand is always active, and once one is chosen the other
 * games are active only with a check made after that choice. */
export function isActive(
  s: SlotSummary,
  nowMs: number,
  minutes = DEFAULT_ACTIVE_MINUTES,
  ov: ActivityOverrides = NO_OVERRIDES,
): boolean {
  if (ov.pinned?.name === s.name) return true
  const last = s.last_check_at
  if (s.goal || !last || nowMs / 1000 - last >= minutes * 60) return false
  if (ov.pinned && last <= ov.pinned.at) return false
  const dismissed = ov.dismissed[s.name]
  return dismissed === undefined || last > dismissed
}

const inLogic = (s: SlotSummary) => (s.logic.state === 'ok' ? s.logic.count : 0)

/** Active games first, then the most checks in logic, then the most checks left; finished games last. */
export function sortSlots(
  slots: SlotSummary[],
  nowMs = Date.now(),
  activeMinutes = DEFAULT_ACTIVE_MINUTES,
  ov: ActivityOverrides = NO_OVERRIDES,
): SlotSummary[] {
  const group = (s: SlotSummary) => (isActive(s, nowMs, activeMinutes, ov) ? 0 : s.goal ? 2 : 1)
  return slots
    .map((s, i) => ({ s, i }))
    .sort((a, b) => {
      const ga = group(a.s)
      const gb = group(b.s)
      if (ga !== gb) return ga - gb
      return (
        inLogic(b.s) - inLogic(a.s) ||
        b.s.checks.remaining - a.s.checks.remaining ||
        b.s.hints.in_my_world_in_logic - a.s.hints.in_my_world_in_logic ||
        b.s.items.new - a.s.items.new ||
        a.i - b.i
      )
    })
    .map((x) => x.s)
}

export function countToDo(slots: SlotSummary[]): number {
  return slots.filter((s) => !s.goal && s.logic.state === 'ok' && s.logic.count > 0).length
}

export function summaryText(slots: SlotSummary[]): string {
  const n = countToDo(slots)
  if (n === 0) return 'Aucun jeu où avancer en logique'
  return `${n} ${n === 1 ? 'jeu' : 'jeux'} où avancer`
}

/** "Objet → check ∆ monde" (asked by Romain: shorter than a sentence). */
export function hintMineElsewhere(h: Hint): string {
  return `${h.item} → ${h.location} ∆ ${h.finder} (${h.finder_game})`
}

export function hintInMyWorld(h: Hint): string {
  return `${h.location} contient ${h.item} pour ${h.receiver}`
}

export function statusLabel(status: SlotSummary['status']): string {
  return (
    {
      connected: 'Connecté',
      connecting: 'Connexion…',
      disconnected: 'Déconnecté',
      error: 'Erreur',
      idle: 'En attente',
    } as const
  )[status]
}

export function pluralize(n: number, one: string, many: string): string {
  return `${n} ${n === 1 ? one : many}`
}

export interface LocationGroup {
  title: string | null
  locations: LogicLocation[]
}

/** Prefix of a location name used as an area: "FJ: Foo" -> "FJ", "Forsaken City - Foo" -> "Forsaken City". */
export function namePrefix(name: string): string | null {
  const m = /^(.{2,40}?)(?::\s| - )/.exec(name)
  return m ? m[1].trim() : null
}

function groupBy(locs: LogicLocation[], key: (l: LogicLocation) => string | null): Map<string, LogicLocation[]> {
  const out = new Map<string, LogicLocation[]>()
  for (const l of locs) {
    const k = key(l) || 'Autres'
    if (!out.has(k)) out.set(k, [])
    out.get(k)!.push(l)
  }
  return out
}

/** Hinted locations first; long lists are grouped by region or by name prefix, whichever gives
 * readable groups (several groups, about 3+ locations each on average); otherwise a flat list. */
export function groupLocations(locs: LogicLocation[], threshold = 12): LocationGroup[] {
  const hinted = locs.filter((l) => l.hint)
  const rest = locs.filter((l) => !l.hint)
  const groups: LocationGroup[] = []
  if (hinted.length) groups.push({ title: 'Hintées', locations: hinted })
  let best: Map<string, LogicLocation[]> | null = null
  if (locs.length > threshold) {
    for (const key of [(l: LogicLocation) => l.region ?? null, (l: LogicLocation) => namePrefix(l.name)]) {
      if (!rest.some((l) => key(l))) continue
      const g = groupBy(rest, key)
      const readable = g.size > 1 && rest.length / g.size >= 3
      if (readable && (!best || g.size < best.size)) best = g
    }
  }
  if (!best) {
    if (rest.length) groups.push({ title: hinted.length ? 'Autres' : null, locations: rest })
    return groups
  }
  const byName = (a: string, b: string) => Number(a === 'Autres') - Number(b === 'Autres') || a.localeCompare(b)
  for (const key of [...best.keys()].sort(byName)) {
    groups.push({ title: key, locations: best.get(key)! })
  }
  return groups
}
