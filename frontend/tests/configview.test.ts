import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import ConfigView from '../src/components/ConfigView.vue'

const KH2 = [{ option: 'Goal', display: 'Goal', choices: ['three_proofs', 'hitlist'] }]

afterEach(() => {
  vi.unstubAllGlobals()
})

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
})
