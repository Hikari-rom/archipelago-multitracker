# Dashboard display preferences Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let each device choose which infos the v2 dashboard shows, through a density preset (Essentiel / Standard / Complet) refined by one checkbox per info, in Configuration › Affichage.

**Architecture:** A pure module `frontend/src/v2/lib/display.ts` holds the 11 info keys, the presets and the toggle logic. `frontend/src/v2/lib/prefs.ts` persists the choice in `localStorage` (`amt-v2-display`), the store exposes it as `tracker.display` with `shows(key)` and `setDisplay(p)`, and the dashboard components add `v-if="shows(...)"`. A new `DisplayInfos.vue` block, mounted in `ConfigView.vue`, edits it.

**Tech Stack:** Vue 3 (`<script setup>`), Tailwind, vitest + happy-dom + @vue/test-utils. No backend change.

**Spec:** `docs/superpowers/specs/2026-11-09-dashboard-display-prefs-design.md`

## Global Constraints

- Interface text in French, exactly as written in this plan; code, identifiers, test names and commit messages in English.
- New code carries no comments.
- No new dependency.
- Storage key `amt-v2-display`, JSON `{ preset, shown }`; absent or unreadable → Complet.
- Complet renders exactly as before the feature: the snapshots recorded in Task 1 are never updated (`-u` is forbidden).
- Never hidden: big number, game name, connection error and « Réessayer », BK, approximate logic warning, logic unavailable, state colours (`v2-gold`, `v2-go`, `v2-bk`, row tints), buttons, Détails tabs.
- v1 (`frontend/src/App.vue`, `frontend/src/components/SlotCard.vue`, …) is untouched; `DetailTabs.vue` and `DetailSheet.vue` are untouched.
- Run one test file: `cd frontend && npx vitest run tests/v2/<file>`. Full check: `cd frontend && npm test && npm run build`.
- Commits: imperative English subject, no `Co-Authored-By` or « Generated with » trailer. Do not push. Do not touch `docs/anti-slop/`.

## Review Focus

- Every info unchecked (custom, empty set): no orphan « · », no empty `<p>`, no empty extras row on the active card → tests in Task 4 (tile, active card, carousel, focus panel) and Task 5 (totals bar).
- Private window or corrupted storage (`getItem` throws, JSON garbage, `shown` not an array): Complet, nothing throws → tests in Task 3.
- Stored custom set with unknown or duplicate keys, or equal to a preset: unknown keys dropped, order normalised, preset name recovered → tests in Task 3.
- Connection error, BK, approximate logic while everything is hidden: still shown → test in Task 4.
- A box changed while the dashboard is mounted: the dashboard updates at once, without reload → test in Task 4; a moving ticker chosen but `recent` unchecked: nothing shown → test in Task 5.

## File Structure

- Create `frontend/src/v2/lib/display.ts`: info keys, labels, presets, `applyPreset`, `presetOf`, `toggleInfo`, `joinShown`.
- Modify `frontend/src/v2/lib/prefs.ts`: `loadDisplay`, `saveDisplay`.
- Modify `frontend/src/stores/tracker.ts`: `display` state, `shows`, `setDisplay`.
- Modify `frontend/src/v2/components/{StateChips,GameTile,ActiveCard,FocusPanel,ActiveCarousel,TotalsBar,RecentStrip,FocusList}.vue`: `v-if` on infos.
- Create `frontend/src/v2/components/DisplayInfos.vue`: the Configuration block.
- Modify `frontend/src/components/ConfigView.vue`: mount `DisplayInfos`, disable the ticker select when `recent` is off.
- Tests: create `frontend/tests/v2/displayFixtures.ts`, `display-baseline.test.ts`, `display.test.ts`, `display-cards.test.ts`, `display-lists.test.ts`, `display-config.test.ts`; extend `frontend/tests/v2/prefs.test.ts`.
- Modify `frontend/scripts/screenshot-v2.mjs`, `DECISIONS.md`, `BACKLOG.md`, `PROGRESS.md`, `README.md`.

---

### Task 1: Baseline snapshots of the current dashboard

Records how the dashboard renders today with every info shown. These snapshots are the « Complet = au pixel près » guard for every later task.

**Files:**
- Create: `frontend/tests/v2/displayFixtures.ts`
- Create: `frontend/tests/v2/display-baseline.test.ts`
- Create (generated): `frontend/tests/v2/__snapshots__/display-baseline.test.ts.snap`

**Interfaces:**
- Produces (in `displayFixtures.ts`): `NOW: number`, `ctx: CardCtx`, `rich(over?: Partial<SlotSummary>): SlotSummary`, `recentItem: RecentItem`, `prime(): void`, `reset(): void`.

- [ ] **Step 1: Write the fixtures**

`frontend/tests/v2/displayFixtures.ts`:

```ts
import type { RecentItem, SlotDetail, SlotSummary } from '../../src/lib/types'
import type { CardCtx } from '../../src/v2/lib/card'
import { tracker } from '../../src/stores/tracker'
import { mk } from '../helpers'

export const NOW = 1_800_000_000_000

export const ctx: CardCtx = { nowMs: NOW, activeMinutes: 30, activity: { pinned: null, dismissed: {} }, roomSleeping: false }

export const rich = (over: Partial<SlotSummary> = {}): SlotSummary =>
  mk({
    name: 'romain_tww',
    game: 'The Wind Waker',
    checks: { done: 4, total: 10, remaining: 6 },
    items: { received: 5, new: 2 },
    hints: { mine_elsewhere: 0, in_my_world: 1, in_my_world_in_logic: 1 },
    logic: { state: 'ok', count: 3, message: null },
    go_mode: true,
    last_check_at: NOW / 1000 - 300,
    ...over,
  })

const detail = (s: SlotSummary): SlotDetail => ({
  ...s,
  items_list: [],
  hints_mine_elsewhere: [],
  hints_in_my_world: [],
  in_logic_locations: [
    { id: 1, name: 'Windfall chest', region: 'Windfall', hint: null },
    { id: 2, name: 'Great Sea chest', region: 'Great Sea', hint: null },
  ],
})

export const recentItem: RecentItem = {
  index: 1, name: 'Hookshot', sender: 'kuro', own: false, location: 'Somewhere', progression: true, useful: false,
  trap: false, new: true, slot: 'romain_tww', game: 'The Wind Waker', received_at: NOW / 1000 - 60,
}

export function prime(): void {
  tracker.nowMs = NOW
  tracker.activeMinutes = 30
  tracker.activity = { pinned: null, dismissed: {} }
  tracker.ticker = 'off'
  tracker.details = { romain_tww: detail(rich()) }
  tracker.recent = [recentItem]
}

export function reset(): void {
  tracker.details = {}
  tracker.recent = []
  tracker.ticker = 'off'
}
```

- [ ] **Step 2: Write the baseline test**

`frontend/tests/v2/display-baseline.test.ts`:

