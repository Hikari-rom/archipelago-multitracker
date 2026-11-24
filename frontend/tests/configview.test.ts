import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import ConfigView from '../src/components/ConfigView.vue'
import { tracker } from '../src/stores/tracker'

const KH2 = [{ option: 'Goal', display: 'Goal', choices: ['three_proofs', 'hitlist'] }]

afterEach(() => {
  vi.unstubAllGlobals()
  history.replaceState(null, '', '/')
})

const NO_UPDATE = { mode: 'none', current: { version: null }, latest: null, available: false, blocked: null, checked_at: null, check_error: null, running: false, status: null }
const KH2_A = { name: 'A', game: 'Kingdom Hearts 2', owner: null, yaml: null, goal: {} }
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

/** Fake server: the saved configuration, the room, the update state; PUT bodies are collected in `puts`. */
function server(config: Record<string, unknown>, o: { players?: { name: string; game: string }[]; update?: Record<string, unknown>; putStatus?: number } = {}) {
  const puts: Record<string, unknown>[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      if (url === '/api/config' && init?.method === 'PUT') {
        puts.push(JSON.parse(String(init.body)))
        return o.putStatus ? json({ detail: 'disque plein' }, o.putStatus) : json({ ok: true })
      }
      if (url === '/api/config') {
        return json({
          room_url: null, server: '127.0.0.1:1', has_password: false, player_yamls: [], yamls: [],
          games: { 'Kingdom Hearts 2': { logic: true, needs_yaml: false } }, ...config,
        })
      }
      if (url === '/api/discover') return json({ room_url: 'https://archipelago.gg/room/x', server: 'archipelago.gg:1', players: o.players ?? [] })
      if (url === '/api/update') return json({ ...NO_UPDATE, ...o.update })
      if (url === '/api/apworlds') return json({ dir: 'data/apworlds', default_source: null, files: [] })
      return json({})
    }),
  )
  return puts
}

const tabs = (w: ReturnType<typeof mount>) => w.findAll('[role="tab"]')
const selected = (w: ReturnType<typeof mount>) => w.find('[role="tab"][aria-selected="true"]').attributes('data-config-tab')
async function openTab(w: ReturnType<typeof mount>, tab: string) {
  await w.find(`[data-config-tab="${tab}"]`).trigger('mousedown', { button: 0, ctrlKey: false })
  await flushPromises()
}

