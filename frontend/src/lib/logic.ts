import type { Hint, SlotSummary } from './types'

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
      }
    }
    return { text: "Rien en logique pour l'instant", variant: 'neutral' }
  }
  if (l.state === 'pending') return { text: 'Calcul de la logique…', variant: 'pending' }
  return {
    text: 'Logique indisponible pour ce jeu',
    variant: 'muted',
    secondary: l.message ?? undefined,
  }
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

function group(s: SlotSummary): number {
  if (s.goal) return 2
  return hasSomethingToDo(s) ? 0 : 1
}

export function sortSlots(slots: SlotSummary[]): SlotSummary[] {
  return slots
    .map((s, i) => ({ s, i }))
    .sort((a, b) => {
      const ga = group(a.s)
      const gb = group(b.s)
      if (ga !== gb) return ga - gb
      if (ga === 0) {
        const d =
          b.s.hints.in_my_world_in_logic - a.s.hints.in_my_world_in_logic ||
          (b.s.logic.state === 'ok' ? b.s.logic.count : 0) -
            (a.s.logic.state === 'ok' ? a.s.logic.count : 0) ||
          b.s.items.new - a.s.items.new
        if (d) return d
      }
      return a.i - b.i
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

export function hintMineElsewhere(h: Hint): string {
  return `Ton ${h.item} est à ${h.location} dans le monde de ${h.finder} (${h.finder_game})`
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