```ts
import { mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import ActiveCard from '../../src/v2/components/ActiveCard.vue'
import ActiveCarousel from '../../src/v2/components/ActiveCarousel.vue'
import FocusList from '../../src/v2/components/FocusList.vue'
import FocusPanel from '../../src/v2/components/FocusPanel.vue'
import GameTile from '../../src/v2/components/GameTile.vue'
import RecentStrip from '../../src/v2/components/RecentStrip.vue'
import StateChips from '../../src/v2/components/StateChips.vue'
import TotalsBar from '../../src/v2/components/TotalsBar.vue'
import { cardState } from '../../src/v2/lib/card'
import { ctx, prime, reset, rich } from './displayFixtures'

beforeEach(prime)
afterEach(reset)

const totals = () => mount(TotalsBar, { props: { slots: [rich()], sort: 'auto', layout: 'cards', hideDone: false, owner: '', chips: [] } })
const list = () => mount(FocusList, { props: { slots: [rich(), rich({ name: 'romain_celeste', game: 'Celeste', go_mode: false })], current: 'romain_tww' } })
const all = () => [
  totals(),
  mount(RecentStrip, { props: { slots: [rich()] } }),
  mount(ActiveCard, { props: { summary: rich() } }),
  mount(ActiveCarousel, { props: { slots: [rich()] } }),
  mount(GameTile, { props: { summary: rich() } }),
  mount(FocusPanel, { props: { summary: rich() } }),
  list(),
  mount(StateChips, { props: { state: cardState(rich(), ctx) } }),
]

describe('dashboard with every info shown (Complet)', () => {
  it('the fixture exercises every info', () => {
    const text = all().map((w) => w.text()).join('\n')
    for (const s of ['romain_tww', '4 / 10 faits', '6 restants', '6 rest.', '★', '◆1', 'GO MODE', 'Connecté', 'Actif · auto', 'Windfall', 'Hookshot', 'dernier check'])
      expect(text).toContain(s)
  })
  it('totals bar', () => expect(totals().html()).toMatchSnapshot())
  it('recent strip', () => expect(mount(RecentStrip, { props: { slots: [rich()] } }).html()).toMatchSnapshot())
  it('active card', () => expect(mount(ActiveCard, { props: { summary: rich() } }).html()).toMatchSnapshot())
  it('phone carousel', () => expect(mount(ActiveCarousel, { props: { slots: [rich()] } }).html()).toMatchSnapshot())
  it('tile', () => expect(mount(GameTile, { props: { summary: rich() } }).html()).toMatchSnapshot())
  it('focus panel', () => expect(mount(FocusPanel, { props: { summary: rich() } }).html()).toMatchSnapshot())
  it('focus list', () => expect(list().html()).toMatchSnapshot())
  it('state chips', () => expect(mount(StateChips, { props: { state: cardState(rich(), ctx) } }).html()).toMatchSnapshot())
})
```

- [ ] **Step 3: Run it to record the snapshots**

Run: `cd frontend && npx vitest run tests/v2/display-baseline.test.ts`
Expected: 9 passed, « Snapshots 8 written ». If « the fixture exercises every info » fails, a string of the list is not rendered by today's code: fix the fixture (not the components) until it passes. If the environment has `CI` set, run with `CI= npx vitest run …` so the snapshots are written.

- [ ] **Step 4: Run it again to check the snapshots are stable**

Run: `cd frontend && npx vitest run tests/v2/display-baseline.test.ts`
Expected: 9 passed, « Snapshots 8 passed », nothing written.

- [ ] **Step 5: Commit**

```bash
git add frontend/tests/v2/displayFixtures.ts frontend/tests/v2/display-baseline.test.ts frontend/tests/v2/__snapshots__/display-baseline.test.ts.snap
git commit -m "Snapshot the dashboard with every info shown"
```

---

### Task 2: Info keys, presets and toggling

**Files:**
- Create: `frontend/src/v2/lib/display.ts`
- Test: `frontend/tests/v2/display.test.ts`

**Interfaces:**
- Produces:
  - `type InfoKey = 'slot' | 'done' | 'remaining' | 'newItems' | 'hints' | 'regions' | 'goal' | 'activity' | 'connection' | 'progress' | 'recent'`
  - `INFO_KEYS: readonly InfoKey[]`, `INFO_LABELS: Record<InfoKey, string>`
  - `type Density = 'essentiel' | 'standard' | 'complet'`, `DENSITIES: readonly Density[]`, `DENSITY_LABELS: Record<Density, string>`, `PRESETS: Record<Density, readonly InfoKey[]>`
  - `interface DisplayPrefs { preset: Density | 'custom'; shown: InfoKey[] }`
  - `applyPreset(d: Density): DisplayPrefs`
  - `presetOf(shown: readonly InfoKey[]): Density | 'custom'`
  - `normalizeShown(keys: readonly unknown[]): InfoKey[]`
  - `toggleInfo(p: DisplayPrefs, key: InfoKey, on: boolean): DisplayPrefs`
  - `joinShown(parts: readonly (string | false | null | undefined)[]): string`

- [ ] **Step 1: Write the failing tests**

`frontend/tests/v2/display.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { applyPreset, INFO_KEYS, joinShown, normalizeShown, PRESETS, presetOf, toggleInfo } from '../../src/v2/lib/display'

describe('display presets', () => {
  it('match the spec table', () => {
    expect(PRESETS.essentiel).toEqual(['newItems', 'hints', 'goal'])
    expect(PRESETS.standard).toEqual(['done', 'newItems', 'hints', 'regions', 'goal', 'progress', 'recent'])
    expect(PRESETS.complet).toEqual(INFO_KEYS)
    expect(INFO_KEYS).toHaveLength(11)
  })
  it('applyPreset returns a copy', () => {
    const p = applyPreset('essentiel')
    expect(p).toEqual({ preset: 'essentiel', shown: ['newItems', 'hints', 'goal'] })
    p.shown.push('slot')
    expect(PRESETS.essentiel).toHaveLength(3)
  })
  it('presetOf ignores order and names custom sets', () => {
    expect(presetOf(['goal', 'newItems', 'hints'])).toBe('essentiel')
    expect(presetOf(['goal'])).toBe('custom')
    expect(presetOf([])).toBe('custom')
  })
  it('normalizeShown drops unknown keys and duplicates, keeps the INFO_KEYS order', () => {
    expect(normalizeShown(['goal', 'nope', 'slot', 'goal', 3])).toEqual(['slot', 'goal'])
  })
})

describe('toggleInfo', () => {
  it('leaving a preset makes it custom, coming back names it again', () => {
    const off = toggleInfo(applyPreset('essentiel'), 'hints', false)
    expect(off).toEqual({ preset: 'custom', shown: ['newItems', 'goal'] })
    expect(toggleInfo(off, 'hints', true)).toEqual(applyPreset('essentiel'))
  })
  it('reaches another preset', () => {
    let p = applyPreset('essentiel')
    for (const k of ['done', 'regions', 'progress', 'recent'] as const) p = toggleInfo(p, k, true)
    expect(p.preset).toBe('standard')
  })
  it('is idempotent', () => {
    expect(toggleInfo(applyPreset('complet'), 'slot', true)).toEqual(applyPreset('complet'))
  })
})

describe('joinShown', () => {
  it('joins the shown parts with a middle dot', () => {
    expect(joinShown(['checks en logique', 'romain_tww', '4 / 10 faits'])).toBe('checks en logique · romain_tww · 4 / 10 faits')
    expect(joinShown(['checks en logique', false, null, undefined, ''])).toBe('checks en logique')
    expect(joinShown([false, false])).toBe('')
  })
})
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd frontend && npx vitest run tests/v2/display.test.ts`
Expected: FAIL, « Failed to resolve import "../../src/v2/lib/display" ».

