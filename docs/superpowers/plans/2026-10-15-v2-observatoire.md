# v2 « Observatoire » Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a second UI, « Observatoire », served at `/v2` next to the unchanged v1 at `/`, reusing the existing store and API.

**Architecture:** `src/main.ts` becomes a router: `/v2…` dynamically imports `src/v2/main.ts`, anything else imports `src/v1.ts` (today's `main.ts`). The v2 has its own components under `src/v2/`, its own preferences (localStorage keys `amt-v2-*`), and its own theme tokens (a TS object applied as CSS variables on `<html>`, so contrast is unit-tested). Store (`src/stores/tracker.ts`), `src/lib/*`, `src/components/ui/*` and the backend are reused; the only change to shared code is `restoreActivity()` in the store and a « Essayer la v2 » link in the v1 header.

**Tech Stack:** Vue 3.5 (`<script setup lang="ts">`), Tailwind CSS 4 (`@tailwindcss/vite`), reka-ui 2 primitives (DropdownMenu, Dialog), `@vueuse/core` (`useMediaQuery`), vitest 5 + happy-dom + `@vue/test-utils`, Playwright (screenshots only).

**Spec:** `docs/superpowers/specs/2026-10-15-v2-observatoire-design.md`. Visual reference with exact values: `docs/design/observatoire.dc.html` (sections are `<section data-screen-label="…">` / `<div data-screen-label="2a Cartes">` … `2k Plan`; open it in a browser or read the inline styles).

## Global Constraints

- Work in `frontend/`. Run tests with `cd frontend && npm test`, build with `npm run build` (runs `vue-tsc --noEmit` first: types must pass).
- Code, comments, commit messages in English; **every visible UI string in French**; game, item, location, option names never translated.
- Commit after each task on `main`, message in English, ending with the two trailer lines:
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` and
  `Claude-Session: https://claude.ai/code/session_0158GQtzHfEWz7d15p2mTqYa`. Push only in Task 13.
- Raspberry Pi constraints: no global installs, no new npm dependency (everything needed is already in `package.json`), no sudo. Max 2–3 heavy processes at once.
- Zero spoiler: the v2 only displays fields already returned by `/api/*` (types in `src/lib/types.ts`).
- v1 must keep working unchanged at `/` (all existing tests stay green).
- localStorage access always wrapped in `try/catch` (pattern of `src/lib/theme.ts`).
- Every colour meaning carries a sign as well as a colour: ◆ hint en logique, ★ nouvel item, ✓ fait/but atteint, ! erreur/avertissement, ◉ actif choisi, ◔ actif auto.
- Text contrast ≥ 4.5:1 (WCAG AA) on its surface, both themes (enforced by Task 3's test). In Nuit, text is never placed directly on the sky: always on a surface (`bg-card`, `bg-header`, `bg-popover`).
- Phone = viewport `< 700px` (`useMediaQuery('(max-width: 699px)')`), touch targets ≥ 44 px there. Long game names: `line-clamp-2` + `title` with the full name.
- `prefers-reduced-motion: reduce` or the « Ciel animé » switch off ⇒ no animation at all.

## Review Focus

1. **Theme « Auto » following the system live**: switching the OS from dark to light while `/v2` is open must switch Nuit→Plan without reload (Task 7 test: `resolveTheme` + AppV2 reacting to the media query ref).
2. **Active game expiry and undo**: « Expire dans N min » never negative and the card leaves Actifs when it reaches 0; « Annuler » after « Plus actif » restores exactly the previous `tracker.activity` (pinned included) and persists it (Task 4 tests).
3. **History items without time and day boundaries**: entries with `checked_at`/`received_at` null go to a single « Avant le suivi » group at the end; an entry at 00:06 today is under « Aujourd'hui », one at 23:58 yesterday under « Hier », timezone = device local time (Task 5 tests).
4. **Slots whose logic is not `ok`** (`unavailable`, `error`, `pending`, warning message) and disconnected slots must render a coherent big number (`—`, `··`, `≈`-prefixed) and never `NaN`/`undefined` (Task 4 tests, Task 8 render test).
5. **v1 untouched**: `/` still boots the v1 (with its own `style.css` and `amt-theme`), and `/v2/` (trailing slash) and `/v2#history` boot the v2; `/v20` does not (Task 1 test).

---

## File map

| Path | Responsibility | Task |
|---|---|---|
| `src/main.ts` | route `/v2` → v2, else v1 | 1 |
| `src/v1.ts` | today's `main.ts` body, unchanged | 1 |
| `src/lib/v2path.ts` | `isV2Path`, `v2Href`, `v1Href` | 1 |
| `src/App.vue` | + « Essayer la v2 » link | 1 |
| `src/v2/main.ts` | boot the v2 (theme, font, mock or start) | 1 |
| `src/v2/theme.css` | imports `../style.css`; v2 Tailwind colours, fonts, page backgrounds, keyframes | 1, 3 |
| `src/v2/AppV2.vue` | v2 shell (header, menus, nav, views) | 1 (stub), 7 |
| `src/v2/lib/prefs.ts` | layout / sort / hide-done / theme / sky preferences | 2 |
| `src/v2/lib/tokens.ts` | Nuit and Plan token values + `applyV2Theme` + `resolveTheme` | 3 |
| `src/v2/lib/card.ts` | state of a game card | 4 |
| `src/v2/lib/regions.ts` | logic locations grouped by region | 4 |
| `src/v2/lib/undo.ts` | « Plus actif » with 6 s undo | 4 |
| `src/stores/tracker.ts` | + `restoreActivity` | 4 |
| `src/v2/lib/days.ts` | history grouped by day, category badge | 5 |
| `src/lib/history.ts` | export `MONTHS` (already defined, not exported) | 5 |
| `src/v2/lib/sky.ts` | deterministic star field | 6 |
| `src/v2/components/SkyBackground.vue` | the animated sky | 6 |
| `src/v2/components/ThemeMenu.vue`, `MoreMenu.vue`, `BottomNav.vue`, `SleepBanner.vue`, `OwnerSelect.vue` | shell pieces | 7 |
| `src/v2/lib/nav.ts` | shared nav state (history tab) | 7 |
| `src/v2/components/BigNumber.vue`, `StateChips.vue`, `GoalBlock.vue`, `DetailTabs.vue`, `UndoToast.vue` | card building blocks | 8 |
| `src/v2/components/ActiveCard.vue`, `GameTile.vue`, `TotalsBar.vue`, `RecentStrip.vue` | Cards layout pieces | 9 |
| `src/v2/views/DashboardV2.vue` | dashboard (Cards + Focus + phone) | 9, 10 |
| `src/v2/components/FocusPanel.vue`, `FocusList.vue`, `DetailSheet.vue`, `ActiveCarousel.vue` | Focus + phone | 10 |
| `src/v2/lib/useHistory.ts`, `src/v2/views/HistoryV2.vue` | history page | 11 |
| `src/v2/views/GoalsV2.vue` | goals page | 12 |
| `src/mock/fixtures.ts`, `src/mock/install.ts` | + mock history | 13 |
| `scripts/screenshot-v2.mjs` | v2 screenshots | 13 |
| `tests/v2/*.test.ts` | tests | all |

---

### Task 1: Entry split, v2 boot, link from v1

**Files:**
- Create: `src/lib/v2path.ts`, `src/v1.ts`, `src/v2/main.ts`, `src/v2/theme.css`, `src/v2/AppV2.vue` (stub), `tests/v2/v2path.test.ts`
- Modify: `src/main.ts` (whole file), `src/App.vue` (header buttons, ~line 151)

**Interfaces:**
- Produces: `isV2Path(pathname: string): boolean`, `v2Href(hash: string): string`, `v1Href(hash: string): string` in `src/lib/v2path.ts`.

- [ ] **Step 1: Write the failing test** `tests/v2/v2path.test.ts`

```ts
import { describe, expect, it } from 'vitest'
import { isV2Path, v1Href, v2Href } from '../../src/lib/v2path'

describe('v2 path', () => {
  it('matches /v2 and below only', () => {
    expect(isV2Path('/v2')).toBe(true)
    expect(isV2Path('/v2/')).toBe(true)
    expect(isV2Path('/v2/anything')).toBe(true)
    expect(isV2Path('/')).toBe(false)
    expect(isV2Path('/v20')).toBe(false)
    expect(isV2Path('/assets/v2')).toBe(false)
  })
  it('keeps the hash when switching version', () => {
    expect(v2Href('#history')).toBe('/v2#history')
    expect(v2Href('')).toBe('/v2')
    expect(v1Href('#goals')).toBe('/#goals')
    expect(v1Href('')).toBe('/')
  })
})
```

- [ ] **Step 2: Run it** — `npm test -- tests/v2/v2path.test.ts` → FAIL (module not found).

- [ ] **Step 3: Implement** `src/lib/v2path.ts`

```ts
// The v2 interface ("Observatoire") lives at /v2, next to the v1 at /.
export function isV2Path(pathname: string): boolean {
  return pathname === '/v2' || pathname.startsWith('/v2/')
}
export function v2Href(hash: string): string {
  return '/v2' + hash
}
export function v1Href(hash: string): string {
  return '/' + hash
}
```

- [ ] **Step 4: Run it** → PASS.

- [ ] **Step 5: Move the v1 boot.** Create `src/v1.ts` with exactly the current content of `src/main.ts` (imports of `App.vue`, `./style.css`, theme, mock/start). Replace `src/main.ts` with:

```ts
import { isV2Path } from './lib/v2path'

// Each version loads its own code and CSS: /v2 is the "Observatoire" interface, anything else the v1.
if (isV2Path(location.pathname)) void import('./v2/main')
else void import('./v1')
```

- [ ] **Step 6: v2 boot.** `src/v2/theme.css` (completed in Task 3):

```css
@import "../style.css";

@theme inline {
  --font-mono: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace;
}
```

`src/v2/AppV2.vue` (stub, replaced in Task 7):

```vue
<script setup lang="ts">
import { tracker } from '../stores/tracker'
</script>

<template>
  <main class="p-4">v2 · {{ tracker.slots.length }} jeux</main>
</template>
```

`src/v2/main.ts`:

```ts
import { createApp } from 'vue'
import './theme.css'
import AppV2 from './AppV2.vue'
import { dispatch, start } from '../stores/tracker'

function loadMonoFont(): void {
  const l = document.createElement('link')
  l.rel = 'stylesheet'
  l.href = 'https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&display=swap'
  document.head.appendChild(l)
}

loadMonoFont()
if (import.meta.env.VITE_MOCK === '1') {
  void import('../mock/install').then((m) => {
    m.installMockMode(dispatch)
    createApp(AppV2).mount('#app')
  })
} else {
  createApp(AppV2).mount('#app')
  void start()
}
```

- [ ] **Step 7: Link from v1.** In `src/App.vue`, import `v2Href` from `./lib/v2path` and add, right after the theme `<Button>` in the header:

```vue
<Button as="a" variant="outline" size="sm" :href="v2Href(typeof location === 'undefined' ? '' : location.hash)">Essayer la v2</Button>
```

(`Button` from shadcn-vue accepts `as`; check `src/components/ui/button/Button.vue` forwards it — it uses reka-ui `Primitive`, so it does.)

- [ ] **Step 8: Verify** — `npm test && npm run build` → all green; `ls dist/assets` shows separate chunks for `v1` and `main` of v2.

- [ ] **Step 9: Commit** — `git add -A frontend && git commit -m "v2: serve a second interface at /v2 (entry split, boot, link from v1)"` (+ trailers).

---

### Task 2: v2 preferences

**Files:**
- Create: `src/v2/lib/prefs.ts`, `tests/v2/prefs.test.ts`

**Interfaces:**
- Consumes: `SortMode` from `src/lib/dashboard.ts`.
- Produces:
  - `type V2Layout = 'cards' | 'focus'`; `loadLayout(): V2Layout`; `saveLayout(v: V2Layout): void` (key `amt-v2-layout`, default `'cards'`)
  - `loadSort(): SortMode`; `saveSort(v: SortMode): void` (key `amt-v2-sort`, default `'auto'`)
  - `loadHideDone(): boolean`; `saveHideDone(v: boolean): void` (key `amt-v2-hide-done`, default `false`)
  - `type ThemeChoice = 'nuit' | 'plan' | 'auto'`; `loadThemeChoice(): ThemeChoice`; `saveThemeChoice(v): void` (key `amt-v2-theme`, default `'nuit'`)
  - `loadSkyAnimated(): boolean`; `saveSkyAnimated(v: boolean): void` (key `amt-v2-sky`, default `true`)
  - `loadHideReached(): boolean`; `saveHideReached(v: boolean): void` (key `amt-v2-hide-reached`, default `false`)

- [ ] **Step 1: Failing test** `tests/v2/prefs.test.ts`

```ts
import { afterEach, describe, expect, it, vi } from 'vitest'
import * as p from '../../src/v2/lib/prefs'

afterEach(() => {
  localStorage.clear()
  vi.restoreAllMocks()
})

describe('v2 prefs', () => {
  it('defaults', () => {
    expect(p.loadLayout()).toBe('cards')
    expect(p.loadSort()).toBe('auto')
    expect(p.loadHideDone()).toBe(false)
    expect(p.loadThemeChoice()).toBe('nuit')
    expect(p.loadSkyAnimated()).toBe(true)
    expect(p.loadHideReached()).toBe(false)
  })
  it('round-trips and uses v2 keys only', () => {
    p.saveLayout('focus')
    p.saveSort('percent')
    p.saveHideDone(true)
    p.saveThemeChoice('plan')
    p.saveSkyAnimated(false)
    p.saveHideReached(true)
    expect(p.loadLayout()).toBe('focus')
    expect(p.loadSort()).toBe('percent')
    expect(p.loadHideDone()).toBe(true)
    expect(p.loadThemeChoice()).toBe('plan')
    expect(p.loadSkyAnimated()).toBe(false)
    expect(p.loadHideReached()).toBe(true)
    expect(Object.keys(localStorage).every((k) => k.startsWith('amt-v2-'))).toBe(true)
  })
  it('ignores invalid values and storage errors', () => {
    localStorage.setItem('amt-v2-layout', 'compact')
    localStorage.setItem('amt-v2-theme', 'dark')
    expect(p.loadLayout()).toBe('cards')
    expect(p.loadThemeChoice()).toBe('nuit')
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    expect(p.loadSort()).toBe('auto')
    expect(() => p.saveSort('count')).not.toThrow()
  })
})
```

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement** `src/v2/lib/prefs.ts`

```ts
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
```

- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** — `"v2: per-device preferences under amt-v2-* keys"`.

---

### Task 3: Theme tokens Nuit / Plan, with contrast test

**Files:**
- Create: `src/v2/lib/tokens.ts`, `tests/v2/tokens.test.ts`
- Modify: `src/v2/theme.css`, `src/v2/main.ts`

**Interfaces:**
- Consumes: `ThemeChoice`, `loadThemeChoice` (Task 2).
- Produces:
  - `type ResolvedTheme = 'nuit' | 'plan'`
  - `TOKENS: Record<ResolvedTheme, Record<TokenName, string>>`
  - `CARD_OPAQUE: Record<ResolvedTheme, string>` (opaque colour the text sits on, for contrast)
  - `resolveTheme(choice: ThemeChoice, prefersDark: boolean): ResolvedTheme`
  - `applyV2Theme(theme: ResolvedTheme, el?: HTMLElement): void` — sets every token as `--<name>` inline on `<html>`, `data-v2="<theme>"`, and `data-theme="dark"|"light"` (so the v1 `dark:` variant used by `ui/*`, `ConfigView`, `LogsView` follows).
  - Tailwind colours added: `text-logic`, `text-done`, `text-hint`, `text-new`, `text-error`, `bg-header` (+ `bg-logic/15` etc. via opacity modifiers).

- [ ] **Step 1: Failing test** `tests/v2/tokens.test.ts`

```ts
import { describe, expect, it } from 'vitest'
import { applyV2Theme, CARD_OPAQUE, resolveTheme, TOKENS, type ResolvedTheme } from '../../src/v2/lib/tokens'

function rgb(c: string, over?: number[]): number[] {
  const hex = /^#([0-9a-f]{6})$/i.exec(c)
  if (hex) return [0, 2, 4].map((i) => parseInt(hex[1].slice(i, i + 2), 16))
  const m = /^rgba\((\d+),\s*(\d+),\s*(\d+),\s*([\d.]+)\)$/.exec(c)
  if (!m || !over) throw new Error('unparsable colour ' + c)
  const a = Number(m[4])
  return [1, 2, 3].map((i, k) => Math.round(Number(m[i]) * a + over[k] * (1 - a)))
}
const lum = (c: number[]) => {
  const v = c.map((x) => {
    x /= 255
    return x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4
  })
  return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]
}
const ratio = (a: number[], b: number[]) => {
  const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p)
  return (x + 0.05) / (y + 0.05)
}

describe('v2 tokens', () => {
  for (const theme of ['nuit', 'plan'] as ResolvedTheme[]) {
    const t = TOKENS[theme]
    const card = rgb(CARD_OPAQUE[theme])
    it(`${theme}: text tokens reach AA on the card`, () => {
      for (const k of ['foreground', 'muted-foreground', 'logic', 'done', 'hint', 'new', 'error', 'primary'] as const)
        expect(ratio(rgb(t[k]), card), k).toBeGreaterThanOrEqual(4.5)
    })
    it(`${theme}: tinted badges reach AA`, () => {
      for (const [fg, bg] of [['good-foreground', 'good'], ['warn-foreground', 'warn'], ['info-foreground', 'info']] as const)
        expect(ratio(rgb(t[fg]), rgb(t[bg], card)), fg).toBeGreaterThanOrEqual(4.5)
      expect(ratio(rgb(t['primary-foreground']), rgb(t.primary)), 'primary button').toBeGreaterThanOrEqual(4.5)
    })
  }
  it('resolves auto from the system', () => {
    expect(resolveTheme('auto', true)).toBe('nuit')
    expect(resolveTheme('auto', false)).toBe('plan')
    expect(resolveTheme('plan', true)).toBe('plan')
    expect(resolveTheme('nuit', false)).toBe('nuit')
  })
  it('applies variables and the v1 dark flag', () => {
    const el = document.createElement('html')
    applyV2Theme('nuit', el)
    expect(el.dataset.v2).toBe('nuit')
    expect(el.dataset.theme).toBe('dark')
    expect(el.style.getPropertyValue('--logic')).toBe(TOKENS.nuit.logic)
    applyV2Theme('plan', el)
    expect(el.dataset.theme).toBe('light')
    expect(el.style.getPropertyValue('--logic')).toBe(TOKENS.plan.logic)
  })
})
```

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement** `src/v2/lib/tokens.ts` (values from the spec's « Tokens » table, oklch converted to hex; checked: all ≥ 4.5 on the card except where the test says otherwise — if a value fails, darken/lighten it keeping its hue and record the change in the commit message)

```ts
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
```

- [ ] **Step 4: Run** → PASS (adjust a value if a pair fails; never lower the threshold).

- [ ] **Step 5: CSS.** Replace `src/v2/theme.css` with:

```css
@import "../style.css";

@theme inline {
  --font-mono: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace;
  --color-logic: var(--logic);
  --color-done: var(--done);
  --color-hint: var(--hint);
  --color-new: var(--new);
  --color-error: var(--error);
  --color-header: var(--header);
}

/* Page ground: the night sky gradient (stars are SkyBackground.vue), or the drawing grid of "Plan". */
html[data-v2='nuit'] body {
  background: radial-gradient(ellipse at 75% -5%, #19263f, #09121f 50%) fixed;
}
html[data-v2='plan'] body {
  background-color: #eaeef3;
  background-image: linear-gradient(#c7d0db 1px, transparent 1px), linear-gradient(90deg, #c7d0db 1px, transparent 1px);
  background-size: 28px 28px;
  background-position: -1px -1px;
  background-attachment: fixed;
}

@keyframes v2-twinkle {
  0%, 100% { opacity: 0.25; }
  50% { opacity: 1; }
}
@keyframes v2-drift {
  from { transform: translate3d(0, 0, 0); }
  to { transform: translate3d(0, -50%, 0); }
}
@media (prefers-reduced-motion: reduce) {
  [data-sky], [data-star] { animation: none !important; }
}
```

- [ ] **Step 6: Apply at boot** — in `src/v2/main.ts`, before mounting:

```ts
import { applyV2Theme, resolveTheme } from './lib/tokens'
import { loadThemeChoice } from './lib/prefs'
applyV2Theme(resolveTheme(loadThemeChoice(), matchMedia('(prefers-color-scheme: dark)').matches))
```

- [ ] **Step 7: Verify** `npm test && npm run build`; **Commit** — `"v2: Nuit and Plan theme tokens with an AA contrast test"`.

---

### Task 4: Card state, regions, « Plus actif » with undo

**Files:**
- Create: `src/v2/lib/card.ts`, `src/v2/lib/regions.ts`, `src/v2/lib/undo.ts`, `tests/v2/card.test.ts`, `tests/v2/regions.test.ts`, `tests/v2/undo.test.ts`
- Modify: `src/stores/tracker.ts` (after `setInactive`, ~line 75)

**Interfaces:**
- Consumes: `isActive`, `ActivityOverrides`, `connectionMessage`, `statusLabel` (`src/lib/logic.ts`); `setInactive`, `tracker` (store); `formatWhen` (`src/lib/history.ts`).
- Produces:
  - store: `restoreActivity(prev: ActivityOverrides): void`
  - `card.ts`:
    ```ts
    export interface CardCtx { nowMs: number; activeMinutes: number; activity: ActivityOverrides; roomSleeping: boolean }
    export type CardActivity = { kind: 'chosen' } | { kind: 'auto'; agoMin: number; expiresInMin: number } | null
    export type CardLogic =
      | { kind: 'ok'; count: number; approx: boolean; message: string | null }
      | { kind: 'unavailable'; message: string | null }
      | { kind: 'pending'; waiting: boolean }
    export type CardConnection = { kind: 'ok' } | { kind: 'connecting' } | { kind: 'sleeping'; since: string | null } | { kind: 'error'; message: string }
    export interface CardState { activity: CardActivity; logic: CardLogic; big: string; connection: CardConnection; goalReached: boolean }
    export function cardState(s: SlotSummary, ctx: CardCtx): CardState
    export function hhmm(epochSeconds: number): string
    ```
  - `regions.ts`:
    ```ts
    export interface RegionGroup { name: string; count: number; hinted: number; locations: LogicLocation[] }
    export const OTHER_REGION = 'Autres'
    export function regionsOf(locs: LogicLocation[]): RegionGroup[]
    ```
  - `undo.ts`: `undo` (reactive `{ message: string; prev: ActivityOverrides | null }`), `UNDO_MS = 6000`, `dismissWithUndo(name: string, game: string): void`, `undoLast(): void`, `clearUndo(): void`.

- [ ] **Step 1: Failing tests.**

`tests/v2/card.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { cardState, type CardCtx } from '../../src/v2/lib/card'
import { mk } from '../helpers'

const NOW = 1_800_000_000_000
const ago = (min: number) => NOW / 1000 - min * 60
const ctx = (p: Partial<CardCtx> = {}): CardCtx => ({
  nowMs: NOW, activeMinutes: 30, activity: { pinned: null, dismissed: {} }, roomSleeping: false, ...p,
})

describe('cardState', () => {
  it('auto active: minutes ago and minutes left, never negative', () => {
    const s = mk({ name: 'a', last_check_at: ago(12), logic: { state: 'ok', count: 7, message: null } })
    expect(cardState(s, ctx()).activity).toEqual({ kind: 'auto', agoMin: 12, expiresInMin: 18 })
    expect(cardState(mk({ name: 'b', last_check_at: ago(29.9) }), ctx()).activity).toEqual({ kind: 'auto', agoMin: 29, expiresInMin: 1 })
    expect(cardState(mk({ name: 'c', last_check_at: ago(30) }), ctx()).activity).toBeNull()
  })
  it('chosen by hand wins over auto', () => {
    const s = mk({ name: 'a', last_check_at: ago(5) })
    expect(cardState(s, ctx({ activity: { pinned: { name: 'a', at: ago(1) }, dismissed: {} } })).activity).toEqual({ kind: 'chosen' })
  })
  it('big number for every logic state', () => {
    expect(cardState(mk({ name: 'a', logic: { state: 'ok', count: 58, message: null } }), ctx()).big).toBe('58')
    expect(cardState(mk({ name: 'a', logic: { state: 'ok', count: 21, message: 'options aléatoires' } }), ctx())).toMatchObject({
      big: '21', logic: { kind: 'ok', approx: true },
    })
    expect(cardState(mk({ name: 'a', logic: { state: 'unavailable', count: 0, message: null } }), ctx()).big).toBe('—')
    expect(cardState(mk({ name: 'a', logic: { state: 'error', count: 0, message: 'x' } }), ctx()).big).toBe('—')
    expect(cardState(mk({ name: 'a', logic: { state: 'pending', count: 0, message: null } }), ctx())).toMatchObject({
      big: '··', logic: { kind: 'pending', waiting: false },
    })
    expect(cardState(mk({ name: 'a', status: 'connecting', logic: { state: 'pending', count: 0, message: null } }), ctx()).logic).toEqual({
      kind: 'pending', waiting: true,
    })
  })
  it('connection: ok, sleeping room, error message', () => {
    expect(cardState(mk({ name: 'a' }), ctx()).connection).toEqual({ kind: 'ok' })
    const off = mk({ name: 'a', status: 'disconnected', error: 'ConnectionRefusedError', updated_at: NOW / 1000 - 3600 })
    expect(cardState(off, ctx({ roomSleeping: true })).connection.kind).toBe('sleeping')
    expect(cardState(off, ctx()).connection).toEqual({ kind: 'error', message: 'Serveur injoignable, nouvel essai automatique.' })
    expect(cardState(mk({ name: 'a', status: 'error', error: null }), ctx()).connection).toEqual({ kind: 'error', message: 'Erreur' })
    expect(cardState(mk({ name: 'a', status: 'connecting' }), ctx()).connection).toEqual({ kind: 'connecting' })
  })
  it('goal reached', () => {
    expect(cardState(mk({ name: 'a', goal: true }), ctx()).goalReached).toBe(true)
  })
})
```

`tests/v2/regions.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { OTHER_REGION, regionsOf } from '../../src/v2/lib/regions'
import type { LogicLocation } from '../../src/lib/types'

const L = (id: number, region: string | null, hint = false): LogicLocation => ({
  id, name: `loc ${id}`, region, hint: hint ? { item: 'Hookshot', receiver: 'kuro', progression: true } : null,
})

describe('regionsOf', () => {
  it('groups by region, biggest first, hinted locations first inside', () => {
    const r = regionsOf([L(1, 'Great Sea'), L(2, 'Windfall'), L(3, 'Windfall', true), L(4, null), L(5, 'Windfall')])
    expect(r.map((g) => [g.name, g.count, g.hinted])).toEqual([['Windfall', 3, 1], ['Great Sea', 1, 0], [OTHER_REGION, 1, 0]])
    expect(r[0].locations.map((l) => l.id)).toEqual([3, 2, 5])
  })
  it('ties: hinted regions first, then name', () => {
    const r = regionsOf([L(1, 'B'), L(2, 'A'), L(3, 'C', true)])
    expect(r.map((g) => g.name)).toEqual(['C', 'A', 'B'])
  })
  it('empty', () => expect(regionsOf([])).toEqual([]))
})
```

`tests/v2/undo.test.ts`:

```ts
import { afterEach, describe, expect, it, vi } from 'vitest'
import { restoreActivity, tracker } from '../../src/stores/tracker'
import { dismissWithUndo, undo, undoLast, UNDO_MS } from '../../src/v2/lib/undo'
import { mk } from '../helpers'

afterEach(() => {
  vi.useRealTimers()
  tracker.activity = { pinned: null, dismissed: {} }
  tracker.slots = []
  localStorage.clear()
})

describe('Plus actif + Annuler', () => {
  it('restores the previous activity exactly and saves it', () => {
    vi.useFakeTimers()
    tracker.slots = [mk({ name: 'celeste', last_check_at: 100 })]
    tracker.activity = { pinned: { name: 'celeste', at: 50 }, dismissed: { other: 3 } }
    dismissWithUndo('celeste', 'Celeste (Open World)')
    expect(tracker.activity.pinned).toBeNull()
    expect(tracker.activity.dismissed.celeste).toBe(100)
    expect(undo.message).toBe("Celeste (Open World) n'est plus actif jusqu'à son prochain check.")
    undoLast()
    expect(tracker.activity).toEqual({ pinned: { name: 'celeste', at: 50 }, dismissed: { other: 3 } })
    expect(JSON.parse(localStorage.getItem('amt-activity')!)).toEqual(tracker.activity)
    expect(undo.message).toBe('')
  })
  it('the message disappears after 6 s', () => {
    vi.useFakeTimers()
    tracker.slots = [mk({ name: 'a', last_check_at: 1 })]
    dismissWithUndo('a', 'A')
    vi.advanceTimersByTime(UNDO_MS - 1)
    expect(undo.message).not.toBe('')
    vi.advanceTimersByTime(1)
    expect(undo.message).toBe('')
    expect(undo.prev).toBeNull()
  })
  it('restoreActivity copies its argument', () => {
    const prev = { pinned: null, dismissed: { a: 1 } }
    restoreActivity(prev)
    prev.dismissed.a = 9
    expect(tracker.activity.dismissed.a).toBe(1)
  })
})
```

- [ ] **Step 2: Run** `npm test -- tests/v2` → FAIL.

- [ ] **Step 3: Store.** In `src/stores/tracker.ts`, after `setInactive`:

```ts
/** "Annuler" after "Plus actif": put back the choices as they were. */
export function restoreActivity(prev: ActivityOverrides): void {
  tracker.activity = { pinned: prev.pinned ? { ...prev.pinned } : null, dismissed: { ...prev.dismissed } }
  saveActivity()
}
```

- [ ] **Step 4: `src/v2/lib/card.ts`**

```ts
// State of a game card in the v2: activity, logic, big number, connection.
import { connectionMessage, isActive, statusLabel, type ActivityOverrides } from '../../lib/logic'
import type { SlotSummary } from '../../lib/types'

export interface CardCtx { nowMs: number; activeMinutes: number; activity: ActivityOverrides; roomSleeping: boolean }
export type CardActivity = { kind: 'chosen' } | { kind: 'auto'; agoMin: number; expiresInMin: number } | null
export type CardLogic =
  | { kind: 'ok'; count: number; approx: boolean; message: string | null }
  | { kind: 'unavailable'; message: string | null }
  | { kind: 'pending'; waiting: boolean }
export type CardConnection = { kind: 'ok' } | { kind: 'connecting' } | { kind: 'sleeping'; since: string | null } | { kind: 'error'; message: string }
export interface CardState { activity: CardActivity; logic: CardLogic; big: string; connection: CardConnection; goalReached: boolean }

const two = (n: number) => String(n).padStart(2, '0')
export function hhmm(epochSeconds: number): string {
  const d = new Date(epochSeconds * 1000)
  return `${two(d.getHours())}:${two(d.getMinutes())}`
}

function activityOf(s: SlotSummary, c: CardCtx): CardActivity {
  if (c.activity.pinned?.name === s.name) return { kind: 'chosen' }
  if (!isActive(s, c.nowMs, c.activeMinutes, c.activity) || !s.last_check_at) return null
  const agoMin = Math.max(0, Math.floor((c.nowMs / 1000 - s.last_check_at) / 60))
  return { kind: 'auto', agoMin, expiresInMin: Math.max(1, c.activeMinutes - agoMin) }
}

function logicOf(s: SlotSummary): CardLogic {
  const l = s.logic
  if (l.state === 'ok') return { kind: 'ok', count: l.count, approx: !!l.message, message: l.message }
  if (l.state === 'pending') return { kind: 'pending', waiting: s.status !== 'connected' }
  return { kind: 'unavailable', message: l.message }
}

function connectionOf(s: SlotSummary, c: CardCtx): CardConnection {
  if (s.status === 'connected') return { kind: 'ok' }
  if (c.roomSleeping) return { kind: 'sleeping', since: s.updated_at ? hhmm(s.updated_at) : null }
  if (s.status === 'error' || s.status === 'disconnected')
    return { kind: 'error', message: connectionMessage(s, false) || statusLabel(s.status) }
  return { kind: 'connecting' }
}

export function cardState(s: SlotSummary, c: CardCtx): CardState {
  const logic = logicOf(s)
  const big = logic.kind === 'ok' ? String(logic.count) : logic.kind === 'pending' ? '··' : '—'
  return { activity: activityOf(s, c), logic, big, connection: connectionOf(s, c), goalReached: s.goal }
}
```

- [ ] **Step 5: `src/v2/lib/regions.ts`**

```ts
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
```

(Check: test 2 expects `['C','A','B']` for 1/1/1 counts with C hinted — order is count, then hinted, then name. ✓)

- [ ] **Step 6: `src/v2/lib/undo.ts`**

```ts
// "Plus actif" with a 6 s "Annuler".
import { reactive } from 'vue'
import type { ActivityOverrides } from '../../lib/logic'
import { restoreActivity, setInactive, tracker } from '../../stores/tracker'

export const UNDO_MS = 6000
export const undo = reactive({ message: '', prev: null as ActivityOverrides | null })
let timer: ReturnType<typeof setTimeout> | undefined

export function clearUndo(): void {
  clearTimeout(timer)
  undo.message = ''
  undo.prev = null
}

export function dismissWithUndo(name: string, game: string): void {
  const prev = { pinned: tracker.activity.pinned ? { ...tracker.activity.pinned } : null, dismissed: { ...tracker.activity.dismissed } }
  setInactive(name)
  clearTimeout(timer)
  undo.prev = prev
  undo.message = `${game} n'est plus actif jusqu'à son prochain check.`
  timer = setTimeout(clearUndo, UNDO_MS)
}

export function undoLast(): void {
  if (undo.prev) restoreActivity(undo.prev)
  clearUndo()
}
```

- [ ] **Step 7: Run** `npm test` → PASS (all, v1 included).
- [ ] **Step 8: Commit** — `"v2: card state, regions of logic locations, undo for \"Plus actif\""`.

---

### Task 5: History grouped by day, category badges

**Files:**
- Create: `src/v2/lib/days.ts`, `tests/v2/days.test.ts`
- Modify: `src/lib/history.ts` (`const MONTHS` → `export const MONTHS`)

**Interfaces:**
- Produces:
  ```ts
  export interface DayRow<T> { entry: T; showSource: boolean }
  export interface DayGroup<T> { key: string; label: string; rows: DayRow<T>[] }
  export const BEFORE_TRACKING = 'Avant le suivi'
  export function dayLabel(epochSeconds: number, nowMs: number): string
  export function groupByDay<T>(entries: T[], at: (e: T) => number | null, source: (e: T) => string, nowMs: number): DayGroup<T>[]
  export type Category = 'PROG' | 'UTILE' | 'PIÈGE'
  export function category(i: { progression: boolean; useful: boolean; trap: boolean }): Category | null
  ```

- [ ] **Step 1: Failing test** `tests/v2/days.test.ts`

```ts
import { describe, expect, it } from 'vitest'
import { BEFORE_TRACKING, category, dayLabel, groupByDay } from '../../src/v2/lib/days'

// local time: build timestamps from Date parts so the test does not depend on the timezone
const at = (y: number, mo: number, d: number, h: number, mi: number) => new Date(y, mo, d, h, mi).getTime() / 1000
const NOW = new Date(2026, 9, 15, 0, 30).getTime()

describe('days', () => {
  it('labels', () => {
    expect(dayLabel(at(2026, 9, 15, 0, 6), NOW)).toBe("Aujourd'hui")
    expect(dayLabel(at(2026, 9, 14, 23, 58), NOW)).toBe('Hier')
    expect(dayLabel(at(2026, 9, 3, 12, 0), NOW)).toBe('3 oct.')
    expect(dayLabel(at(2025, 11, 31, 12, 0), NOW)).toBe('31 déc. 2025')
  })
  it('groups newest first, untimed entries last, source shown once per run', () => {
    type E = { t: number | null; src: string }
    const es: E[] = [
      { t: at(2026, 9, 15, 0, 6), src: 'Slay the Spire' },
      { t: at(2026, 9, 14, 23, 58), src: 'Jak' },
      { t: at(2026, 9, 14, 23, 55), src: 'Jak' },
      { t: at(2026, 9, 14, 23, 15), src: 'Celeste' },
      { t: null, src: 'Celeste' },
      { t: null, src: 'Celeste' },
    ]
    const g = groupByDay(es, (e) => e.t, (e) => e.src, NOW)
    expect(g.map((d) => [d.label, d.rows.length])).toEqual([["Aujourd'hui", 1], ['Hier', 3], [BEFORE_TRACKING, 2]])
    expect(g[1].rows.map((r) => r.showSource)).toEqual([true, false, true])
    expect(g[2].rows.map((r) => r.showSource)).toEqual([true, false])
  })
  it('untimed entries in the middle still go to the last group', () => {
    const g = groupByDay([{ t: null }, { t: at(2026, 9, 15, 0, 1) }], (e) => e.t, () => 'x', NOW)
    expect(g.map((d) => d.label)).toEqual(["Aujourd'hui", BEFORE_TRACKING])
  })
  it('category', () => {
    expect(category({ progression: true, useful: false, trap: false })).toBe('PROG')
    expect(category({ progression: false, useful: true, trap: false })).toBe('UTILE')
    expect(category({ progression: true, useful: false, trap: true })).toBe('PIÈGE')
    expect(category({ progression: false, useful: false, trap: false })).toBeNull()
  })
})
```

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement** — export `MONTHS` in `src/lib/history.ts`, then `src/v2/lib/days.ts`:

```ts
// History page of the v2: entries grouped by day (device time), the source game shown once per run.
import { MONTHS } from '../../lib/history'

export interface DayRow<T> { entry: T; showSource: boolean }
export interface DayGroup<T> { key: string; label: string; rows: DayRow<T>[] }
export const BEFORE_TRACKING = 'Avant le suivi'

export function dayLabel(epochSeconds: number, nowMs: number): string {
  const d = new Date(epochSeconds * 1000)
  const today = new Date(nowMs)
  const yesterday = new Date(today.getFullYear(), today.getMonth(), today.getDate() - 1)
  if (d.toDateString() === today.toDateString()) return "Aujourd'hui"
  if (d.toDateString() === yesterday.toDateString()) return 'Hier'
  const base = `${d.getDate()} ${MONTHS[d.getMonth()]}`
  return d.getFullYear() === today.getFullYear() ? base : `${base} ${d.getFullYear()}`
}

export function groupByDay<T>(entries: T[], at: (e: T) => number | null, source: (e: T) => string, nowMs: number): DayGroup<T>[] {
  const groups: DayGroup<T>[] = []
  const before: T[] = []
  for (const e of entries) {
    const t = at(e)
    if (t == null) {
      before.push(e)
      continue
    }
    const key = new Date(t * 1000).toDateString()
    let g = groups[groups.length - 1]
    if (!g || g.key !== key) groups.push((g = { key, label: dayLabel(t, nowMs), rows: [] }))
    g.rows.push({ entry: e, showSource: true })
  }
  if (before.length) groups.push({ key: 'before', label: BEFORE_TRACKING, rows: before.map((entry) => ({ entry, showSource: true })) })
  for (const g of groups)
    g.rows.forEach((r, i) => (r.showSource = i === 0 || source(g.rows[i - 1].entry) !== source(r.entry)))
  return groups
}

export type Category = 'PROG' | 'UTILE' | 'PIÈGE'
export function category(i: { progression: boolean; useful: boolean; trap: boolean }): Category | null {
  if (i.trap) return 'PIÈGE'
  if (i.progression) return 'PROG'
  if (i.useful) return 'UTILE'
  return null
}
```

- [ ] **Step 4: Run** → PASS. **Step 5: Commit** — `"v2: history grouped by day and item categories"`.

---

### Task 6: Star field and SkyBackground

**Files:**
- Create: `src/v2/lib/sky.ts`, `src/v2/components/SkyBackground.vue`, `tests/v2/sky.test.ts`

**Interfaces:**
- Produces:
  ```ts
  export interface Star { x: number; y: number; size: number; opacity: number; twinkle: boolean; dur: number; delay: number }
  export interface SkyLayer { stars: Star[]; duration: number }
  export function skyLayers(phone: boolean): SkyLayer[]   // [far, near]
  ```
  `SkyBackground.vue` props: `{ animated: boolean }`; uses `useMediaQuery('(max-width: 699px)')` for density.

- [ ] **Step 1: Failing test** `tests/v2/sky.test.ts`

```ts
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import SkyBackground from '../../src/v2/components/SkyBackground.vue'
import { skyLayers } from '../../src/v2/lib/sky'

describe('sky', () => {
  it('densities, durations and bounds from the mockup', () => {
    const [far, near] = skyLayers(false)
    expect([far.stars.length, near.stars.length, far.duration, near.duration]).toEqual([150, 34, 260, 150])
    const [pf, pn] = skyLayers(true)
    expect([pf.stars.length, pn.stars.length]).toEqual([55, 14])
    for (const s of far.stars) {
      expect(s.x).toBeGreaterThanOrEqual(0)
      expect(s.x).toBeLessThan(100)
      expect(s.y).toBeLessThan(50)
      expect(s.size).toBeGreaterThanOrEqual(0.8)
      expect(s.size).toBeLessThanOrEqual(1.3)
    }
  })
  it('is deterministic', () => expect(skyLayers(false)).toEqual(skyLayers(false)))
  it('renders each star twice (seamless loop) and stops when not animated', () => {
    const w = mount(SkyBackground, { props: { animated: false } })
    expect(w.attributes('aria-hidden')).toBe('true')
    const stars = w.findAll('[data-star]')
    expect(stars.length).toBe((150 + 34) * 2)
    expect(w.findAll('[data-sky]').every((l) => !(l.attributes('style') ?? '').includes('v2-drift'))).toBe(true)
    expect(mount(SkyBackground, { props: { animated: true } }).find('[data-sky]').attributes('style')).toContain('v2-drift')
  })
})
```

(happy-dom: `matchMedia('(max-width: 699px)')` is false at the default 1024 px width → desktop density.)

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: `src/v2/lib/sky.ts`** (port of the mockup's `sky()` generator)

```ts
// Star field of the "Nuit" theme: two layers drifting upwards, generated once from a fixed seed.
export interface Star { x: number; y: number; size: number; opacity: number; twinkle: boolean; dur: number; delay: number }
export interface SkyLayer { stars: Star[]; duration: number }

function rng(seed: number) {
  let s = seed
  return () => {
    s = (s * 16807) % 2147483647
    return s / 2147483647
  }
}

function layer(rnd: () => number, count: number, size: [number, number], op: [number, number], twinkleShare: number, duration: number): SkyLayer {
  const stars = Array.from({ length: count }, () => ({
    x: rnd() * 100,
    y: rnd() * 50,
    size: size[0] + rnd() * (size[1] - size[0]),
    opacity: op[0] + rnd() * (op[1] - op[0]),
    twinkle: rnd() < twinkleShare,
    dur: 3 + rnd() * 5,
    delay: -rnd() * 8,
  }))
  return { stars, duration }
}

export function skyLayers(phone: boolean): SkyLayer[] {
  const rnd = rng(phone ? 29 : 11)
  return [
    layer(rnd, phone ? 55 : 150, [0.8, 1.3], [0.25, 0.6], 0.15, 260),
    layer(rnd, phone ? 14 : 34, [1.5, 2.4], [0.5, 0.9], 0.4, 150),
  ]
}
```

- [ ] **Step 4: `src/v2/components/SkyBackground.vue`**

```vue
<script setup lang="ts">
import { computed } from 'vue'
import { useMediaQuery } from '@vueuse/core'
import { skyLayers } from '../lib/sky'

/** Fixed behind the page; each layer is 200 % high with every star twice, and slides by -50 %: no visible restart. */
const props = defineProps<{ animated: boolean }>()
const phone = useMediaQuery('(max-width: 699px)')
const layers = computed(() => skyLayers(phone.value))
</script>

<template>
  <div aria-hidden="true" class="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
    <div
      v-for="(l, li) in layers"
      :key="li"
      data-sky
      class="absolute top-0 left-0 h-[200%] w-full will-change-transform"
      :style="{ animation: props.animated ? `v2-drift ${l.duration}s linear infinite` : 'none' }"
    >
      <template v-for="(s, i) in l.stars" :key="i">
        <span
          v-for="off in [0, 50]"
          :key="off"
          data-star
          class="absolute rounded-full bg-[#EAEEF3]"
          :style="{
            left: s.x.toFixed(2) + '%',
            top: (s.y + off).toFixed(2) + '%',
            width: s.size + 'px',
            height: s.size + 'px',
            opacity: s.opacity,
            boxShadow: s.size > 1.8 ? '0 0 4px rgba(200,215,255,.7)' : 'none',
            animation: props.animated && s.twinkle ? `v2-twinkle ${s.dur.toFixed(1)}s ease-in-out ${s.delay.toFixed(1)}s infinite` : 'none',
          }"
        />
      </template>
    </div>
  </div>
</template>
```

- [ ] **Step 5: Run** → PASS. **Step 6: Commit** — `"v2: animated star field for the Nuit theme"`.

---

### Task 7: The v2 shell (header, menus, phone nav, room banner, owner filter, routing)

**Files:**
- Create: `src/v2/lib/nav.ts`, `src/v2/components/ThemeMenu.vue`, `MoreMenu.vue`, `BottomNav.vue`, `SleepBanner.vue`, `OwnerSelect.vue`, `tests/v2/shell.test.ts`
- Modify: `src/v2/AppV2.vue` (replace stub)
- Temporary: until Tasks 9–12 land, `AppV2` renders placeholders `<p>` for dashboard/history/goals (replaced by the real views in those tasks).

**Interfaces:**
- Consumes: Tasks 2, 3, 6; store `tracker`, `setView`, `refreshMeta`, `View`; `wakeRoom` (`src/lib/api.ts`); owner helpers from `src/lib/config.ts` (`ALL_OWNERS`, `NO_OWNER`, `distinctOwners`, `filterByOwner`, `hasNoOwner`, `loadOwnerChoice`, `saveOwnerChoice`, `showOwnerFilter`); `totals` (`src/lib/dashboard.ts`); `v1Href`.
- Produces:
  - `nav.ts`: `export const historyTab = ref<'sent' | 'received'>('sent')`; `export function openHistory(tab: 'sent' | 'received'): void` (sets the tab and `setView('history')`).
  - `ThemeMenu.vue` props `{ choice: ThemeChoice; resolved: ResolvedTheme; sky: boolean }`, emits `update:choice`, `update:sky`.
  - `MoreMenu.vue` no props (uses `setView`, `v1Href`).
  - `BottomNav.vue` no props.
  - `SleepBanner.vue` no props (reads `tracker.roomSleeping`, `tracker.roomError`, `tracker.slots`).
  - `OwnerSelect.vue` `v-model: string` (owner key) + prop `chips: { key: string; label: string }[]`.
  - `AppV2` passes `slots` (owner-filtered `tracker.slots`) to the views.

- [ ] **Step 1: Failing test** `tests/v2/shell.test.ts`

```ts
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import AppV2 from '../../src/v2/AppV2.vue'
import { setView, tracker } from '../../src/stores/tracker'
import { mk } from '../helpers'

afterEach(() => {
  tracker.slots = []
  tracker.loaded = false
  tracker.roomSleeping = false
  tracker.roomError = ''
  setView('dashboard')
  document.documentElement.removeAttribute('data-v2')
})

describe('AppV2 shell', () => {
  it('tabs, logo home, live state, theme and more menus', async () => {
    tracker.loaded = true
    tracker.sse = 'open'
    tracker.slots = [mk({ name: 'a', logic: { state: 'ok', count: 58, message: null } })]
    const w = mount(AppV2, { attachTo: document.body })
    const tabs = w.findAll('nav[aria-label="Navigation"] a, nav[aria-label="Navigation"] button').map((t) => t.text())
    expect(tabs).toEqual(expect.arrayContaining(['Tableau', 'Historique', 'Objectifs']))
    expect(w.text()).toContain('En direct')
    expect(w.find('button[aria-label^="Thème"]').exists()).toBe(true)
    expect(w.find('button[aria-label="Plus"]').exists()).toBe(true)
    await w.find('button[aria-label="Historique"]').trigger('click')
    expect(tracker.view).toBe('history')
    await w.find('a[aria-label="Retour au tableau de bord"]').trigger('click')
    expect(tracker.view).toBe('dashboard')
    expect(document.documentElement.dataset.v2).toBe('nuit')
    w.unmount()
  })
  it('sleeping room banner with wake button', async () => {
    tracker.loaded = true
    tracker.slots = [mk({ name: 'a', status: 'disconnected', updated_at: new Date(2026, 9, 15, 2, 14).getTime() / 1000 })]
    tracker.roomSleeping = true
    tracker.roomError = 'room endormie'
    const w = mount(AppV2)
    await flushPromises()
    expect(w.text()).toContain('La room est endormie')
    expect(w.text()).toContain('02:14')
    expect(w.findAll('button').some((b) => b.text() === 'Réveiller maintenant')).toBe(true)
  })
  it('logs and config views reuse the v1 pages', async () => {
    tracker.loaded = true
    tracker.slots = [mk({ name: 'a' })]
    setView('logs')
    const w = mount(AppV2)
    expect(w.findComponent({ name: 'LogsView' }).exists()).toBe(true)
  })
})
```

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: `src/v2/lib/nav.ts`**

```ts
import { ref } from 'vue'
import { setView } from '../../stores/tracker'

/** Tab of the History page, set from the dashboard ("Tout voir →" opens "Items reçus"). */
export const historyTab = ref<'sent' | 'received'>('sent')
export function openHistory(tab: 'sent' | 'received'): void {
  historyTab.value = tab
  setView('history')
}
```

- [ ] **Step 4: Menus.** Use reka-ui primitives directly (`DropdownMenuRoot`, `DropdownMenuTrigger`, `DropdownMenuPortal`, `DropdownMenuContent`, `DropdownMenuItem`, `DropdownMenuRadioGroup`, `DropdownMenuRadioItem`, `DropdownMenuCheckboxItem`, `DropdownMenuItemIndicator` from `'reka-ui'`). Content panel classes: `z-50 min-w-64 rounded-xl border bg-popover p-1.5 text-popover-foreground shadow-xl`; items `flex min-h-11 cursor-default items-center gap-3 rounded-lg px-3 text-sm outline-none data-[highlighted]:bg-accent`.

`ThemeMenu.vue`:

```vue
<script setup lang="ts">
import { DropdownMenuCheckboxItem, DropdownMenuContent, DropdownMenuItemIndicator, DropdownMenuLabel, DropdownMenuPortal,
  DropdownMenuRadioGroup, DropdownMenuRadioItem, DropdownMenuRoot, DropdownMenuSeparator, DropdownMenuTrigger } from 'reka-ui'
import type { ThemeChoice } from '../lib/prefs'
import type { ResolvedTheme } from '../lib/tokens'

const props = defineProps<{ choice: ThemeChoice; resolved: ResolvedTheme; sky: boolean; compact?: boolean }>()
const emit = defineEmits<{ 'update:choice': [ThemeChoice]; 'update:sky': [boolean] }>()
const LABEL: Record<ThemeChoice, string> = { nuit: 'Nuit', plan: 'Plan', auto: 'Auto' }
const OPTIONS: { key: ThemeChoice; title: string; sub: string }[] = [
  { key: 'nuit', title: 'Nuit', sub: 'Ciel étoilé, sombre' },
  { key: 'plan', title: 'Plan', sub: 'Clair, grille de dessin' },
  { key: 'auto', title: 'Auto', sub: 'Suit le système : Plan ou Nuit' },
]
const item = 'flex min-h-11 cursor-default items-center gap-3 rounded-lg px-3 py-1.5 text-sm outline-none data-[highlighted]:bg-accent'
</script>

<template>
  <DropdownMenuRoot>
    <DropdownMenuTrigger
      :aria-label="`Thème : ${LABEL[props.choice]}`"
      class="flex min-h-9 items-center gap-1.5 rounded-lg border px-3 text-sm hover:bg-accent max-[699px]:min-h-11 max-[699px]:min-w-11 max-[699px]:justify-center"
    >
      <span aria-hidden="true">◐</span><span v-if="!props.compact">{{ LABEL[props.choice] }} ▾</span>
    </DropdownMenuTrigger>
    <DropdownMenuPortal>
      <DropdownMenuContent align="end" :side-offset="6" class="z-50 w-72 max-w-[calc(100vw-32px)] rounded-xl border bg-popover p-1.5 text-popover-foreground shadow-xl">
        <DropdownMenuLabel class="px-3 py-1.5 font-mono text-[11px] tracking-widest uppercase text-muted-foreground">Thème</DropdownMenuLabel>
        <DropdownMenuRadioGroup :model-value="props.choice" @update:model-value="(v) => emit('update:choice', v as ThemeChoice)">
          <DropdownMenuRadioItem v-for="o in OPTIONS" :key="o.key" :value="o.key" :class="item">
            <span class="flex flex-1 flex-col"><span class="font-semibold">{{ o.title }}</span><span class="text-xs text-muted-foreground">{{ o.sub }}</span></span>
            <DropdownMenuItemIndicator aria-hidden="true">✓</DropdownMenuItemIndicator>
          </DropdownMenuRadioItem>
        </DropdownMenuRadioGroup>
        <DropdownMenuSeparator class="my-1 h-px bg-border" />
        <DropdownMenuCheckboxItem
          :model-value="props.sky"
          :disabled="props.resolved !== 'nuit'"
          :class="item"
          @update:model-value="(v) => emit('update:sky', !!v)"
        >
          <span class="flex flex-1 flex-col"><span class="font-semibold">Ciel animé</span><span class="text-xs text-muted-foreground">Coupé si le système réduit les animations</span></span>
          <DropdownMenuItemIndicator aria-hidden="true">✓</DropdownMenuItemIndicator>
        </DropdownMenuCheckboxItem>
      </DropdownMenuContent>
    </DropdownMenuPortal>
  </DropdownMenuRoot>
</template>
```

`MoreMenu.vue`: trigger `aria-label="Plus"` showing `Plus ▾` (desktop) / `⋯ Plus` (phone, via prop `compact`); items « Journal » → `setView('logs')`, « Configuration » → `setView('config')`, separator, « Revenir à la v1 » as `DropdownMenuItem as-child` wrapping `<a :href="v1Href(location.hash)">`. Same classes as ThemeMenu.

- [ ] **Step 5: `BottomNav.vue`** (phone only; fixed bottom, `bg-header backdrop-blur border-t`, `pb-[env(safe-area-inset-bottom)]`), four 44 px+ buttons with `aria-current="page"` on the active view: `⌂ Tableau` → `setView('dashboard')`, `↺ Historique` → `setView('history')`, `⚑ Objectifs` → `setView('goals')`, and `<MoreMenu compact />` as the fourth item. Each button: `flex min-h-14 flex-1 flex-col items-center justify-center gap-0.5 text-[11px]`, icon span `text-lg aria-hidden`.

- [ ] **Step 6: `SleepBanner.vue`** — shown when `tracker.roomError`. Copies the wake logic of `src/App.vue` (`waking`, `wakeError`, `onWake` calling `wakeRoom()` then `refreshMeta()`):

```vue
<script setup lang="ts">
import { computed, ref } from 'vue'
import { wakeRoom } from '../../lib/api'
import { refreshMeta, tracker } from '../../stores/tracker'
import { hhmm } from '../lib/card'

const waking = ref(false)
const wakeError = ref('')
const since = computed(() => {
  const t = Math.max(0, ...tracker.slots.map((s) => s.updated_at ?? 0))
  return t ? hhmm(t) : ''
})
async function onWake() {
  waking.value = true
  wakeError.value = ''
  try {
    const r = await wakeRoom()
    if (!r.ok && r.room_error) wakeError.value = r.room_error
  } catch (e) {
    wakeError.value = e instanceof Error ? e.message : String(e)
  } finally {
    await refreshMeta()
    waking.value = false
  }
}
</script>

<template>
  <div v-if="tracker.roomError" role="alert" class="mx-auto mt-3 flex max-w-[1440px] flex-wrap items-center gap-x-4 gap-y-2 rounded-xl border bg-card px-4 py-3 text-sm">
    <span aria-hidden="true" class="text-xl text-logic">☾</span>
    <p v-if="tracker.roomSleeping" class="min-w-0 flex-1">
      <strong>La room est endormie</strong>
      <span class="text-muted-foreground"> archipelago.gg l'a arrêtée faute d'activité.<template v-if="since"> Les chiffres affichés datent de {{ since }}.</template></span>
    </p>
    <p v-else class="min-w-0 flex-1"><span class="text-error" aria-hidden="true">! </span>Room : {{ tracker.roomError }}</p>
    <button v-if="tracker.roomSleeping" type="button" class="min-h-9 rounded-lg bg-primary px-4 font-semibold text-primary-foreground disabled:opacity-60" :disabled="waking" @click="onWake">
      {{ waking ? 'Réveil…' : 'Réveiller maintenant' }}
    </button>
    <span v-if="wakeError" class="text-error">{{ wakeError }}</span>
  </div>
</template>
```

- [ ] **Step 7: `OwnerSelect.vue`** — a native `<select>` labelled « Joueur » (`<label>` + `<select class="h-9 rounded-lg border bg-card px-2 text-sm">`), options from `chips` (« Tous » shown as « tous »), `v-model` string. Shown only when `showOwnerFilter(tracker.slots)`.

- [ ] **Step 8: `AppV2.vue`**

```vue
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useMediaQuery } from '@vueuse/core'
import ConfigView from '../components/ConfigView.vue'
import LogsView from '../components/LogsView.vue'
import { ALL_OWNERS, NO_OWNER, distinctOwners, filterByOwner, hasNoOwner, loadOwnerChoice, saveOwnerChoice, showOwnerFilter } from '../lib/config'
import { totals } from '../lib/dashboard'
import { setView, tracker, type View } from '../stores/tracker'
import BottomNav from './components/BottomNav.vue'
import MoreMenu from './components/MoreMenu.vue'
import SkyBackground from './components/SkyBackground.vue'
import SleepBanner from './components/SleepBanner.vue'
import ThemeMenu from './components/ThemeMenu.vue'
import { loadSkyAnimated, loadThemeChoice, saveSkyAnimated, saveThemeChoice, type ThemeChoice } from './lib/prefs'
import { applyV2Theme, resolveTheme } from './lib/tokens'

const phone = useMediaQuery('(max-width: 699px)')
const prefersDark = useMediaQuery('(prefers-color-scheme: dark)')
const reducedMotion = useMediaQuery('(prefers-reduced-motion: reduce)')

const themeChoice = ref<ThemeChoice>(loadThemeChoice())
const resolved = computed(() => resolveTheme(themeChoice.value, prefersDark.value))
watch(resolved, (t) => applyV2Theme(t), { immediate: true })
watch(themeChoice, saveThemeChoice)
const sky = ref(loadSkyAnimated())
watch(sky, saveSkyAnimated)

const ownerChoice = ref(loadOwnerChoice())
const chips = computed(() => [
  { key: ALL_OWNERS, label: 'tous' },
  ...distinctOwners(tracker.slots).map((o) => ({ key: o, label: o })),
  ...(hasNoOwner(tracker.slots) ? [{ key: NO_OWNER, label: 'sans joueur' }] : []),
])
const owner = computed({
  get: () => (chips.value.some((c) => c.key === ownerChoice.value) ? ownerChoice.value : ALL_OWNERS),
  set: (k: string) => {
    ownerChoice.value = k
    saveOwnerChoice(k)
  },
})
const selected = computed(() => filterByOwner(tracker.slots, owner.value))
const inLogic = computed(() => totals(selected.value).inLogic)

const showConfig = computed(() => tracker.view === 'config' || (tracker.loaded && !tracker.slots.length && !tracker.loadError))
const view = computed<View>(() => (showConfig.value ? 'config' : tracker.view))
const roomHref = computed(() => (/^https?:\/\//.test(tracker.roomUrl) ? tracker.roomUrl : ''))
const sseLabel = computed(() => ({ open: 'En direct', connecting: 'Connexion…', reconnecting: 'Reconnexion…' })[tracker.sse])
const TABS: { key: View; label: string }[] = [
  { key: 'dashboard', label: 'Tableau' },
  { key: 'history', label: 'Historique' },
  { key: 'goals', label: 'Objectifs' },
]
</script>

<template>
  <SkyBackground v-if="resolved === 'nuit'" :animated="sky && !reducedMotion" />
  <header class="sticky top-0 z-20 border-b bg-header backdrop-blur-md">
    <div class="mx-auto flex h-14 max-w-[1440px] items-center gap-5 px-4 min-[700px]:px-8">
      <a href="#" aria-label="Retour au tableau de bord" class="flex min-w-0 items-center gap-2.5" @click.prevent="setView('dashboard')">
        <span class="grid size-7 shrink-0 place-items-center rounded-md border border-logic/60 font-mono text-[11px] font-bold text-logic">AP</span>
        <span class="flex min-w-0 flex-col">
          <span class="text-[15px] font-semibold">Multitracker</span>
          <span v-if="!phone && (tracker.server || tracker.roomUrl)" class="truncate font-mono text-[10.5px] text-muted-foreground">
            {{ tracker.server }}<template v-if="roomHref"> · <a :href="roomHref" target="_blank" rel="noopener" class="underline-offset-2 hover:underline">room ↗</a></template>
          </span>
        </span>
      </a>
      <nav v-if="!phone" aria-label="Navigation" class="ml-5 flex self-stretch">
        <button
          v-for="t in TABS" :key="t.key" type="button" :aria-label="t.label"
          :aria-current="view === t.key ? 'page' : undefined"
          class="border-b-2 px-4 text-sm"
          :class="view === t.key ? 'border-logic font-semibold' : 'border-transparent text-muted-foreground hover:text-foreground'"
          @click="setView(t.key)"
        >{{ t.label }}</button>
      </nav>
      <span v-if="phone" class="ml-auto font-mono text-sm"><strong class="text-logic">{{ inLogic }}</strong> en logique</span>
      <span v-if="!phone" class="ml-auto flex items-center gap-2 text-xs text-muted-foreground">
        <span class="size-2 rounded-full" :class="tracker.sse === 'open' ? 'bg-done' : 'bg-new'" aria-hidden="true" />{{ sseLabel }}
      </span>
      <MoreMenu v-if="!phone" />
      <ThemeMenu v-model:choice="themeChoice" v-model:sky="sky" :resolved="resolved" :compact="phone" />
    </div>
  </header>
  <SleepBanner class="mx-4 min-[700px]:mx-8" />
  <main class="mx-auto max-w-[1440px] px-4 pt-4 pb-24 min-[700px]:px-8 min-[700px]:pb-10">
    <p v-if="tracker.loadError && !tracker.slots.length" role="alert" class="rounded-xl border bg-card p-4"><span class="text-error">! </span>Impossible de joindre le serveur : {{ tracker.loadError }}</p>
    <ConfigView v-else-if="view === 'config'" />
    <LogsView v-else-if="view === 'logs'" />
    <p v-else-if="view === 'history'">Historique (Task 11)</p>
    <p v-else-if="view === 'goals'">Objectifs (Task 12)</p>
    <p v-else>Tableau ({{ selected.length }} jeux, Task 9)</p>
  </main>
  <BottomNav v-if="phone" />
</template>
```

Pass `owner`/`chips` down to the views in Tasks 9–12 (`<OwnerSelect v-if="showOwnerFilter(tracker.slots)" v-model="owner" :chips="chips" />` sits in each view's control bar; expose them via props `slots`, `owner`, `chips`, and emit `update:owner`). Keep the placeholders' `selected` reference so `vue-tsc` does not complain about unused imports.

- [ ] **Step 9: Run** `npm test && npm run build` → PASS. **Step 10: Commit** — `"v2: shell with tabs, theme and more menus, phone nav, room banner"`.

---

### Task 8: Card building blocks (big number, state chips, goal block, detail tabs, undo toast)

**Files:**
- Create: `src/v2/components/BigNumber.vue`, `StateChips.vue`, `GoalBlock.vue`, `DetailTabs.vue`, `UndoToast.vue`, `tests/v2/blocks.test.ts`
- Modify: `src/v2/AppV2.vue` (mount `<UndoToast />` once, before `</main>`'s sibling `BottomNav`)

**Interfaces:**
- Consumes: `cardState`, `CardState`, `CardCtx` (Task 4), `regionsOf` (Task 4), `category` (Task 5), `undo`, `undoLast` (Task 4); store `tracker`, `markSeen`, `loadDetail`; `formatReceived` (`src/lib/history.ts`); `hintInMyWorld`, `hintMineElsewhere` (`src/lib/logic.ts`); `mainCounter`, `counterText` (`src/lib/goals.ts`).
- Produces:
  - `useCardCtx(): ComputedRef<CardCtx>` exported from `src/v2/lib/card.ts` (add it there: `computed(() => ({ nowMs: tracker.nowMs, activeMinutes: tracker.activeMinutes, activity: tracker.activity, roomSleeping: tracker.roomSleeping }))`).
  - `BigNumber.vue` props `{ state: CardState; size?: 'xl' | 'lg' | 'md' }` → the number in `font-mono tabular-nums`, coloured `text-logic` when `logic.kind === 'ok' && count > 0`, `text-muted-foreground` otherwise; `≈` prefix span (`aria-label="approximatif"`) when `logic.approx`; ✓ in `text-done` instead of the number when `goalReached`. Sizes: xl 56px (focus/active), lg 34px (tiles), md 22px (lists).
  - `StateChips.vue` props `{ state: CardState }` → the pills: `◉ Actif · choisi` / `◔ Actif · auto · il y a N min` (`bg-logic/15 text-logic`), `● Connecté` (`text-done`) or the connection state (`☾ En pause, chiffres de HH:MM`, `! <message>` in `text-error` on `bg-warn` followed by a `Réessayer` button (`data-retry`) calling `start()` from the store — it reconnects the live stream and reloads the snapshot, `Connexion…`), `Logique indisponible pour ce jeu`, `Calcul de la logique…` (or `En attente de connexion` when `waiting`), `! <message>` for approx logic, `✓ But atteint`.
  - `GoalBlock.vue` props `{ objective: Objective | null | undefined; goal: boolean; compact?: boolean }` → compact: `But · <label> <current> / <target>` from `mainCounter`; full: summary, counters with bars (`bg-done`), steps ✓ faite (`text-done`) / ○ à faire / ⊘ + « invisible pour un tracker ».
  - `DetailTabs.vue` props `{ name: string; initial?: DetailTab }`, `type DetailTab = 'logic' | 'new' | 'received' | 'hints' | 'goal'`.
  - `UndoToast.vue` no props.

- [ ] **Step 1: Failing test** `tests/v2/blocks.test.ts`

```ts
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import BigNumber from '../../src/v2/components/BigNumber.vue'
import DetailTabs from '../../src/v2/components/DetailTabs.vue'
import StateChips from '../../src/v2/components/StateChips.vue'
import UndoToast from '../../src/v2/components/UndoToast.vue'
import { cardState, type CardCtx } from '../../src/v2/lib/card'
import { undo } from '../../src/v2/lib/undo'
import { tracker } from '../../src/stores/tracker'
import type { SlotDetail } from '../../src/lib/types'
import { mk } from '../helpers'

const NOW = 1_800_000_000_000
const ctx: CardCtx = { nowMs: NOW, activeMinutes: 30, activity: { pinned: null, dismissed: {} }, roomSleeping: false }

afterEach(() => {
  tracker.details = {}
  undo.message = ''
  undo.prev = null
})

describe('card blocks', () => {
  it('big number never shows NaN/undefined', () => {
    for (const logic of [
      { state: 'ok', count: 0, message: null },
      { state: 'ok', count: 21, message: 'yaml' },
      { state: 'pending', count: 0, message: null },
      { state: 'unavailable', count: 0, message: null },
      { state: 'error', count: 0, message: null },
    ] as const) {
      const t = mount(BigNumber, { props: { state: cardState(mk({ name: 'a', logic: { ...logic } }), ctx) } }).text()
      expect(t).not.toMatch(/NaN|undefined/)
    }
    // render `<span aria-label="approximatif">≈</span>{{ big }}` with no whitespace between them
    expect(mount(BigNumber, { props: { state: cardState(mk({ name: 'a', logic: { state: 'ok', count: 21, message: 'x' } }), ctx) } }).text()).toBe('≈21')
  })
  it('chips: auto active and error', () => {
    const s = mk({ name: 'a', last_check_at: NOW / 1000 - 12 * 60, status: 'error', error: 'connexion refusée : mot de passe' })
    const t = mount(StateChips, { props: { state: cardState(s, ctx) } }).text()
    expect(t).toContain('◔ Actif · auto · il y a 12 min')
    expect(t).toContain('connexion refusée : mot de passe')
    expect(t).toContain('Réessayer')
  })
  it('detail tabs: regions, hinted locations first, new items', async () => {
    const d = {
      ...mk({ name: 'ww', items: { received: 2, new: 1 } }),
      items_list: [
        { index: 1, name: 'Progressive Sword', sender: 'kuro', own: false, location: 'X', progression: true, useful: false, trap: false, new: true, received_at: null },
        { index: 0, name: 'Rupee', sender: 'kuro', own: false, location: 'Y', progression: false, useful: false, trap: false, new: false, received_at: null },
      ],
      hints_mine_elsewhere: [],
      hints_in_my_world: [],
      in_logic_locations: [
        { id: 1, name: 'Windfall Island - Cafe Bar - Postman', region: 'Windfall Island', hint: null },
        { id: 2, name: 'Windfall Island - Jail - Tingle - First Gift', region: 'Windfall Island', hint: { item: 'Golden Walnut', receiver: 'kuro_valley', progression: true } },
        { id: 3, name: 'Great Sea - Crab', region: 'Great Sea', hint: null },
      ],
    } as SlotDetail
    tracker.details = { ww: d }
    const w = mount(DetailTabs, { props: { name: 'ww' } })
    await flushPromises()
    expect(w.find('[role="tablist"]').exists()).toBe(true)
    const rows = w.findAll('[data-location]').map((r) => r.text())
    expect(rows[0]).toContain('Tingle')
    expect(rows[0]).toContain('hint · Golden Walnut pour kuro_valley')
    await w.find('[role="tab"][data-tab="new"]').trigger('click')
    expect(w.text()).toContain('Progressive Sword')
    expect(w.text()).not.toContain('Rupee')
    expect(w.text()).toContain('Marquer comme vu')
  })
  it('undo toast', async () => {
    undo.message = "Celeste n'est plus actif jusqu'à son prochain check."
    undo.prev = { pinned: null, dismissed: {} }
    const w = mount(UndoToast)
    expect(w.attributes('role')).toBe('status')
    expect(w.text()).toContain('Annuler')
  })
})
```

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement the five components** following the Interfaces block and mockup section 2g (« États ») and 2b (Focus detail). Required details:
  - `DetailTabs.vue`: reads `tracker.details[props.name]`; when missing and no `tracker.detailError[name]`, calls `loadDetail(name)` in `onMounted` and shows `Chargement…`; on error shows `! <error>`. Tablist (`role="tablist"`, buttons `role="tab"`, `:aria-selected`, `data-tab`) with labels and counts: `En logique <n>`, `★ Nouveaux <n>`, `Reçus <n>`, `Hints <n>`, `But`. Arrow keys Left/Right move between tabs.
    - `logic`: two columns on ≥ 900 px (`grid-cols-[minmax(0,240px)_1fr]`), one on phone. Left: `regionsOf(d.in_logic_locations)` as buttons (`name`, `◆<hinted>` in `text-hint` when > 0, count in `font-mono`); selected region `bg-logic/15`. Right: heading `<region> · <count> en logique · hintées en premier`, then each location as `<li data-location>`: `◆` (`text-hint`, `aria-label="hintée"`) when `hint`, the name, and under it `hint · <hint.item> pour <hint.receiver>`. Empty: `Aucun check en logique.`.
    - `new`: `d.items_list.filter((i) => i.new)` newest first; each row: category badge (`category(i)`: PROG `text-logic bg-logic/15`, UTILE `text-done bg-done/15`, PIÈGE `text-error bg-error/15`, none = no badge), name, `de <sender> · <location>` (or `inventaire de départ` when `origin === 'start'`), time `formatReceived(i, tracker.nowMs)`. Button `Marquer comme vu` → `markSeen(name)`.
    - `received`: all `items_list` sorted by `index` desc, first 50, same rows, then `+ N autres` when more.
    - `hints`: `hints_in_my_world` (in-logic first, each prefixed `◆` in `text-hint` when `in_logic`) using `hintInMyWorld`, then `hints_mine_elsewhere` using `hintMineElsewhere`.
    - `goal`: `<GoalBlock :objective="d.objective" :goal="d.goal" />`.
  - `UndoToast.vue`: fixed bottom-center (`bottom-24` on phone above BottomNav, `bottom-6` on desktop), `role="status" aria-live="polite"`, `bg-popover border rounded-xl shadow-xl px-4 py-3`, text `undo.message`, button `Annuler` → `undoLast()`. Rendered only when `undo.message`.

- [ ] **Step 4: Run** → PASS. **Step 5: Commit** — `"v2: card building blocks (big number, state chips, goal, detail tabs, undo toast)"`.

---

### Task 9: Dashboard — Cards layout (desktop)

**Files:**
- Create: `src/v2/components/TotalsBar.vue`, `RecentStrip.vue`, `ActiveCard.vue`, `GameTile.vue`, `src/v2/views/DashboardV2.vue`, `tests/v2/dashboard.test.ts`
- Modify: `src/v2/AppV2.vue` (render `DashboardV2` for `view === 'dashboard'`)

**Interfaces:**
- Consumes: Tasks 2, 4, 7, 8; `sortBy`, `splitFeatured`, `compactMain`, `totals`, `feedItems`, `FEED_SHORT`, `SORT_LABELS`, `barParts` (`src/lib/dashboard.ts`); `stableOrder` (`src/lib/order.ts`); store `tracker`, `setFeatured`, `pinActive`, `toggleOpen`, `isOpen`, `markSeen`; `openHistory` (Task 7); `formatWhen`.
- Produces: `DashboardV2.vue` props `{ slots: SlotSummary[]; owner: string; chips: { key: string; label: string }[] }`, emits `update:owner`. Exposes no API. `TotalsBar` props `{ slots: SlotSummary[]; sort: SortMode; layout: V2Layout; hideDone: boolean; owner; chips }` + `update:*` emits.

- [ ] **Step 1: Failing test** `tests/v2/dashboard.test.ts`

```ts
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import DashboardV2 from '../../src/v2/views/DashboardV2.vue'
import { installMock } from '../../src/lib/api'
import { tracker } from '../../src/stores/tracker'
import { mk } from '../helpers'

const NOW = 1_800_000_000_000
const ago = (m: number) => NOW / 1000 - m * 60

beforeEach(() => {
  installMock({ getSlot: async (n) => ({ ...mk({ name: n }), items_list: [], hints_in_my_world: [], hints_mine_elsewhere: [], in_logic_locations: [] }), markSeen: async () => ({ seen: 0 }) })
  tracker.nowMs = NOW
  tracker.activeMinutes = 30
  tracker.loaded = true
})
afterEach(() => {
  tracker.slots = []
  tracker.activity = { pinned: null, dismissed: {} }
  localStorage.clear()
})

const slots = () => [
  mk({ name: 'isaac', game: 'The Binding of Isaac Repentance', logic: { state: 'ok', count: 58, message: null }, checks: { done: 0, total: 361, remaining: 361 } }),
  mk({ name: 'celeste', game: 'Celeste (Open World)', last_check_at: ago(12), logic: { state: 'ok', count: 7, message: null }, items: { received: 1, new: 1 } }),
  mk({ name: 'jak3', game: 'Jak 3', logic: { state: 'ok', count: 34, message: null }, hints: { mine_elsewhere: 0, in_my_world: 1, in_my_world_in_logic: 1 } }),
  mk({ name: 'mkwii', game: 'Mario Kart Wii', logic: { state: 'unavailable', count: 0, message: null } }),
]

describe('DashboardV2 · Cartes', () => {
  it('totals, actives first, then "Où avancer"', async () => {
    tracker.slots = slots()
    tracker.activity = { pinned: { name: 'isaac', at: ago(1) }, dismissed: {} }
    const w = mount(DashboardV2, { props: { slots: tracker.slots, owner: '*', chips: [] } })
    await flushPromises()
    expect(w.text()).toContain('99 en logique')
    const actives = w.findAll('[data-active-card]').map((c) => c.attributes('data-active-card'))
    expect(actives).toEqual(['isaac', 'celeste'])
    expect(w.text()).toContain('◉ Actif · choisi')
    expect(w.text()).toContain('Où avancer · 2 jeux')
    const tiles = w.findAll('[data-tile]').map((t) => t.attributes('data-tile'))
    expect(tiles).toEqual(['jak3', 'mkwii'])
    expect(w.find('[data-tile="mkwii"]').text()).toContain('—')
    expect(w.find('[data-tile="jak3"]').text()).toContain('◆1')
  })
  it('"Activer" pins the game; "Plus actif" offers undo', async () => {
    tracker.slots = slots()
    const w = mount(DashboardV2, { props: { slots: tracker.slots, owner: '*', chips: [] } })
    await w.find('[data-tile="jak3"] button[data-activate]').trigger('click')
    expect(tracker.activity.pinned?.name).toBe('jak3')
    await w.find('[data-active-card="celeste"] button[data-dismiss]').trigger('click')
    expect(tracker.activity.dismissed.celeste).toBe(ago(12))
  })
  it('layout switch is remembered under the v2 key', async () => {
    tracker.slots = slots()
    const w = mount(DashboardV2, { props: { slots: tracker.slots, owner: '*', chips: [] } })
    await w.find('button[data-layout="focus"]').trigger('click')
    expect(localStorage.getItem('amt-v2-layout')).toBe('focus')
    expect(localStorage.getItem('amt-layout')).toBeNull()
  })
})
```

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: `DashboardV2.vue` logic** (mirrors `src/App.vue` lines 46–113):

```ts
const props = defineProps<{ slots: SlotSummary[]; owner: string; chips: { key: string; label: string }[] }>()
const emit = defineEmits<{ 'update:owner': [string] }>()
const sort = ref<SortMode>(loadSort())
watch(sort, saveSort)
const layout = ref<V2Layout>(loadLayout())
watch(layout, saveLayout)
const hideDone = ref(loadHideDone())
watch(hideDone, saveHideDone)
const phone = useMediaQuery('(max-width: 699px)')

const sorted = computed(() => sortBy(sort.value, props.slots, tracker.nowMs, tracker.activeMinutes, tracker.activity))
let lastOrder: string[] = []
const anyOpen = computed(() => Object.values(tracker.open).some(Boolean))
const ordered = computed(() => {
  const r = stableOrder(lastOrder, sorted.value, anyOpen.value || tracker.seenFreeze)
  lastOrder = r.map((s) => s.name)
  return r
})
const visible = computed(() => (hideDone.value ? ordered.value.filter((s) => !s.goal) : ordered.value))
const split = computed(() => splitFeatured(visible.value, tracker.nowMs, tracker.activeMinutes, tracker.activity))
const main = computed(() => compactMain(visible.value, tracker.nowMs, tracker.activeMinutes, tracker.activity))
const focus = computed(() => layout.value === 'focus')
// featured slots get their details loaded (regions on the active cards, the Focus panel)
watch(
  () => (focus.value ? (main.value ? [main.value] : []) : split.value.featured).map((s) => s.name).join('\n'),
  (names) => setFeatured(names ? names.split('\n') : []),
  { immediate: true },
)
```

Template (desktop, Cards): `<TotalsBar …/>`, `<RecentStrip :slots="props.slots" />`, then if `split.featured.length`: heading `◉ Actifs · N` with mono note `auto = check il y a moins de {{ tracker.activeMinutes }} min`, `<ActiveCard v-for … :summary="s" />`; then heading `▸ Où avancer · {{ split.rest.length }} jeux` + mono `tri {{ SORT_LABELS[sort].toLowerCase() }}`, grid `grid grid-cols-1 gap-3 min-[700px]:grid-cols-2 min-[1100px]:grid-cols-3` of `<GameTile>`. Empty states: `!tracker.loaded` → `Chargement…`; `!visible.length` → `Tous les jeux sont terminés.`. Focus and phone branches are added in Task 10 (`v-if="focus"` / `v-if="phone"` placeholders render the Cards layout until then).

- [ ] **Step 4: `TotalsBar.vue`** — one `bg-card border rounded-[14px]` bar: `<strong class="text-logic">{{ t.inLogic }}</strong> en logique`, `{{ t.done }} / {{ t.total }} faits`, `★ {{ t.newItems }} nouveaux` (`text-new`, hidden at 0), `{{ slots.length }} jeux`; then controls: `Tri` segmented buttons from `SORT_LABELS` (`aria-pressed`), `Affichage` segmented `Cartes`/`Focus` (`data-layout="cards|focus"`, `aria-pressed`), checkbox `Masquer terminés` (native `<input type="checkbox">` + `<label>`), `<OwnerSelect>` when `showOwnerFilter(tracker.slots)`. On phone, only `Où avancer · N`, the `Conseillé ▾` select and the Cartes/Focus switch are shown (mockup 2c).

- [ ] **Step 5: `RecentStrip.vue`** — `Derniers reçus` label (mono uppercase), then `feedItems(tracker.recent, new Set(slots.map(s => s.name)), FEED_SHORT)` inline: `★` (`text-new` if `progression`) `<item>` → `<game>` · `formatWhen(i.received_at, tracker.nowMs)`; `Tout voir →` button → `openHistory('received')`. On phone: one line (first item) with `›` that calls `openHistory('received')`.

- [ ] **Step 6: `ActiveCard.vue`** props `{ summary: SlotSummary }`, root `<article :data-active-card="summary.name" class="rounded-[14px] border bg-card p-5">`:
  - top row: `<StateChips>` + right side buttons `✕ Plus actif` (`data-dismiss`, → `dismissWithUndo(summary.name, summary.game)`) and `Détails ▾/▴` (toggles a local `expanded` ref, `aria-expanded`).
  - body: `<BigNumber size="xl">` then the name (`text-2xl font-semibold line-clamp-2`, `:title`), mono line `checks en logique · {{ name }} · {{ done }} / {{ total }} faits`; `★ N nouveau(x) · Marquer comme vu` (button → `markSeen`) when `items.new`.
  - footer: from `tracker.details[name]`, `regionsOf(...).slice(0, 3)` as `Region <count>` mono chips + `+ N régions`; `<GoalBlock compact>`.
  - `expanded` → `<DetailTabs :name="summary.name" />` below.
- [ ] **Step 7: `GameTile.vue`** props `{ summary: SlotSummary }`, root `<article :data-tile="summary.name" class="flex flex-col gap-2 rounded-[14px] border bg-card p-4 transition hover:border-logic/50 focus-within:ring-2 focus-within:ring-logic" :class="{ 'min-[700px]:col-span-2': isOpen(summary.name) }">`:
  - `<BigNumber size="lg">`, name (`line-clamp-2`, `title`), mono `{{ name }} · {{ remaining }} restants`.
  - chips line: `★{{ items.new }}` (`text-new`) when > 0, `◆{{ hints.in_my_world_in_logic }}` (`text-hint`) when > 0, `Logique indisponible` when `logic.kind === 'unavailable'`, `<StateChips>` subset only for error/sleeping/pending/approx states (the full chips are for active cards).
  - buttons: `◎ Activer` (`data-activate`, → `pinActive(name)`), `Détails` (→ `toggleOpen(name)`, `aria-expanded="isOpen(name)"`).
  - `isOpen(name)` → `<DetailTabs :name>`.
- [ ] **Step 8: AppV2** — replace the dashboard placeholder by `<DashboardV2 :slots="selected" :owner="owner" :chips="chips" @update:owner="(k) => (owner = k)" />`.
- [ ] **Step 9: Run** `npm test && npm run build` → PASS. **Step 10: Commit** — `"v2: dashboard in Cards layout (totals, feed, active cards, game tiles)"`.

---

### Task 10: Dashboard — Focus layout and phone

**Files:**
- Create: `src/v2/components/FocusPanel.vue`, `FocusList.vue`, `DetailSheet.vue`, `ActiveCarousel.vue`, `tests/v2/focus.test.ts`
- Modify: `src/v2/views/DashboardV2.vue`

**Interfaces:**
- Consumes: Tasks 8–9; `barParts`; reka-ui `DialogRoot`, `DialogPortal`, `DialogOverlay`, `DialogContent`, `DialogTitle`, `DialogClose`.
- Produces: `FocusPanel` props `{ summary: SlotSummary }`; `FocusList` props `{ slots: SlotSummary[]; current: string | null }`; `DetailSheet` props `{ name: string | null }` emits `close`; `ActiveCarousel` props `{ slots: SlotSummary[] }`.

- [ ] **Step 1: Failing test** `tests/v2/focus.test.ts`

```ts
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import FocusList from '../../src/v2/components/FocusList.vue'
import DashboardV2 from '../../src/v2/views/DashboardV2.vue'
import { installMock } from '../../src/lib/api'
import { tracker } from '../../src/stores/tracker'
import { mk } from '../helpers'

beforeEach(() => {
  installMock({ getSlot: async (n) => ({ ...mk({ name: n }), items_list: [], hints_in_my_world: [], hints_mine_elsewhere: [], in_logic_locations: [] }), markSeen: async () => ({ seen: 0 }) })
  tracker.loaded = true
})
afterEach(() => {
  tracker.slots = []
  tracker.activity = { pinned: null, dismissed: {} }
  localStorage.clear()
})

describe('Focus', () => {
  it('list click shows the game and makes it active', async () => {
    tracker.slots = [mk({ name: 'a', game: 'A' }), mk({ name: 'ww', game: 'The Wind Waker HD', logic: { state: 'ok', count: 58, message: null } })]
    localStorage.setItem('amt-v2-layout', 'focus')
    const w = mount(DashboardV2, { props: { slots: tracker.slots, owner: '*', chips: [] } })
    await flushPromises()
    await w.find('[data-focus-row="ww"]').trigger('click')
    expect(tracker.activity.pinned?.name).toBe('ww')
    expect(w.find('[data-focus-panel]').attributes('data-focus-panel')).toBe('ww')
    expect(w.find('[data-focus-row="ww"]').attributes('aria-current')).toBe('true')
  })
  it('rows: number, tags, remaining', () => {
    const s = [mk({ name: 'a', game: 'A', logic: { state: 'ok', count: 3, message: null }, items: { received: 2, new: 2 }, checks: { done: 1, total: 10, remaining: 9 } })]
    const t = mount(FocusList, { props: { slots: s, current: null } }).text()
    expect(t).toContain('3')
    expect(t).toContain('★2')
    expect(t).toContain('9 rest.')
  })
})
```

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: `FocusPanel.vue`** (mockup 2b): `<article :data-focus-panel="summary.name" class="rounded-[14px] border bg-card p-6">`: `<StateChips>`, mono `● Connecté · dernier check {{ formatWhen(last_check_at) }}`, `✕ Plus actif` (`dismissWithUndo`) when active; `<BigNumber size="xl">` + name + mono `checks en logique · slot · done / total faits · remaining restants`; `<GoalBlock compact>` on the right; then `<DetailTabs :name="summary.name" initial="logic" />`.

- [ ] **Step 4: `FocusList.vue`**: header `{{ slots.length }} jeux · clic = afficher et rendre actif`; `<ul class="max-h-[calc(100vh-220px)] overflow-y-auto">` (desktop; no max-h on phone) of `<li><button :data-focus-row="s.name" :aria-current="s.name === current ? 'true' : undefined" @click="pinActive(s.name)">` with: left rail `w-[3px]` `bg-logic` when current, `<BigNumber size="md">`, name (`truncate`, `title`) + tag `◉ choisi` / `◔ auto` from `cardState`, a 4 px bar (`barParts(done, logic, total)`: `bg-done` then `bg-logic`), `◆N ★N`, `{{ remaining }} rest.` (mono). Current row `bg-logic/15`.

- [ ] **Step 5: `ActiveCarousel.vue`** (phone, mockup 2c): horizontal `snap-x snap-mandatory overflow-x-auto` with one compact card per active slot (`min-w-full snap-start`): StateChips, `x / n` counter (updated on `scroll` from `scrollLeft / clientWidth`), `✕ Plus actif`, BigNumber lg + name + `en logique · done / total`, `<GoalBlock compact>`, button `Détails ↑` emitting `details` with the slot name. Height ≤ ~190 px.

- [ ] **Step 6: `DetailSheet.vue`** (mockup 2e): `DialogRoot :open="!!name"` → `DialogContent` full screen (`fixed inset-0 z-50 flex flex-col bg-popover`), header with StateChips, `DialogClose` `✕` (`aria-label="Fermer"`), `DialogTitle` = BigNumber md + game + mono `slot · done / total`; body `<DetailTabs :name>` (regions shown as a collapsible list on phone: inside DetailTabs, under 700 px, render each region as `<details>` with `<summary>` `▸ Region ◆N count` instead of the two columns).

- [ ] **Step 7: DashboardV2 branches**:
  - desktop + `focus`: `grid grid-cols-[minmax(0,3fr)_minmax(0,2fr)] items-start gap-4` → `<FocusPanel v-if="main" :summary="main" />` + `<FocusList :slots="visible" :current="main?.name ?? null" />`.
  - phone + `cards`: `<ActiveCarousel v-if="split.featured.length" :slots="split.featured" @details="sheet = $event" />`, `<RecentStrip>` (one line), `Où avancer · N` + sort select + Cartes/Focus switch, then a compact list: same rows as `FocusList` but without the active marker (reuse `FocusList` with `current=null`; tapping a row = `pinActive`).
  - phone + `focus`: the main game as a single `ActiveCarousel` card (`[main]`), then `Toucher = rendre actif` + `<FocusList :slots="visible.filter(s => s.name !== main?.name)" :current="null" />`.
  - `<DetailSheet :name="sheet" @close="sheet = null" />` (`const sheet = ref<string | null>(null)`).
- [ ] **Step 8: Run** → PASS. **Step 9: Commit** — `"v2: Focus layout and phone dashboard (carousel, detail sheet)"`.

---

### Task 11: History page

**Files:**
- Create: `src/v2/lib/useHistory.ts`, `src/v2/views/HistoryV2.vue`, `tests/v2/history.test.ts`
- Modify: `src/v2/AppV2.vue` (render `HistoryV2`)

**Interfaces:**
- Consumes: `api.getHistory` (`src/lib/api.ts`), `groupByDay`, `category`, `BEFORE_TRACKING` (Task 5), `historyTab` (Task 7), `formatChecked`, `formatReceived`, `sentText` (`src/lib/history.ts`), `hhmm` (Task 4).
- Produces: `useHistory(slots: () => SlotSummary[], kind: Ref<'sent' | 'received'>, slotFilter: Ref<string>)` returning `{ sent, received, perSlot, totals, loading, error, more, PAGE }` — the logic of `src/components/HistoryView.vue` lines 14–80 moved into a composable **copied** (the v1 file stays untouched).

- [ ] **Step 1: Failing test** `tests/v2/history.test.ts`

```ts
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import HistoryV2 from '../../src/v2/views/HistoryV2.vue'
import { installMock } from '../../src/lib/api'
import type { HistoryPage, SentCheck } from '../../src/lib/types'
import { tracker } from '../../src/stores/tracker'
import { mk } from '../helpers'

const t = (d: number, h: number, m: number) => new Date(2026, 9, d, h, m).getTime() / 1000
const check = (p: Partial<SentCheck>): SentCheck => ({
  slot: 'celeste', game: 'Celeste (Open World)', location_id: 1, location: 'Old Site A - Room s2', checked_at: null, checked_after: null,
  item: 'Sand of Hours', receiver: 'romain_zeldaph', receiver_game: 'The Legend of Zelda - Phantom Hourglass', to_self: false,
  progression: true, useful: false, trap: false, ...p,
})
const page: HistoryPage<SentCheck> = {
  kind: 'sent', total: 3, offset: 0, scout_checked: true,
  slots: [{ name: 'celeste', game: 'Celeste (Open World)', checks: { done: 42, total: 729 }, sent: { known: 42, to_others: 41 }, received: 1 }],
  items: [
    check({ checked_at: t(15, 0, 6), location: 'A' }),
    check({ checked_at: t(14, 23, 58), location: 'B', item: null }),
    check({ checked_at: null, location: 'C', to_self: true, receiver: 'celeste' }),
  ],
}

afterEach(() => (tracker.slots = []))

describe('HistoryV2', () => {
  it('sent checks grouped by day, unknown content, per-game table', async () => {
    installMock({ getSlot: async () => { throw new Error('no') }, markSeen: async () => ({ seen: 0 }), history: async () => page })
    tracker.nowMs = new Date(2026, 9, 15, 0, 30).getTime()
    tracker.slots = [mk({ name: 'celeste', game: 'Celeste (Open World)' })]
    const w = mount(HistoryV2, { props: { slots: tracker.slots, owner: '*', chips: [] } })
    await flushPromises()
    const days = w.findAll('[data-day]').map((d) => d.attributes('data-day'))
    expect(days).toEqual(["Aujourd'hui", 'Hier', 'Avant le suivi'])
    expect(w.text()).toContain('contenu inconnu')
    expect(w.text()).toContain('pour moi')
    expect(w.text()).toContain('PROG')
    expect(w.find('[data-history-table]').text()).toContain('42 / 729')
    expect(w.findAll('[role="tab"]').map((x) => x.text())).toEqual(['Checks envoyés · 3', 'Items reçus'])
  })
})
```

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: `useHistory.ts`** — copy the state, `load()`, `more()`, the two `watch`es (kind/wanted with `immediate: true`; the 1.5 s signature reload with `onBeforeUnmount` cleanup) from `src/components/HistoryView.vue` lines 14–80, parameterised by the arguments above (`props.slots` → `slots()`).

- [ ] **Step 4: `HistoryV2.vue`** (mockups 2h and 2f), props `{ slots; owner; chips }`:
  - title `Historique`; tablist `Checks envoyés · {{ sent?.total ?? '…' }}` / `Items reçus · {{ received?.total ?? '…' }}` bound to `historyTab` (counts only for loaded pages: the test expects `Items reçus` without a count before it is loaded); `Jeu : <select>` (« tous (N) » + one option per slot, game name); `OwnerSelect`; mono note `du plus récent au plus ancien · pages de 200`.
  - desktop: `grid grid-cols-[320px_1fr] gap-4`; left `<table data-history-table>`: header `Jeu · clic = filtrer | Faits | Envoyés | Reçus`, row per `perSlot` (`done / total`, `sentText(s)`, `received`), click → `slotFilter = s.name` (`aria-pressed`), footer `Total`. Phone: `<details>` `Par jeu ▾` with the same three numbers per game.
  - legend: `PROG progression`, `UTILE utile`, `PIÈGE piège`, `sans étiquette = normal`.
  - sent list: `groupByDay(items, (c) => c.checked_at, (c) => c.game, tracker.nowMs)`; each group `<section :data-day="g.label">` with header `{{ g.label }} · {{ g.rows.length }} check(s)`; row: time (`formatChecked(c)` reduced to `HH:MM` when `checked_at` and same-day, `—` when null), source game (only when `showSource`, `font-semibold`), location (mono), then `contenu inconnu` (italic, muted) when `item` null, else category badge + item + `pour moi` (`to_self`) or `pour <receiver> · <receiver_game>`.
  - received list: `groupByDay(items, (i) => i.received_at ?? null, (i) => i.game, tracker.nowMs)`; row: time, badge + item, `pour <game>`, `de <sender> · <location>` / `inventaire de départ` / `donné par le serveur`.
  - `Afficher plus` button when `items.length < total` → `more()`.
  - error: `! <error>` on `bg-warn`; `scout_checked === false` → note `Le contenu des checks faits n'est pas demandé au serveur (Configuration).`
- [ ] **Step 5: AppV2** — `<HistoryV2 v-else-if="view === 'history'" :slots="selected" :owner="owner" :chips="chips" @update:owner="(k) => (owner = k)" />`.
- [ ] **Step 6: Run** → PASS. **Step 7: Commit** — `"v2: History page grouped by day with the per-game table"`.

---

### Task 12: Goals page

**Files:**
- Create: `src/v2/views/GoalsV2.vue`, `tests/v2/goals.test.ts`
- Modify: `src/v2/AppV2.vue`

**Interfaces:**
- Consumes: `sortByGoal`, `goalProgress` (`src/lib/goals.ts`), `GoalBlock` (Task 8), prefs `loadHideReached`/`saveHideReached` (Task 2).

- [ ] **Step 1: Failing test** `tests/v2/goals.test.ts`

```ts
import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import GoalsV2 from '../../src/v2/views/GoalsV2.vue'
import { mk } from '../helpers'

afterEach(() => localStorage.clear())

const slots = [
  mk({ name: 'sdv', game: 'Stardew Valley', owner: 'kuro', goal: true, objective: { summary: 'Restaurer le Community Center', counters: [{ label: 'Bundle', current: 30, target: 30 }], steps: [], source: null } }),
  mk({ name: 'jak1', game: 'Jak and Daxter: The Precursor Legacy', objective: { summary: 'Vaincre Gol et Maia', counters: [{ label: 'Power Cell', current: 4, target: 72 }], steps: [{ label: 'Final Boss', done: false }, { label: 'Secret', done: null }], source: 'slot_data' } }),
  mk({ name: 'none', game: 'Mystery' }),
]

describe('GoalsV2', () => {
  it('count, order, steps and hide reached', async () => {
    const w = mount(GoalsV2, { props: { slots, owner: '*', chips: [] } })
    expect(w.text()).toContain('1 but atteint sur 3')
    expect(w.findAll('[data-goal]').map((g) => g.attributes('data-goal'))).toEqual(['jak1', 'sdv', 'none'])
    expect(w.find('[data-goal="sdv"]').text()).toContain('✓ But atteint')
    expect(w.find('[data-goal="jak1"]').text()).toContain('4 / 72')
    expect(w.find('[data-goal="jak1"]').text()).toContain('invisible pour un tracker')
    expect(w.find('[data-goal="jak1"]').text()).toContain('3 %') // mean of 4/72 and the one known non-final step (0)
    await w.find('input[type="checkbox"]').setValue(true)
    expect(w.find('[data-goal="sdv"]').exists()).toBe(false)
    expect(localStorage.getItem('amt-v2-hide-reached')).toBe('1')
  })
})
```

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: `GoalsV2.vue`** (mockup 2i): header `Objectifs` + `{{ reached }} but{{ reached > 1 ? 's' : '' }} atteint{{ … }} sur {{ slots.length }}`, `OwnerSelect`, checkbox `Masquer les buts atteints` (pref); grid `grid-cols-1 min-[700px]:grid-cols-2 min-[1100px]:grid-cols-3 gap-3` of `<article :data-goal="s.name" class="rounded-[14px] border bg-card p-5">`: game (`line-clamp-2`), mono slot (+ ` · owner`), right `✓ But atteint` (`text-done`) or `{{ Math.round(goalProgress(s) * 100) }} %` (mono), then `<GoalBlock :objective="s.objective" :goal="s.goal" />`; slot without objective: `Pas encore de description du but pour ce jeu.` (muted).
- [ ] **Step 4: AppV2** — `<GoalsV2 v-else-if="view === 'goals'" … />`; remove the last placeholders and any now-unused code.
- [ ] **Step 5: Run** `npm test && npm run build` → PASS. **Step 6: Commit** — `"v2: Goals page"`.

---

### Task 13: Mock history, screenshots, docs, push

**Files:**
- Modify: `src/mock/fixtures.ts` (+ `mockHistory`), `src/mock/install.ts` (+ `history`)
- Create: `scripts/screenshot-v2.mjs`
- Modify (repo root): `BACKLOG.md`, `DECISIONS.md`, `PROGRESS.md`, `docs/API.md` (no change expected — check only)

- [ ] **Step 1: Mock history.** In `src/mock/fixtures.ts` add `export function mockHistory(kind: 'sent' | 'received', slots: string[]): HistoryPage<any>` building, from `mockSlots` filtered by `slots`, a page with: `slots` (one `HistorySlot` per mock slot, using its `checks`, `sent ?? { known: 0, to_others: 0 }`, `items.received`), and `items`: for `sent`, 12 `SentCheck`s over today / yesterday / `checked_at: null` (one with `item: null`), for `received` the `mockRecent()` items mapped to `ReceivedEntry`. In `install.ts` add `history: async (k, s) => mockHistory(k, s)`.
- [ ] **Step 2: Screenshot script** `scripts/screenshot-v2.mjs` (same Chromium lookup as `screenshot.mjs`):

```js
// Screenshots of the v2 at /v2 (run against the mock dev server: VITE_MOCK=1 npx vite --port 38290).
// Usage: node scripts/screenshot-v2.mjs [baseUrl] [outDir]
import { chromium } from '@playwright/test'
import { existsSync, mkdirSync } from 'node:fs'

const base = process.argv[2] ?? 'http://127.0.0.1:38290'
const out = process.argv[3] ?? '../test-output/screenshots/v2'
mkdirSync(out, { recursive: true })
const executablePath = ['/usr/bin/chromium', '/usr/bin/chromium-browser'].find((p) => existsSync(p))
const browser = await chromium.launch(executablePath ? { executablePath } : {})
const shots = [
  ['dashboard-cards', '/v2', { 'amt-v2-layout': 'cards' }],
  ['dashboard-focus', '/v2', { 'amt-v2-layout': 'focus' }],
  ['history', '/v2#history', {}],
  ['goals', '/v2#goals', {}],
]
for (const [device, viewport] of [['desktop', { width: 1440, height: 900 }], ['phone', { width: 390, height: 844 }]]) {
  for (const theme of ['nuit', 'plan']) {
    for (const [name, path, prefs] of shots) {
      const ctx = await browser.newContext({ viewport, reducedMotion: 'reduce' })
      await ctx.addInitScript((p) => { for (const [k, v] of Object.entries(p)) localStorage.setItem(k, v) }, { 'amt-v2-theme': theme, ...prefs })
      const page = await ctx.newPage()
      await page.goto(base + path, { waitUntil: 'networkidle' })
      await page.waitForTimeout(1200)
      await page.screenshot({ path: `${out}/${device}-${theme}-${name}.png`, fullPage: true })
      await ctx.close()
    }
  }
}
await browser.close()
console.log(`screenshots in ${out}`)
```

- [ ] **Step 3: Take them.** `cd frontend && (VITE_MOCK=1 npx vite --port 38290 --strictPort > /tmp/v2-vite.log 2>&1 & echo $! > ../.run/v2-vite.pid)`; wait until `curl -s localhost:38290/v2` answers; `node scripts/screenshot-v2.mjs`; then stop **only** that process: `kill $(cat ../.run/v2-vite.pid)` after checking `ps -p $(cat ../.run/v2-vite.pid) -o cmd=` shows `vite --port 38290`. Look at every PNG in `test-output/screenshots/v2/` and compare with the mockup sections 2a–2k: fix visible defects (overflow at 390 px, text directly on the sky, illegible contrast, horizontal scroll) before continuing, re-running the relevant tests.
- [ ] **Step 4: Production check.** `npm test && npm run build`; then `scripts/app.sh restart` from the repo root and `curl -s localhost:42753/v2 | grep -c '<div id="app">'` → `1`; `curl -s localhost:42753/ | grep -c '<div id="app">'` → `1`.
- [ ] **Step 5: Docs** (French):
  - `BACKLOG.md`: new section `## M20 — v2 « Observatoire » sous /v2 (demandé par Romain le 2026-10-15)` with checked items: entrée séparée `/v2` et lien depuis la v1 ; thèmes Nuit et Plan (tokens, contraste AA testé) + ciel animé ; tableau de bord Cartes et Focus, téléphone ; états des cartes et « Plus actif » avec Annuler ; Historique par jour ; Objectifs ; captures `test-output/screenshots/v2/`. Unchecked follow-ups: 3e/4e thème, refonte Journal/Configuration, retrait de la v1 quand la v2 est validée.
  - `DECISIONS.md`: next D number — « v2 servie à côté de la v1 sous `/v2` : un seul point d'entrée qui charge l'une ou l'autre (code et CSS séparés), mêmes store et API, préférences `amt-v2-*` séparées, choix du jeu actif partagé. Thèmes définis en TS (`src/v2/lib/tokens.ts`) et appliqués en variables CSS pour tester le contraste. »
  - `PROGRESS.md`: one line in the state summary: « 2026-10-15 : v2 Observatoire testable sur `/v2` (M20). »
- [ ] **Step 6: Commit and push** — `git add -A && git commit -m "v2: mock history, screenshots, docs (M20)"` (+ trailers) then `git pull --rebase && git push`. Notify: `bash scripts/overnight/notify.sh "M20 v2" "v2 Observatoire testable sur /v2"`.

---

## Self-review (done by the plan author)

- Spec coverage: entry `/v2` (T1), prefs (T2), tokens + contrast (T3), card states 1–12 (T4 + T8 chips with « Réessayer » + T9 tiles), regions (T4), undo (T4, T8), history by day (T5, T11), sky (T6), shell/menus/nav/banner/owner filter (T7), Cards (T9), Focus + phone + sheet (T10), Goals (T12), screenshots + docs (T13). Journal/Configuration reuse (T7).
- Deviation from spec « la v1 ne charge pas le CSS v2 et inversement »: v2's `theme.css` imports `style.css` to reuse the shadcn variable mapping and base layer; the v1 never loads v2 CSS. The v2 overrides every variable inline, so no v1 colour shows.
- Types used across tasks: `CardState`/`CardCtx`/`cardState`/`hhmm`/`useCardCtx` (T4, T8), `RegionGroup`/`regionsOf` (T4), `DayGroup`/`groupByDay`/`category` (T5), `V2Layout`/`ThemeChoice` (T2), `ResolvedTheme`/`applyV2Theme`/`resolveTheme` (T3), `historyTab`/`openHistory` (T7), `undo`/`dismissWithUndo`/`undoLast` (T4).
