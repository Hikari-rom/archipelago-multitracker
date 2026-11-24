import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import ConfigView from '../src/components/ConfigView.vue'

const json = (body: unknown) => new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } })
const NO_UPDATE = { mode: 'none', current: { version: null }, latest: null, available: false, blocked: null, checked_at: null, check_error: null, running: false, status: null }

afterEach(() => {
  vi.unstubAllGlobals()
  history.replaceState(null, '', '/')
})

/** Tracked: A (KH2, player kuro), C (Jak 3 without its yaml). In the room only: B (Hades). */
function setup(o: { wide: boolean; goalOverride?: boolean }) {
  vi.stubGlobal('matchMedia', (q: string) => ({
    matches: o.wide && q.includes('min-width'), media: q, onchange: null,
    addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {}, dispatchEvent: () => false,
  }))
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      if (url === '/api/config') {
        return json({
          room_url: 'https://archipelago.gg/room/x', server: null, has_password: false, player_yamls: [], yamls: [],
          goal_override: !!o.goalOverride,
          slots: [
            { name: 'A', game: 'Kingdom Hearts 2', owner: 'kuro', yaml: null, goal: {} },
            { name: 'C', game: 'Jak 3', owner: null, yaml: null, goal: {} },
          ],
          games: {
            'Kingdom Hearts 2': { logic: true, needs_yaml: false, goal_options: [{ option: 'Goal', display: 'Goal', choices: ['three_proofs'] }] },
            'Jak 3': { logic: true, needs_yaml: true },
          },
        })
      }
      if (url === '/api/discover') {
        return json({ room_url: 'https://archipelago.gg/room/x', server: 'archipelago.gg:1', players: [
          { name: 'A', game: 'Kingdom Hearts 2' }, { name: 'B', game: 'Hades' }, { name: 'C', game: 'Jak 3' },
        ] })
      }
      if (url === '/api/update') return json(NO_UPDATE)
      if (url === '/api/apworlds') return json({ dir: 'data/apworlds', default_source: null, files: [] })
      return json({})
    }),
  )
}

const shown = (w: VueWrapper) => w.findAll('[data-slot-row]').map((r) => r.attributes('data-slot-row'))
async function mode(w: VueWrapper, m: string) {
  await w.find(`[data-slot-mode="${m}"]`).trigger('click')
}

describe('Slots tab', () => {
  it('PC: tracked slots first, then the whole room, the ones to fix, and a search on the player', async () => {
    setup({ wide: true })
    const w = mount(ConfigView)
    await flushPromises()
    expect(w.find('[data-slot-mode="tracked"]').attributes('aria-pressed')).toBe('true')
    expect(shown(w)).toEqual(['A', 'C'])
    await mode(w, 'all')
    expect(shown(w)).toEqual(['A', 'C', 'B']) // saved slots first, then the rest of the room (as before)
    await mode(w, 'fix')
    expect(shown(w)).toEqual(['C'])
    await mode(w, 'all')
    await w.find('input[type="search"]').setValue('KURO')
    expect(shown(w)).toEqual(['A'])
  })

  it('PC: the header box unticks the slots shown, and only them', async () => {
    setup({ wide: true })
    const w = mount(ConfigView)
    await flushPromises()
    await w.find('input[type="search"]').setValue('Jak')
    await w.find('[aria-label="cocher les slots affichés"]').trigger('click')
    await w.find('input[type="search"]').setValue('')
    await mode(w, 'all')
    const state = (n: string) => w.find(`[aria-label="suivre ${n}"]`).attributes('data-state')
    expect(state('C')).toBe('unchecked')
    expect(state('A')).toBe('checked')
  })

  it('PC: the « But » column only when the goal is chosen by hand', async () => {
    setup({ wide: true })
    const off = mount(ConfigView)
    await flushPromises()
    expect(off.find('table').exists()).toBe(true)
    expect(off.findAll('th').map((t) => t.text())).not.toContain('But')
    setup({ wide: true, goalOverride: true })
    const on = mount(ConfigView)
    await flushPromises()
    expect(on.findAll('th').map((t) => t.text())).toContain('But')
    expect(on.find('[data-goal-choice]').exists()).toBe(true)
  })

  it('phone: a list, a tap opens the slot settings, a change there shows the save bar', async () => {
    setup({ wide: false })
    const w = mount(ConfigView, { attachTo: document.body })
    await flushPromises()
    expect(w.find('table').exists()).toBe(false)
    await w.find('[data-slot-row="A"] [data-slot-open]').trigger('click')
    await flushPromises()
    const sheet = document.querySelector('[data-slot-sheet]')!
    expect(sheet).not.toBeNull()
    expect(sheet.querySelector('[aria-label="yaml de A"]')).not.toBeNull()
    const owner = sheet.querySelector('[aria-label="joueur de A"]') as HTMLInputElement
    owner.value = 'romain'
    owner.dispatchEvent(new Event('input'))
    await flushPromises()
    expect(w.find('[data-save-bar]').exists()).toBe(true)
    w.unmount()
  })
})