- [ ] **Step 3: Write the module**

`frontend/src/v2/lib/display.ts`:

```ts
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
```

- [ ] **Step 4: Run it to verify it passes**

Run: `cd frontend && npx vitest run tests/v2/display.test.ts`
Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/v2/lib/display.ts frontend/tests/v2/display.test.ts
git commit -m "Add the dashboard info keys and their presets"
```

---

### Task 3: Persist the choice and share it through the store

**Files:**
- Modify: `frontend/src/v2/lib/prefs.ts` (append at the end)
- Modify: `frontend/src/stores/tracker.ts:10` (import), `:34` (state), and append two exported functions after `restoreActivity` (around line 122)
- Test: `frontend/tests/v2/prefs.test.ts` (extend), `frontend/tests/v2/display.test.ts` (extend)

**Interfaces:**
- Consumes: `applyPreset`, `presetOf`, `normalizeShown`, `DENSITIES`, `DisplayPrefs`, `InfoKey` from Task 2.
- Produces: `loadDisplay(): DisplayPrefs`, `saveDisplay(p: DisplayPrefs): void` (prefs.ts); `tracker.display: DisplayPrefs`, `shows(key: InfoKey): boolean`, `setDisplay(p: DisplayPrefs): void` (store).

- [ ] **Step 1: Write the failing prefs tests**

Append to the `describe('v2 prefs', …)` block of `frontend/tests/v2/prefs.test.ts`:

```ts
  it('display: Complet by default, round-trips a custom set', () => {
    expect(p.loadDisplay()).toEqual({ preset: 'complet', shown: [...INFO_KEYS] })
    p.saveDisplay({ preset: 'custom', shown: ['slot', 'goal'] })
    expect(p.loadDisplay()).toEqual({ preset: 'custom', shown: ['slot', 'goal'] })
    expect(localStorage.getItem('amt-v2-display')).not.toBeNull()
  })
  it('display: a named preset is rebuilt from the preset, not from the stored list', () => {
    localStorage.setItem('amt-v2-display', JSON.stringify({ preset: 'essentiel', shown: ['slot'] }))
    expect(p.loadDisplay()).toEqual({ preset: 'essentiel', shown: ['newItems', 'hints', 'goal'] })
  })
  it('display: custom sets are cleaned and recognised', () => {
    localStorage.setItem('amt-v2-display', JSON.stringify({ preset: 'custom', shown: ['goal', 'nope', 'goal', 'slot'] }))
    expect(p.loadDisplay()).toEqual({ preset: 'custom', shown: ['slot', 'goal'] })
    localStorage.setItem('amt-v2-display', JSON.stringify({ preset: 'custom', shown: ['goal', 'hints', 'newItems'] }))
    expect(p.loadDisplay().preset).toBe('essentiel')
  })
  it('display: garbage and blocked storage give Complet', () => {
    for (const v of ['{', '"x"', 'null', '{"preset":"custom","shown":"slot"}', '{"preset":"dense"}']) {
      localStorage.setItem('amt-v2-display', v)
      expect(p.loadDisplay().preset).toBe('complet')
    }
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    expect(p.loadDisplay().preset).toBe('complet')
    expect(() => p.saveDisplay({ preset: 'custom', shown: [] })).not.toThrow()
  })
```

and add at the top of the file, after the existing imports:

```ts
import { INFO_KEYS } from '../../src/v2/lib/display'
```

- [ ] **Step 2: Write the failing store tests**

Append to `frontend/tests/v2/display.test.ts`:

```ts
import { afterEach } from 'vitest'
import { setDisplay, shows, tracker } from '../../src/stores/tracker'

describe('store', () => {
  afterEach(() => {
    setDisplay(applyPreset('complet'))
    localStorage.clear()
  })
  it('starts on Complet', () => {
    expect(tracker.display.preset).toBe('complet')
    expect(INFO_KEYS.every(shows)).toBe(true)
  })
  it('setDisplay changes what shows() answers and saves it', () => {
    setDisplay(applyPreset('essentiel'))
    expect(shows('newItems')).toBe(true)
    expect(shows('slot')).toBe(false)
    expect(JSON.parse(localStorage.getItem('amt-v2-display')!)).toEqual(applyPreset('essentiel'))
  })
})
```

Move the two new `import` lines to the top of the file with the other imports (merge `afterEach` into the existing `vitest` import).

- [ ] **Step 3: Run them to verify they fail**

Run: `cd frontend && npx vitest run tests/v2/prefs.test.ts tests/v2/display.test.ts`
Expected: FAIL, « p.loadDisplay is not a function » and « setDisplay is not a function » (or a missing export error).

- [ ] **Step 4: Implement prefs**

In `frontend/src/v2/lib/prefs.ts`, add to the imports at the top:

```ts
import { applyPreset, DENSITIES, normalizeShown, presetOf, type Density, type DisplayPrefs } from './display'
```

and append at the end of the file:

```ts
export function loadDisplay(): DisplayPrefs {
  try {
    const v = JSON.parse(read('amt-v2-display') ?? 'null')
    if (v && DENSITIES.includes(v.preset)) return applyPreset(v.preset as Density)
    if (v && v.preset === 'custom' && Array.isArray(v.shown)) {
      const shown = normalizeShown(v.shown)
      return { preset: presetOf(shown), shown }
    }
  } catch {
    return applyPreset('complet')
  }
  return applyPreset('complet')
}
export const saveDisplay = (v: DisplayPrefs) => write('amt-v2-display', JSON.stringify(v))
```

- [ ] **Step 5: Implement the store**

In `frontend/src/stores/tracker.ts`:

Replace line 10:

```ts
import { loadHintsLayout, loadTicker } from '../v2/lib/prefs'
```

with:

```ts
import { loadDisplay, loadHintsLayout, loadTicker, saveDisplay } from '../v2/lib/prefs'
import type { DisplayPrefs, InfoKey } from '../v2/lib/display'
```

In the `reactive({...})` object, right after `hintsLayout: loadHintsLayout(),` add:

```ts
  display: loadDisplay(),
```

After the `restoreActivity` function, add:

```ts
export function shows(key: InfoKey): boolean {
  return tracker.display.shown.includes(key)
}

export function setDisplay(p: DisplayPrefs): void {
  tracker.display = p
  saveDisplay(p)
}
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd frontend && npx vitest run tests/v2/prefs.test.ts tests/v2/display.test.ts tests/v2/display-baseline.test.ts`
Expected: all passed; the existing « round-trips and uses v2 keys only » test still passes (the new key starts with `amt-v2-`).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/v2/lib/prefs.ts frontend/src/stores/tracker.ts frontend/tests/v2/prefs.test.ts frontend/tests/v2/display.test.ts
git commit -m "Keep the dashboard info choice on the device and share it in the store"
```

---

### Task 4: Hide infos on the cards

