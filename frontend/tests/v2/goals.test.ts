import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { tracker } from '../../src/stores/tracker'
import GoalChooser from '../../src/v2/components/GoalChooser.vue'
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

describe('GoalChooser (D34)', () => {
  const KH2 = [{ option: 'Goal', display: 'Goal', choices: ['three_proofs', 'hitlist'] }]

  afterEach(() => {
    vi.unstubAllGlobals()
    tracker.slots = []
  })

  it('appears only when the server sends the options (« Choisir le but à la main » on) and saves the choice', async () => {
    const off = mk({ name: 'kh2', game: 'Kingdom Hearts 2', goal_choosable: true })
    tracker.slots = [off]
    const w = mount(GoalsV2, { props: { slots: [off], owner: '*', chips: [] } })
    expect(w.find('[data-goal-chooser]').exists()).toBe(false)
    expect(w.text()).toContain('Choisir le but à la main')

    const calls: { url: string; body: unknown }[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, init?: RequestInit) => {
        calls.push({ url, body: JSON.parse(String(init?.body)) })
        return new Response(JSON.stringify({ ok: true, goal: { Goal: 'hitlist' } }), { status: 200 })
      }),
    )
    const on = mk({ name: 'kh2', game: 'Kingdom Hearts 2', goal_choosable: true, goal_options: KH2, goal_chosen: {} })
    tracker.slots = [on]
    await w.setProps({ slots: [on] })
    const select = w.find('[data-goal-chooser] select')
    expect((select.element as HTMLSelectElement).value).toBe('')
    expect(w.text()).not.toContain('Choisir le but à la main')
    await select.setValue('hitlist')
    await flushPromises()
    expect(calls).toEqual([{ url: '/api/slots/kh2/goal', body: { goal: { Goal: 'hitlist' } } }])
    expect((select.element as HTMLSelectElement).value).toBe('hitlist') // until the snapshot brings it
    tracker.slots = [{ ...on, goal_chosen: { Goal: 'hitlist' } }]
    await flushPromises()
    expect((w.find('[data-goal-chooser] select').element as HTMLSelectElement).value).toBe('hitlist')
  })

  it('says why the choice was refused', async () => {
    const on = mk({ name: 'kh2', game: 'Kingdom Hearts 2', goal_options: KH2, goal_chosen: { Goal: 'three_proofs' } })
    tracker.slots = [on]
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ detail: '« Choisir le but à la main » est désactivé dans la Configuration' }), { status: 409 })))
    const w = mount(GoalChooser, { props: { name: 'kh2' } })
    await w.find('select').setValue('hitlist')
    await flushPromises()
    expect(w.find('[role="alert"]').text()).toContain('désactivé')
    expect((w.find('select').element as HTMLSelectElement).value).toBe('three_proofs')
  })
})
