// Colours of the v2 themes. Applied as CSS variables on <html>; the names shared with style.css (shadcn) make the
// ui/* components and the v1 pages (Journal, Configuration) follow the v2 theme.
import type { ThemeChoice } from './prefs'

export type ResolvedTheme = 'nuit' | 'plan'

const nuit = {
  background: '#09121F',
  foreground: '#F4F6F9',
  card: 'rgba(22,32,46,0.82)',
  'card-foreground': '#F4F6F9',
  popover: '#172131',
  'popover-foreground': '#F4F6F9',
  primary: '#8FA8FF',
  'primary-foreground': '#0B1220',
  secondary: 'rgba(201,211,224,0.08)',
  'secondary-foreground': '#F4F6F9',
  muted: 'rgba(201,211,224,0.08)',
  'muted-foreground': '#C9D3E0',
  accent: 'rgba(143,168,255,0.14)',
  'accent-foreground': '#F4F6F9',
  destructive: '#FE8B83',
  border: 'rgba(201,211,224,0.14)',
  input: 'rgba(201,211,224,0.24)',
  ring: '#8FA8FF',
  good: 'rgba(107,207,157,0.14)',
  'good-foreground': '#6BCF9D',
  'good-border': 'rgba(107,207,157,0.4)',
  warn: 'rgba(254,139,131,0.12)',
  'warn-foreground': '#FE8B83',
  info: 'rgba(143,168,255,0.14)',
  'info-foreground': '#8FA8FF',
  live: '#6BCF9D',
  pending: '#EEC066',
  idle: '#C9D3E0',
  prog: '#EEC066',
  'bar-done': '#6BCF9D',
  'bar-logic': '#8FA8FF',
  logic: '#8FA8FF',
  done: '#6BCF9D',
  hint: '#EEA2D4',
  new: '#EEC066',
  error: '#FE8B83',
  header: 'rgba(15,22,33,0.66)',
}
export type TokenName = keyof typeof nuit

const plan: Record<TokenName, string> = {
  background: '#EAEEF3',
  foreground: '#16202E',
  card: '#FFFFFF',
  'card-foreground': '#16202E',
  popover: '#FFFFFF',
  'popover-foreground': '#16202E',
  primary: '#1B4DFF',
  'primary-foreground': '#FFFFFF',
  secondary: '#F4F6F9',
  'secondary-foreground': '#16202E',
  muted: '#F4F6F9',
  'muted-foreground': '#4A5868',
  accent: '#E3E9FF',
  'accent-foreground': '#16202E',
  destructive: '#B63132',
  border: '#C7D0DB',
  input: '#C7D0DB',
  ring: '#1B4DFF',
  good: '#E3F2EA',
  'good-foreground': '#1A6846',
  'good-border': '#9FCDB4',
  warn: '#FBE7E6',
  'warn-foreground': '#B63132',
  info: '#E3E9FF',
  'info-foreground': '#1B4DFF',
  live: '#1F7A52',
  pending: '#8D5E00',
  idle: '#4A5868',
  prog: '#8D5E00',
  'bar-done': '#1F7A52',
  'bar-logic': '#1B4DFF',
  logic: '#1B4DFF',
  done: '#1F7A52',
  hint: '#9E3081',
  new: '#8D5E00',
  error: '#B63132',
  header: 'rgba(234,238,243,0.86)',
}

export const TOKENS: Record<ResolvedTheme, Record<TokenName, string>> = { nuit, plan }
/** Opaque colour under the text of a card: Nuit's translucent card over the sky, Plan's white card. */
export const CARD_OPAQUE: Record<ResolvedTheme, string> = { nuit: '#172131', plan: '#FFFFFF' }

export function resolveTheme(choice: ThemeChoice, prefersDark: boolean): ResolvedTheme {
  if (choice === 'auto') return prefersDark ? 'nuit' : 'plan'
  return choice
}

export function applyV2Theme(theme: ResolvedTheme, el: HTMLElement = document.documentElement): void {
  for (const [k, v] of Object.entries(TOKENS[theme])) el.style.setProperty(`--${k}`, v)
  el.dataset.v2 = theme
  el.dataset.theme = theme === 'nuit' ? 'dark' : 'light'
  el.style.colorScheme = theme === 'nuit' ? 'dark' : 'light'
}