**Files:**
- Modify: `frontend/src/v2/components/StateChips.vue`
- Modify: `frontend/src/v2/components/GameTile.vue`
- Modify: `frontend/src/v2/components/ActiveCard.vue`
- Modify: `frontend/src/v2/components/FocusPanel.vue`
- Modify: `frontend/src/v2/components/ActiveCarousel.vue`
- Test: `frontend/tests/v2/display-cards.test.ts`

**Interfaces:**
- Consumes: `shows`, `setDisplay` (store, Task 3); `applyPreset`, `joinShown`, `InfoKey` (Task 2); `ctx`, `rich`, `prime`, `reset` (Task 1).

- [ ] **Step 1: Write the failing tests**

`frontend/tests/v2/display-cards.test.ts`:

```ts
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import ActiveCard from '../../src/v2/components/ActiveCard.vue'
import ActiveCarousel from '../../src/v2/components/ActiveCarousel.vue'
import FocusPanel from '../../src/v2/components/FocusPanel.vue'
import GameTile from '../../src/v2/components/GameTile.vue'
import GoalBlock from '../../src/v2/components/GoalBlock.vue'
import StateChips from '../../src/v2/components/StateChips.vue'
import { setDisplay } from '../../src/stores/tracker'
import { cardState } from '../../src/v2/lib/card'
import { applyPreset } from '../../src/v2/lib/display'
import { ctx, prime, reset, rich } from './displayFixtures'

const nothing = () => setDisplay({ preset: 'custom', shown: [] })

beforeEach(prime)
afterEach(() => {
  reset()
  setDisplay(applyPreset('complet'))
  localStorage.clear()
})

describe('tile', () => {
  it('Essentiel: no slot nor remaining, new items, hints and go mode kept', () => {
    setDisplay(applyPreset('essentiel'))
    const t = mount(GameTile, { props: { summary: rich() } }).text()
    expect(t).not.toContain('romain_tww')
    expect(t).not.toContain('restants')
    expect(t).toContain('★2')
    expect(t).toContain('◆1')
    expect(t).toContain('GO MODE')
  })
  it('nothing shown: game, number and buttons only, no empty line', () => {
    nothing()
    const w = mount(GameTile, { props: { summary: rich() } })
    expect(w.text()).toContain('The Wind Waker')
    expect(w.text()).toContain('3')
    expect(w.text()).not.toMatch(/★|◆|GO MODE|·/)
    expect(w.find('p').exists()).toBe(false)
    expect(w.find('[data-activate]').exists()).toBe(true)
  })
  it('follows a change made while mounted', async () => {
    const w = mount(GameTile, { props: { summary: rich() } })
    expect(w.text()).toContain('romain_tww')
    setDisplay(applyPreset('essentiel'))
    await nextTick()
    expect(w.text()).not.toContain('romain_tww')
  })
})

describe('active card', () => {
  it('Essentiel: bare caption, new items and goal kept, no regions', () => {
    setDisplay(applyPreset('essentiel'))
    const w = mount(ActiveCard, { props: { summary: rich() } })
    expect(w.find('h3 + p').text()).toBe('checks en logique')
    expect(w.text()).toContain('★ 2 nouveaux')
    expect(w.text()).not.toContain('Windfall')
    expect(w.findComponent(GoalBlock).exists()).toBe(true)
  })
  it('nothing shown: no extras row', () => {
    nothing()
    const w = mount(ActiveCard, { props: { summary: rich() } })
    expect(w.findAll('article > div')).toHaveLength(2)
    expect(w.findComponent(GoalBlock).exists()).toBe(false)
    expect(w.text()).not.toContain('Marquer comme vu')
  })
})

describe('focus panel', () => {
  it('Standard: done kept, slot, remaining and last check hidden', () => {
    setDisplay(applyPreset('standard'))
    const w = mount(FocusPanel, { props: { summary: rich() } })
    expect(w.find('h3 + p').text()).toBe('checks en logique · 4 / 10 faits')
    expect(w.text()).not.toContain('dernier check')
    expect(w.findComponent(GoalBlock).exists()).toBe(true)
  })
  it('nothing shown: bare caption, no goal block', () => {
    nothing()
    const w = mount(FocusPanel, { props: { summary: rich() } })
    expect(w.find('h3 + p').text()).toBe('checks en logique')
    expect(w.findComponent(GoalBlock).exists()).toBe(false)
  })
})

describe('phone carousel', () => {
  it('nothing shown: bare caption, no goal block', () => {
    nothing()
    const w = mount(ActiveCarousel, { props: { slots: [rich()] } })
    expect(w.find('h3 + p').text()).toBe('en logique')
    expect(w.findComponent(GoalBlock).exists()).toBe(false)
  })
})

describe('state chips', () => {
  it('nothing shown: no activity, connection or goal chip', () => {
    nothing()
    const t = mount(StateChips, { props: { state: cardState(rich({ goal: true }), ctx) } }).text()
    expect(t).not.toMatch(/Actif|Expire|Connecté|GO MODE|But atteint/)
  })
  it('nothing shown: sleeping and connecting chips hidden too', () => {
    nothing()
    const sleeping = cardState(rich({ status: 'disconnected' }), { ...ctx, roomSleeping: true })
    expect(mount(StateChips, { props: { state: sleeping } }).text()).not.toContain('En pause')
    const connecting = cardState(rich({ status: 'connecting' }), ctx)
    expect(mount(StateChips, { props: { state: connecting } }).text()).not.toContain('Connexion…')
  })
  it('alerts stay: connection error, BK, approximate logic', () => {
    nothing()
    const error = mount(StateChips, { props: { state: cardState(rich({ status: 'error', error: 'refused' }), ctx) } })
    expect(error.find('[data-retry]').exists()).toBe(true)
    const bk = cardState(rich({ go_mode: false, logic: { state: 'ok', count: 0, message: null } }), ctx)
    expect(mount(StateChips, { props: { state: bk } }).text()).toContain('BK')
    const approx = cardState(rich({ logic: { state: 'ok', count: 3, message: 'options random' } }), ctx)
    expect(mount(StateChips, { props: { state: approx } }).text()).toContain('! options random')
  })
})
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd frontend && npx vitest run tests/v2/display-cards.test.ts`
Expected: FAIL on every test that hides something (e.g. « expected 'The Wind Waker romain_tww · 6 restants…' not to contain 'romain_tww' »). « alerts stay » may already pass.

- [ ] **Step 3: StateChips**

In `frontend/src/v2/components/StateChips.vue`, change the import to:

```ts
import { shows, start } from '../../stores/tracker'
```

Replace the template body (inside the outer `<div class="flex flex-wrap items-center gap-1.5">`) with:

