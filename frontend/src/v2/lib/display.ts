export type InfoKey =
  | 'slot' | 'done' | 'remaining' | 'newItems' | 'hints' | 'regions' | 'goal' | 'activity' | 'connection' | 'progress' | 'recent'

export const INFO_KEYS: readonly InfoKey[] = [
  'slot', 'done', 'remaining', 'newItems', 'hints', 'regions', 'goal', 'activity', 'connection', 'progress', 'recent',
]

export const INFO_LABELS: Record<InfoKey, string> = {
  slot: 'Nom du slot',
  done: 'Faits / total',
  remaining: 'Restants',
  newItems: '★ Nouveaux items',
  hints: '◆ Hints en logique',
  regions: 'Régions en logique',
  goal: 'But et go mode',
  activity: 'Activité',
  connection: 'État de connexion',
  progress: 'Barre de progression',
  recent: 'Bandeau Derniers reçus',
}

export type Density = 'essentiel' | 'standard' | 'complet'
export const DENSITIES: readonly Density[] = ['essentiel', 'standard', 'complet']
export const DENSITY_LABELS: Record<Density, string> = { essentiel: 'Essentiel', standard: 'Standard', complet: 'Complet' }

export const PRESETS: Record<Density, readonly InfoKey[]> = {
  essentiel: ['newItems', 'hints', 'goal'],
  standard: ['done', 'newItems', 'hints', 'regions', 'goal', 'progress', 'recent'],
  complet: INFO_KEYS,
}

export interface DisplayPrefs {
  preset: Density | 'custom'
  shown: InfoKey[]
}

export function normalizeShown(keys: readonly unknown[]): InfoKey[] {
  return INFO_KEYS.filter((k) => keys.includes(k))
}

export function applyPreset(d: Density): DisplayPrefs {
  return { preset: d, shown: [...PRESETS[d]] }
}

export function presetOf(shown: readonly InfoKey[]): Density | 'custom' {
  const key = normalizeShown(shown).join()
  return DENSITIES.find((d) => PRESETS[d].join() === key) ?? 'custom'
}

export function toggleInfo(p: DisplayPrefs, key: InfoKey, on: boolean): DisplayPrefs {
  const shown = normalizeShown(on ? [...p.shown, key] : p.shown.filter((k) => k !== key))
  return { preset: presetOf(shown), shown }
}

export function joinShown(parts: readonly (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(' · ')
}
