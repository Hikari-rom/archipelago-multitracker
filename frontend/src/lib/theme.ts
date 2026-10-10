export type ThemeChoice = 'auto' | 'light' | 'dark'
const KEY = 'amt-theme'

export function loadTheme(): ThemeChoice {
  try {
    const v = localStorage.getItem(KEY)
    if (v === 'light' || v === 'dark' || v === 'auto') return v
  } catch {
    /* ignore */
  }
  return 'auto'
}

export function saveTheme(t: ThemeChoice): void {
  try {
    localStorage.setItem(KEY, t)
  } catch {
    /* ignore */
  }
}

export function applyTheme(t: ThemeChoice): void {
  const el = document.documentElement
  if (t === 'auto') el.removeAttribute('data-theme')
  else el.setAttribute('data-theme', t)
}

export function nextTheme(t: ThemeChoice): ThemeChoice {
  return t === 'auto' ? 'light' : t === 'light' ? 'dark' : 'auto'
}

export const themeLabel: Record<ThemeChoice, string> = {
  auto: 'Auto',
  light: 'Clair',
  dark: 'Sombre',
}