```vue
    <template v-if="shows('activity')">
      <span v-if="state.activity?.kind === 'chosen'" :class="pill" class="border-transparent bg-logic/15 text-logic">◉ Actif · choisi</span>
      <span v-else-if="state.activity?.kind === 'auto'" :class="pill" class="border-transparent bg-logic/15 text-logic">◔ Actif · auto · il y a {{ state.activity.agoMin }} min</span>
      <span v-if="state.activity?.kind === 'auto'" class="text-xs text-muted-foreground">Expire dans {{ state.activity.expiresInMin }} min</span>
      <span v-else-if="state.activity?.kind === 'chosen'" class="text-xs text-muted-foreground">Mémorisé sur cet appareil</span>
    </template>

    <template v-if="state.connection.kind === 'error'">
      <span :class="pill" class="border-transparent bg-warn text-error">! {{ state.connection.message }}</span>
      <button type="button" data-retry class="inline-flex min-h-7 items-center rounded-full border px-2.5 text-xs hover:bg-accent max-[699px]:min-h-11" @click="start()">Réessayer</button>
    </template>
    <template v-else-if="shows('connection')">
      <span v-if="state.connection.kind === 'ok'" :class="pill" class="text-done">● Connecté</span>
      <span v-else-if="state.connection.kind === 'sleeping'" :class="pill" class="text-muted-foreground">☾ En pause<template v-if="state.connection.since">, chiffres de {{ state.connection.since }}</template></span>
      <span v-else :class="pill" class="text-muted-foreground">Connexion…</span>
    </template>

    <span v-if="state.logic.kind === 'unavailable'" data-unavailable :class="pill" class="max-w-full break-words text-muted-foreground">Logique indisponible pour ce jeu<template v-if="state.logic.message"> : {{ state.logic.message }}</template></span>
    <span v-else-if="state.logic.kind === 'pending'" :class="pill" class="text-muted-foreground">{{ state.logic.waiting ? 'En attente de connexion' : 'Calcul de la logique…' }}</span>
    <span v-else-if="state.logic.approx && state.logic.message" :class="pill" class="border-transparent bg-warn text-error">! {{ state.logic.message }}</span>

    <span v-if="state.bk" :class="pill" class="border-transparent bg-bk text-bk-foreground">BK · rien en logique, en attente d'items</span>
    <span v-if="state.goMode && shows('goal')" data-go-pill class="v2-go-pill"><span class="v2-go-text">GO MODE</span><span class="text-muted-foreground">la victoire est en logique</span></span>
    <span v-if="state.goalReached && shows('goal')" :class="pill" class="border-gold-line text-gold">✓ But atteint</span>
```

The connection block now renders the error branch first; in Complet it produces the same elements in the same place, so the baseline snapshot stays identical. Check it in Step 9.

- [ ] **Step 4: GameTile**

In `frontend/src/v2/components/GameTile.vue`:

Change the store import to:

```ts
import { isOpen, pinActive, shows, toggleOpen } from '../../stores/tracker'
```

add:

```ts
import { joinShown } from '../lib/display'
```

and after the `showChips` computed:

```ts
const meta = computed(() =>
  joinShown([shows('slot') && props.summary.name, shows('remaining') && `${props.summary.checks.remaining} restants`]))
```

In the template, replace:

```vue
      <p class="font-mono text-xs text-muted-foreground">{{ summary.name }} · {{ summary.checks.remaining }} restants</p>
```

with:

```vue
      <p v-if="meta" class="font-mono text-xs text-muted-foreground">{{ meta }}</p>
```

and replace the three badges:

```vue
      <span v-if="summary.items.new > 0" class="text-new">★{{ summary.items.new }}</span>
      <span v-if="summary.hints.in_my_world_in_logic > 0" class="text-hint">◆{{ summary.hints.in_my_world_in_logic }}</span>
      <span v-if="state.goMode && !showChips" data-go-pill
```

with:

```vue
      <span v-if="summary.items.new > 0 && shows('newItems')" class="text-new">★{{ summary.items.new }}</span>
      <span v-if="summary.hints.in_my_world_in_logic > 0 && shows('hints')" class="text-hint">◆{{ summary.hints.in_my_world_in_logic }}</span>
      <span v-if="state.goMode && !showChips && shows('goal')" data-go-pill
```

(the rest of the GO MODE `<span>` line is unchanged).

- [ ] **Step 5: ActiveCard**

In `frontend/src/v2/components/ActiveCard.vue`:

Change the store import to:

```ts
import { markSeen, shows, tracker } from '../../stores/tracker'
```

add:

```ts
import { joinShown } from '../lib/display'
```

and after the `regions` computed:

```ts
const meta = computed(() =>
  joinShown([
    'checks en logique',
    shows('slot') && props.summary.name,
    shows('done') && `${props.summary.checks.done} / ${props.summary.checks.total} faits`,
  ]))
```

In the template, replace:

```vue
        <p class="font-mono text-xs text-muted-foreground">checks en logique · {{ summary.name }} · {{ summary.checks.done }} / {{ summary.checks.total }} faits</p>
        <p v-if="summary.items.new" class="mt-1 text-sm">
```

with:

```vue
        <p class="font-mono text-xs text-muted-foreground">{{ meta }}</p>
        <p v-if="summary.items.new && shows('newItems')" class="mt-1 text-sm">
```

and replace the extras row:

```vue
    <div class="mt-4 flex flex-wrap items-center gap-x-3 gap-y-2">
      <span v-for="r in regions.slice(0, 3)" :key="r.name" class="rounded-full border px-2.5 py-0.5 font-mono text-xs">{{ r.name }} {{ r.count }}</span>
      <span v-if="regions.length > 3" class="font-mono text-xs text-muted-foreground">+ {{ regions.length - 3 }} régions</span>
      <GoalBlock :objective=
```

with:

```vue
    <div v-if="shows('regions') || shows('goal')" class="mt-4 flex flex-wrap items-center gap-x-3 gap-y-2">
      <template v-if="shows('regions')">
        <span v-for="r in regions.slice(0, 3)" :key="r.name" class="rounded-full border px-2.5 py-0.5 font-mono text-xs">{{ r.name }} {{ r.count }}</span>
        <span v-if="regions.length > 3" class="font-mono text-xs text-muted-foreground">+ {{ regions.length - 3 }} régions</span>
      </template>
      <GoalBlock v-if="shows('goal')" :objective=
```

(the rest of the `GoalBlock` line is unchanged).

- [ ] **Step 6: FocusPanel**

In `frontend/src/v2/components/FocusPanel.vue`:

Change the store import to:

```ts
import { shows, tracker } from '../../stores/tracker'
```

add:

```ts
import { joinShown } from '../lib/display'
```

and after the `state` computed:

```ts
const meta = computed(() =>
  joinShown([
    'checks en logique',
    shows('slot') && props.summary.name,
    shows('done') && `${props.summary.checks.done} / ${props.summary.checks.total} faits`,
    shows('remaining') && `${props.summary.checks.remaining} restants`,
  ]))
```

In the template, replace:

```vue
        <span v-if="state.connection.kind === 'ok'" class="font-mono text-xs text-muted-foreground">dernier check
```

with:

```vue
        <span v-if="state.connection.kind === 'ok' && shows('activity')" class="font-mono text-xs text-muted-foreground">dernier check
```

replace:

```vue
          <p class="font-mono text-xs text-muted-foreground">checks en logique · {{ summary.name }} · {{ summary.checks.done }} / {{ summary.checks.total }} faits · {{ summary.checks.remaining }} restants</p>
```

with:

```vue
          <p class="font-mono text-xs text-muted-foreground">{{ meta }}</p>
```

and replace `<GoalBlock :objective=` with `<GoalBlock v-if="shows('goal')" :objective=` (rest of the line unchanged).

- [ ] **Step 7: ActiveCarousel**