describe('ConfigView', () => {
  it('shows the page before the victory conditions, then asks for the tracked games still pending', async () => {
    let release: () => void = () => {}
    const asked: string[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        let body: unknown = {}
        if (url === '/api/config') {
          body = {
            room_url: null, server: '127.0.0.1:1', has_password: false, goal_override: true,
            slots: [{ name: 'A', game: 'Kingdom Hearts 2', owner: null, yaml: null, goal: {} }],
            player_yamls: [], yamls: [], games: { 'Kingdom Hearts 2': { logic: true, needs_yaml: false } },
            goal_options_pending: ['Kingdom Hearts 2'],
          }
        } else if (url.startsWith('/api/goal-options')) {
          asked.push(url)
          await new Promise<void>((r) => (release = r))
          body = { games: { 'Kingdom Hearts 2': KH2 } }
        } else if (url === '/api/update') {
          body = { mode: 'none', current: { version: null }, latest: null, available: false, blocked: null, checked_at: null, check_error: null, running: false, status: null }
        } else if (url === '/api/apworlds') {
          body = { dir: 'data/apworlds', default_source: null, files: [] }
        }
        return new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } })
      }),
    )
    const w = mount(ConfigView)
    await flushPromises()
    expect(w.find('[data-goal-loading]').exists()).toBe(true)
    expect(w.find('[data-goal-choice]').exists()).toBe(false)
    expect(asked).toEqual(['/api/goal-options?game=Kingdom%20Hearts%202'])
    release()
    await flushPromises()
    expect(w.find('[data-goal-loading]').exists()).toBe(false)
    expect(w.find('[data-goal-choice]').text()).toContain('But · Goal')
  })

  it('the « fin » box only for the games with logic, off when the slot turned it off', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        let body: unknown = {}
        if (url === '/api/config') {
          body = {
            room_url: null, server: '127.0.0.1:1', has_password: false,
            slots: [
              { name: 'A', game: 'Kingdom Hearts 2', owner: null, yaml: null, goal: {}, goal_needs: false },
              { name: 'B', game: 'Hades', owner: null, yaml: null, goal: {} },
            ],
            player_yamls: [], yamls: [], games: { 'Kingdom Hearts 2': { logic: true, needs_yaml: false } },
          }
        } else if (url === '/api/update') {
          body = { mode: 'none', current: { version: null }, latest: null, available: false, blocked: null, checked_at: null, check_error: null, running: false, status: null }
        } else if (url === '/api/apworlds') {
          body = { dir: 'data/apworlds', default_source: null, files: [] }
        }
        return new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } })
      }),
    )
    const w = mount(ConfigView)
    await flushPromises()
    const boxes = w.findAll('[data-goal-needs]')
    expect(boxes).toHaveLength(1)
    expect(boxes[0].find('[aria-label="ce qui manque pour la victoire de A"]').attributes('data-state')).toBe('unchecked')
  })

  it('five tabs, Slots open when slots are configured', async () => {
    server({ slots: [KH2_A] })
    const w = mount(ConfigView)
    await flushPromises()
    expect(tabs(w).map((t) => t.attributes('data-config-tab'))).toEqual(['slots', 'room', 'fonctions', 'affichage', 'app'])
    expect(selected(w)).toBe('slots')
    expect(w.find('[data-config-summary]').text()).toContain('1 suivis')
  })

  it('first setup: Room open, the save bar shown as soon as a slot is ticked, no « Annuler »', async () => {
    server(
      { slots: [], room_url: 'https://archipelago.gg/room/x', server: null, yamls: [{ path: 'config/players/a.yaml', players: [{ name: 'A', game: 'Kingdom Hearts 2' }], error: null }] },
      { players: [{ name: 'A', game: 'Kingdom Hearts 2' }] },
    )
    const w = mount(ConfigView)
    await flushPromises()
    expect(selected(w)).toBe('room')
    const bar = w.find('[data-save-bar]')
    expect(bar.exists()).toBe(true)
    expect(bar.text()).not.toContain('Annuler')
  })

  it('a change shows the save bar, survives a change of tab, « Annuler » puts it back', async () => {
    server({ slots: [KH2_A] })
    const w = mount(ConfigView)
    await flushPromises()
    expect(w.find('[data-save-bar]').exists()).toBe(false)
    const fin = () => w.find('[aria-label="ce qui manque pour la victoire de A"]')
    await fin().trigger('click')
    expect(w.find('[data-save-bar]').exists()).toBe(true)
    await openTab(w, 'room')
    expect(selected(w)).toBe('room')
    await openTab(w, 'slots')
    expect(fin().attributes('data-state')).toBe('unchecked')
    await w.findAll('[data-save-bar] button').find((b) => b.text() === 'Annuler')!.trigger('click')
    await flushPromises()
    expect(w.find('[data-save-bar]').exists()).toBe(false)
    expect(fin().attributes('data-state')).toBe('checked')
  })

  it('« Enregistrer » sends the page; an error keeps the bar with its message', async () => {
    const puts = server({ slots: [KH2_A] }, { putStatus: 500 })
    const w = mount(ConfigView)
    await flushPromises()
    await w.find('[aria-label="ce qui manque pour la victoire de A"]').trigger('click')
    await w.findAll('[data-save-bar] button').find((b) => b.text() === 'Enregistrer')!.trigger('click')
    await flushPromises()
    expect((puts[0].slots as { goal_needs: boolean }[])[0].goal_needs).toBe(false)
    expect(w.find('[data-save-bar]').exists()).toBe(true)
    expect(w.find('[data-save-bar] [role="alert"]').text()).toContain('disque plein')
  })

  it('Fonctions: the four features, each naming the page it changes', async () => {
    server({ slots: [KH2_A] })
    const w = mount(ConfigView)
    await flushPromises()
    await openTab(w, 'fonctions')
    const panel = w.find('[role="tabpanel"][data-state="active"]')
    expect(panel.findAll('[role="checkbox"]')).toHaveLength(4)
    for (const page of ['Historique', 'Indices', 'Objectifs', 'Plus › Room complète']) expect(panel.text()).toContain(page)
  })

  it('opens the tab named in the address, with a dot on App when an update is ready', async () => {
    history.replaceState(null, '', '/#config/app')
    server({ slots: [KH2_A] }, { update: { available: true } })
    const w = mount(ConfigView)
    await flushPromises()
    expect(selected(w)).toBe('app')
    expect(w.find('[data-config-tab="app"] [data-tab-dot]').exists()).toBe(true)
    expect(w.find('[data-config-tab="room"] [data-tab-dot]').exists()).toBe(false)
  })

  it('a room link opened while the page is shown switches to Room', async () => {
    server({ slots: [KH2_A] })
    const w = mount(ConfigView)
    await flushPromises()
    tracker.prefillRoom = 'https://archipelago.gg/room/y'
    await flushPromises()
    expect(selected(w)).toBe('room')
  })
})
