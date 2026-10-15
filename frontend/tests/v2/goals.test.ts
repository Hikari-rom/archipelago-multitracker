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