In `frontend/src/v2/components/ActiveCarousel.vue`:

Change the store import to:

```ts
import { shows, tracker } from '../../stores/tracker'
```

add:

```ts
import { joinShown } from '../lib/display'
```

In the template, replace:

```vue
          <p class="font-mono text-xs text-muted-foreground">en logique · {{ s.checks.done }} / {{ s.checks.total }}</p>
```

with:

```vue
          <p class="font-mono text-xs text-muted-foreground">{{ joinShown(['en logique', shows('done') && `${s.checks.done} / ${s.checks.total}`]) }}</p>
```

and replace `<GoalBlock :objective=` with `<GoalBlock v-if="shows('goal')" :objective=` (rest of the line unchanged).

- [ ] **Step 8: Run the new tests**

Run: `cd frontend && npx vitest run tests/v2/display-cards.test.ts`
Expected: 11 passed.

- [ ] **Step 9: Check Complet did not move**

Run: `cd frontend && npx vitest run tests/v2/display-baseline.test.ts tests/v2/blocks.test.ts tests/v2/card.test.ts tests/v2/pins.test.ts`
Expected: all passed, « Snapshots 8 passed ». A snapshot mismatch means Complet changed: fix the component, never the snapshot.

- [ ] **Step 10: Commit**

```bash
git add frontend/src/v2/components/StateChips.vue frontend/src/v2/components/GameTile.vue frontend/src/v2/components/ActiveCard.vue frontend/src/v2/components/FocusPanel.vue frontend/src/v2/components/ActiveCarousel.vue frontend/tests/v2/display-cards.test.ts
git commit -m "Hide the unchosen infos on the dashboard cards"
```

---

### Task 5: Hide infos on the totals bar, the recent strip and the Focus list

**Files:**
- Modify: `frontend/src/v2/components/TotalsBar.vue`
- Modify: `frontend/src/v2/components/RecentStrip.vue`
- Modify: `frontend/src/v2/components/FocusList.vue`
- Test: `frontend/tests/v2/display-lists.test.ts`

**Interfaces:**
- Consumes: `shows`, `setDisplay` (Task 3); `applyPreset` (Task 2); `rich`, `prime`, `reset` (Task 1).

- [ ] **Step 1: Write the failing tests**

`frontend/tests/v2/display-lists.test.ts`:

```ts
import { mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import FocusList from '../../src/v2/components/FocusList.vue'
import RecentStrip from '../../src/v2/components/RecentStrip.vue'
import TotalsBar from '../../src/v2/components/TotalsBar.vue'
import { setDisplay, tracker } from '../../src/stores/tracker'
import { applyPreset } from '../../src/v2/lib/display'
import { prime, reset, rich } from './displayFixtures'

const nothing = () => setDisplay({ preset: 'custom', shown: [] })
const totals = (slots = [rich()]) => mount(TotalsBar, { props: { slots, sort: 'auto', layout: 'cards', hideDone: false, owner: '', chips: [] } })

beforeEach(prime)
afterEach(() => {
  reset()
  setDisplay(applyPreset('complet'))
  localStorage.clear()
})

describe('totals bar', () => {
  it('Essentiel: no done count, new items and go mode kept', () => {
    setDisplay(applyPreset('essentiel'))
    const w = totals()
    expect(w.text()).not.toContain('faits')
    expect(w.text()).toContain('★ 2 nouveaux')
    expect(w.find('[data-go-total]').exists()).toBe(true)
  })
  it('nothing shown: in logic, game count and BK stay', () => {
    nothing()
    const w = totals([rich(), rich({ name: 'bk', go_mode: false, logic: { state: 'ok', count: 0, message: null } })])
    expect(w.text()).toContain('en logique')
    expect(w.text()).toContain('2 jeux')
    expect(w.find('[data-bk-total]').exists()).toBe(true)
    expect(w.find('[data-go-total]').exists()).toBe(false)
    expect(w.text()).not.toContain('★')
  })
})

describe('recent strip', () => {
  it('hidden when unchecked, static or moving', () => {
    setDisplay(applyPreset('essentiel'))
    expect(mount(RecentStrip, { props: { slots: [rich()] } }).text()).toBe('')
    tracker.ticker = 'agence'
    expect(mount(RecentStrip, { props: { slots: [rich()] } }).find('[data-ticker]').exists()).toBe(false)
  })
  it('shown in Standard', () => {
    setDisplay(applyPreset('standard'))
    expect(mount(RecentStrip, { props: { slots: [rich()] } }).text()).toContain('Hookshot')
  })
})

describe('focus list', () => {
  it('Essentiel: no activity, bar nor remaining; hints and new items kept', () => {
    setDisplay(applyPreset('essentiel'))
    const w = mount(FocusList, { props: { slots: [rich()], current: null } })
    expect(w.text()).not.toContain('auto')
    expect(w.text()).not.toContain('rest.')
    expect(w.find('.bg-done').exists()).toBe(false)
    expect(w.text()).toContain('◆1')
    expect(w.text()).toContain('★2')
  })
  it('Complet keeps the activity marker and the bar', () => {
    const w = mount(FocusList, { props: { slots: [rich()], current: null } })
    expect(w.text()).toContain('◔ auto')
    expect(w.find('.bg-done').exists()).toBe(true)
  })
})
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd frontend && npx vitest run tests/v2/display-lists.test.ts`
Expected: FAIL on the Essentiel and « nothing shown » tests; « shown in Standard » and « Complet keeps… » pass already.

- [ ] **Step 3: TotalsBar**

In `frontend/src/v2/components/TotalsBar.vue`, change the store import to:

```ts
import { shows, tracker } from '../../stores/tracker'
```

In the template, replace:

```vue
        <span>{{ t.done }} / {{ t.total }} faits</span>
        <span v-if="t.newItems" class="text-new">★ {{ t.newItems }} nouveaux</span>
        <span v-if="go" data-go-total>
```

with:

```vue
        <span v-if="shows('done')">{{ t.done }} / {{ t.total }} faits</span>
        <span v-if="t.newItems && shows('newItems')" class="text-new">★ {{ t.newItems }} nouveaux</span>
        <span v-if="go && shows('goal')" data-go-total>
```

(the rest of the `data-go-total` line is unchanged).

- [ ] **Step 4: RecentStrip**

In `frontend/src/v2/components/RecentStrip.vue`, change the store import to:

```ts
import { shows, tracker } from '../../stores/tracker'
```

and replace the `items` computed with:

```ts
const items = computed(() =>
  shows('recent')
    ? feedItems(tracker.recent, new Set(props.slots.map((s) => s.name)), ticker.value ? TICKER_COUNT : phone.value ? 1 : FEED_SHORT)
    : [])
```

- [ ] **Step 5: FocusList**

In `frontend/src/v2/components/FocusList.vue`, change the store import to:

```ts
import { pinActive, shows } from '../../stores/tracker'
```

In the template, replace:

```vue
              <span v-if="st(s).activity?.kind === 'chosen'" class="shrink-0 font-mono text-[11px] text-logic">◉ choisi</span>
              <span v-else-if="st(s).activity?.kind === 'auto'" class="shrink-0 font-mono text-[11px] text-logic">◔ auto</span>
            </span>
            <span class="mt-1 flex h-1 overflow-hidden rounded-full bg-muted" aria-hidden="true">
```

