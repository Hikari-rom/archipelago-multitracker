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
