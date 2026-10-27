// Preferences of the v2 interface, on this device. Separate keys: the v1 keeps its own.
import type { SortMode } from '../../lib/dashboard'

function read(key: string): string | null {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}
function write(key: string, v: string): void {
  try {
    localStorage.setItem(key, v)
  } catch {
    /* ignore */
  }
}
function oneOf<T extends string>(key: string, values: readonly T[], fallback: T): T {
  const v = read(key)
  return values.includes(v as T) ? (v as T) : fallback
}
const bool = (key: string, fallback: boolean) => {
  const v = read(key)
  return v === '1' ? true : v === '0' ? false : fallback
}

export type V2Layout = 'cards' | 'focus'
export const loadLayout = () => oneOf<V2Layout>('amt-v2-layout', ['cards', 'focus'], 'cards')
export const saveLayout = (v: V2Layout) => write('amt-v2-layout', v)

export const loadSort = () => oneOf<SortMode>('amt-v2-sort', ['auto', 'count', 'percent'], 'auto')
export const saveSort = (v: SortMode) => write('amt-v2-sort', v)

export const loadHideDone = () => bool('amt-v2-hide-done', false)
export const saveHideDone = (v: boolean) => write('amt-v2-hide-done', v ? '1' : '0')

export type ThemeChoice = 'nuit' | 'plan' | 'auto'
export const loadThemeChoice = () => oneOf<ThemeChoice>('amt-v2-theme', ['nuit', 'plan', 'auto'], 'nuit')
export const saveThemeChoice = (v: ThemeChoice) => write('amt-v2-theme', v)

export const loadSkyAnimated = () => bool('amt-v2-sky', true)
export const saveSkyAnimated = (v: boolean) => write('amt-v2-sky', v ? '1' : '0')

export const loadHideReached = () => bool('amt-v2-hide-reached', false)
export const saveHideReached = (v: boolean) => write('amt-v2-hide-reached', v ? '1' : '0')

/** « Derniers reçus » strip of the dashboard: the static list, or a news ticker in one of three looks. */
export type TickerStyle = 'off' | 'agence' | 'arrivees' | 'ruban'
export const TICKER_LABELS: Record<TickerStyle, string> = {
  off: 'Statique',
  agence: "Défilant · Fil d'agence",
  arrivees: 'Défilant · Tableau des arrivées',
  ruban: 'Défilant · Ruban céleste',
}
export const loadTicker = () => oneOf<TickerStyle>('amt-v2-ticker', ['off', 'agence', 'arrivees', 'ruban'], 'off')
export const saveTicker = (v: TickerStyle) => write('amt-v2-ticker', v)

/** Indices page: one sortable table, two tables (your items elsewhere / in your worlds), or one block per slot. */
export type HintsLayout = 'registre' | 'sens' | 'slots'
export const HINTS_LAYOUT_LABELS: Record<HintsLayout, string> = {
  registre: 'Registre : un seul tableau',
  sens: 'Deux sens : tes items / tes mondes',
  slots: 'Groupé par slot',
}
export const loadHintsLayout = () => oneOf<HintsLayout>('amt-v2-hints-layout', ['registre', 'sens', 'slots'], 'registre')
export const saveHintsLayout = (v: HintsLayout) => write('amt-v2-hints-layout', v)

export const loadHideFoundHints = () => bool('amt-v2-hints-hide-found', true)
export const saveHideFoundHints = (v: boolean) => write('amt-v2-hints-hide-found', v ? '1' : '0')

export interface HintsSort {
  key: string
  dir: 1 | -1
}
export function loadHintsSort(): HintsSort {
  try {
    const v = JSON.parse(read('amt-v2-hints-sort') ?? 'null')
    if (v && typeof v.key === 'string' && (v.dir === 1 || v.dir === -1)) return { key: v.key, dir: v.dir }
  } catch {
    /* ignore */
  }
  return { key: 'access', dir: 1 }
}
export const saveHintsSort = (v: HintsSort) => write('amt-v2-hints-sort', JSON.stringify(v))