with:

```vue
              <span v-if="st(s).activity?.kind === 'chosen' && shows('activity')" class="shrink-0 font-mono text-[11px] text-logic">◉ choisi</span>
              <span v-else-if="st(s).activity?.kind === 'auto' && shows('activity')" class="shrink-0 font-mono text-[11px] text-logic">◔ auto</span>
            </span>
            <span v-if="shows('progress')" class="mt-1 flex h-1 overflow-hidden rounded-full bg-muted" aria-hidden="true">
```

and replace:

```vue
            <span v-if="s.hints.in_my_world_in_logic" class="text-hint">◆{{ s.hints.in_my_world_in_logic }} </span>
            <span v-if="s.items.new" class="text-new">★{{ s.items.new }}</span>
          </span>
          <span class="w-16 shrink-0 text-right font-mono text-xs text-muted-foreground">{{ s.checks.remaining }} rest.</span>
```

with:

```vue
            <span v-if="s.hints.in_my_world_in_logic && shows('hints')" class="text-hint">◆{{ s.hints.in_my_world_in_logic }} </span>
            <span v-if="s.items.new && shows('newItems')" class="text-new">★{{ s.items.new }}</span>
          </span>
          <span v-if="shows('remaining')" class="w-16 shrink-0 text-right font-mono text-xs text-muted-foreground">{{ s.checks.remaining }} rest.</span>
```

- [ ] **Step 6: Run the tests**

Run: `cd frontend && npx vitest run tests/v2/display-lists.test.ts tests/v2/display-baseline.test.ts tests/v2/focus.test.ts tests/v2/ticker.test.ts tests/v2/dashboard.test.ts`
Expected: all passed, « Snapshots 8 passed ».

- [ ] **Step 7: Commit**

```bash
git add frontend/src/v2/components/TotalsBar.vue frontend/src/v2/components/RecentStrip.vue frontend/src/v2/components/FocusList.vue frontend/tests/v2/display-lists.test.ts
git commit -m "Hide the unchosen infos on the totals bar, the recent strip and the Focus list"
```

---

### Task 6: The Configuration block

**Files:**
- Create: `frontend/src/v2/components/DisplayInfos.vue`
- Modify: `frontend/src/components/ConfigView.vue:35` (import), the « Affichage » card (around lines 608-657)
- Test: `frontend/tests/v2/display-config.test.ts`

**Interfaces:**
- Consumes: `setDisplay`, `shows`, `tracker` (Task 3); `applyPreset`, `toggleInfo`, `DENSITIES`, `DENSITY_LABELS`, `INFO_KEYS`, `INFO_LABELS`, `Density`, `InfoKey` (Task 2).
- Produces: component `DisplayInfos` (no props, no events); test hooks `data-display-infos`, `data-density="<d>"`, `data-info="<key>"`, `data-custom`.

- [ ] **Step 1: Write the failing tests**

`frontend/tests/v2/display-config.test.ts`:

```ts
import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import DisplayInfos from '../../src/v2/components/DisplayInfos.vue'
import { setDisplay, tracker } from '../../src/stores/tracker'
import { applyPreset, INFO_KEYS } from '../../src/v2/lib/display'

afterEach(() => {
  setDisplay(applyPreset('complet'))
  localStorage.clear()
})

const checked = (w: ReturnType<typeof mount>) =>
  w.findAll('[data-info]').filter((c) => (c.element as HTMLInputElement).checked).map((c) => c.attributes('data-info'))
const pressed = (w: ReturnType<typeof mount>) =>
  w.findAll('[data-density]').filter((b) => b.attributes('aria-pressed') === 'true').map((b) => b.attributes('data-density'))

describe('Configuration › Infos du tableau de bord', () => {
  it('Complet by default: every box checked', () => {
    const w = mount(DisplayInfos)
    expect(checked(w)).toEqual([...INFO_KEYS])
    expect(pressed(w)).toEqual(['complet'])
    expect(w.find('[data-custom]').exists()).toBe(false)
    expect(w.text()).toContain('restent toujours affichés')
  })
  it('a preset checks its boxes and is saved', async () => {
    const w = mount(DisplayInfos)
    await w.find('[data-density="essentiel"]').trigger('click')
    expect(checked(w)).toEqual(['newItems', 'hints', 'goal'])
    expect(pressed(w)).toEqual(['essentiel'])
    expect(JSON.parse(localStorage.getItem('amt-v2-display')!).preset).toBe('essentiel')
  })
  it('a box out of the preset shows « Personnalisé », back in names the preset again', async () => {
    const w = mount(DisplayInfos)
    await w.find('[data-density="essentiel"]').trigger('click')
    await w.find('[data-info="hints"]').setValue(false)
    expect(w.find('[data-custom]').text()).toContain('Personnalisé')
    expect(pressed(w)).toEqual([])
    expect(tracker.display.shown).toEqual(['newItems', 'goal'])
    await w.find('[data-info="hints"]').setValue(true)
    expect(pressed(w)).toEqual(['essentiel'])
    expect(w.find('[data-custom]').exists()).toBe(false)
  })
})
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd frontend && npx vitest run tests/v2/display-config.test.ts`
Expected: FAIL, « Failed to resolve import "../../src/v2/components/DisplayInfos.vue" ».

- [ ] **Step 3: Write the component**

`frontend/src/v2/components/DisplayInfos.vue`:

```vue
<script setup lang="ts">
import { setDisplay, tracker } from '../../stores/tracker'
import { applyPreset, DENSITIES, DENSITY_LABELS, INFO_KEYS, INFO_LABELS, toggleInfo, type Density, type InfoKey } from '../lib/display'

const seg = 'inline-flex rounded-lg border p-0.5'
const segBtn = (on: boolean) => ['min-h-8 rounded-md px-3 text-sm max-[699px]:min-h-11', on ? 'bg-accent font-semibold text-foreground' : 'text-muted-foreground hover:text-foreground']
const pick = (d: Density) => setDisplay(applyPreset(d))
const toggle = (key: InfoKey, e: Event) => setDisplay(toggleInfo(tracker.display, key, (e.target as HTMLInputElement).checked))
</script>

<template>
  <fieldset data-display-infos class="flex flex-col gap-2">
    <legend class="mb-2 text-sm font-medium">Infos du tableau de bord</legend>
    <div class="flex flex-wrap items-center gap-2 text-sm">
      Densité
      <div :class="seg" role="group" aria-label="Densité">
        <button
          v-for="d in DENSITIES" :key="d" type="button" :data-density="d"
          :aria-pressed="tracker.display.preset === d" :class="segBtn(tracker.display.preset === d)" @click="pick(d)"
        >{{ DENSITY_LABELS[d] }}</button>
      </div>
      <span v-if="tracker.display.preset === 'custom'" data-custom class="text-muted-foreground text-xs">· Personnalisé</span>
    </div>
    <div class="grid grid-cols-1 gap-x-6 min-[700px]:grid-flow-col min-[700px]:grid-cols-3 min-[700px]:grid-rows-4">
      <label v-for="k in INFO_KEYS" :key="k" class="flex min-h-8 items-center gap-2 text-sm max-[699px]:min-h-11">
        <input type="checkbox" class="size-4" :data-info="k" :checked="tracker.display.shown.includes(k)" @change="toggle(k, $event)" />
        {{ INFO_LABELS[k] }}
      </label>
    </div>
    <p class="text-muted-foreground text-xs">
      Le gros chiffre, le nom du jeu et les alertes (erreur, BK, logique approximative) restent toujours affichés.
      Interface v2 seulement.
    </p>
  </fieldset>
</template>
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd frontend && npx vitest run tests/v2/display-config.test.ts`
Expected: 3 passed.

- [ ] **Step 5: Mount it in the Configuration**

In `frontend/src/components/ConfigView.vue`:

Replace line 35:

```ts
import { refreshMeta, setActiveMode, setView, tracker } from '../stores/tracker'
```

with:

```ts
import { refreshMeta, setActiveMode, setView, shows, tracker } from '../stores/tracker'
import DisplayInfos from '../v2/components/DisplayInfos.vue'
```

In the « Affichage (sur cet appareil) » card, right after `<CardContent class="flex flex-col gap-3 px-5">` (the one following `<CardTitle>Affichage …</CardTitle>`), insert:

```vue
          <DisplayInfos />
```

and replace:

```vue
            <select :value="tracker.ticker" data-ticker-style :class="cn(selectClass, 'w-auto')" @change="onTicker">
```

with:

```vue
            <select :value="tracker.ticker" data-ticker-style :disabled="!shows('recent')" :class="cn(selectClass, 'w-auto disabled:opacity-50')" @change="onTicker">
```

- [ ] **Step 6: Type-check and run the whole front suite**

Run: `cd frontend && npm test && npm run build`
Expected: every test passes (« Snapshots 8 passed »), `vue-tsc --noEmit` reports no error, `vite build` succeeds.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/v2/components/DisplayInfos.vue frontend/src/components/ConfigView.vue frontend/tests/v2/display-config.test.ts
git commit -m "Let the Configuration choose the dashboard infos"
```

---

### Task 7: Screenshots and repo docs

**Files:**
- Modify: `frontend/scripts/screenshot-v2.mjs:12-17`
- Modify: `DECISIONS.md` (append), `BACKLOG.md` (append), `PROGRESS.md` (state list), `README.md:19`

- [ ] **Step 1: Add the density shots**

In `frontend/scripts/screenshot-v2.mjs`, replace the `shots` array with:

```js
const shots = [
  ['dashboard-cards', '/', { 'amt-v2-layout': 'cards' }],
  ['dashboard-focus', '/', { 'amt-v2-layout': 'focus' }],
  ['dashboard-cards-essentiel', '/', { 'amt-v2-layout': 'cards', 'amt-v2-display': '{"preset":"essentiel","shown":[]}' }],
  ['dashboard-cards-standard', '/', { 'amt-v2-layout': 'cards', 'amt-v2-display': '{"preset":"standard","shown":[]}' }],
  ['dashboard-focus-essentiel', '/', { 'amt-v2-layout': 'focus', 'amt-v2-display': '{"preset":"essentiel","shown":[]}' }],
  ['config', '/#config', {}],
  ['history', '/#history', {}],
  ['goals', '/#goals', {}],
]
```

- [ ] **Step 2: Take the screenshots on the mock server and look at them**

Port 38290 is also used by `tests/test_config_m9.py`: do not run pytest at the same time.

```bash
cd frontend && (VITE_MOCK=1 npx vite --port 38290 > ../test-output/logs/vite-mock.log 2>&1 &) && sleep 8 \
  && node scripts/screenshot-v2.mjs && pkill -f "vite --port 38290"
```

Expected: « screenshots in ../test-output/screenshots/v2 ». Open with the Read tool `desktop-nuit-dashboard-cards.png`, `desktop-nuit-dashboard-cards-essentiel.png`, `desktop-nuit-dashboard-cards-standard.png`, `phone-nuit-dashboard-cards-essentiel.png`, `desktop-nuit-dashboard-focus-essentiel.png`, `desktop-plan-config.png`, `phone-plan-config.png` and check:
- Essentiel: tiles show the number, the game, ★, ◆, GO MODE and the buttons, no slot line, no strip;
- Standard: strip present, no slot line, Focus bar present;
- Complet (`dashboard-cards`): same as before the feature;
- Configuration: the « Infos du tableau de bord » block is first in « Affichage », 3 columns on desktop, 1 on phone.

If the mock server serves no `#config` page, drop that shot and say so in the report.

- [ ] **Step 3: DECISIONS.md**

Append at the end of `DECISIONS.md`:

```markdown

## D36 — Infos du tableau de bord au choix, par appareil (2026-11-09, demandé par Romain)
- **Le problème** : des amis de Romain, chacun sur sa propre instance, trouvent le tableau de bord v2 trop chargé.
- **Réglage par appareil** (`localStorage`, `amt-v2-display`), dans Configuration › Affichage : densité Essentiel /
  Standard / Complet, puis une case par info (11 infos), qui vaut partout (totaux, bandeau, cartes, tuiles, Focus).
  Pas de réglage serveur : chaque ami a son instance, et les autres réglages d'affichage sont déjà par appareil.
- **Complet par défaut** : l'affichage d'avant, au pixel près (instantanés `tests/v2/display-baseline.test.ts`).
- **Jamais masqués** : gros chiffre, nom du jeu, alertes (erreur de connexion, BK, logique approximative ou
  indisponible), couleurs d'état, boutons, onglets Détails.
- Spec : `docs/superpowers/specs/2026-11-09-dashboard-display-prefs-design.md`.
```

- [ ] **Step 4: BACKLOG.md**

Append at the end of `BACKLOG.md`:

```markdown

## M30 — Infos du tableau de bord au choix (demandé par Romain le 2026-11-09, D36)
- [x] Densité Essentiel / Standard / Complet et une case par info dans Configuration › Affichage (sur cet appareil)
- [x] Totaux, bandeau, cartes actives, carrousel téléphone, tuiles, panneau et liste Focus suivent le réglage ;
  alertes toujours affichées ; Complet par défaut, identique à avant
```

- [ ] **Step 5: PROGRESS.md**

In `PROGRESS.md`, section « État actuel », after the line that starts with `   Go mode de \`natazox_slime\` vérifié`, insert:

```markdown
   2026-11-09 : infos du tableau de bord au choix, par appareil (Configuration › Affichage : Essentiel / Standard /
   Complet et une case par info ; Complet par défaut) (M30, D36).
```

- [ ] **Step 6: README.md**

In `README.md` line 19, replace `affichage Cartes ou Focus, thèmes Nuit et Plan, téléphone.` with
`affichage Cartes ou Focus, infos affichées au choix (Configuration › Affichage : Essentiel, Standard ou Complet), thèmes Nuit et Plan, téléphone.`

- [ ] **Step 7: Final check and commit**

Run: `cd frontend && npm test && npm run build`
Expected: all passed, build OK.

```bash
git add frontend/scripts/screenshot-v2.mjs DECISIONS.md BACKLOG.md PROGRESS.md README.md
git commit -m "Document the dashboard info choice (D36)"
```

Do not push: Romain decides.
