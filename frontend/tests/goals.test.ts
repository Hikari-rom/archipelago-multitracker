import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import GoalsView from '../src/components/GoalsView.vue'
import SlotCard from '../src/components/SlotCard.vue'
import { goalProgress, mainCounter, sortByGoal } from '../src/lib/goals'
import type { Objective } from '../src/lib/types'
import { mk } from './helpers'

const kh2: Objective = {
  summary: '40 Lucky Emblems, puis Final Xemnas',
  source: 'slot_data',
  counters: [{ label: 'Lucky Emblems', current: 20, target: 40 }],
  steps: [{ label: 'Vaincre Final Xemnas', done: false }],
}
const odyssey: Objective = {
  summary: 'Vaincre Bowser',
  source: 'slot_data',
  counters: [
    { label: 'Cascade → Sand', current: 5, target: 5 },
    { label: 'Sand → Lake', current: 4, target: 16, detail: 'Power Moons' },
  ],
  steps: [{ label: 'Bowser (event)', done: null }, { label: 'Arrive in the Mushroom Kingdom', done: false }],
}

describe('goals', () => {
  it('main counter: the first one not reached', () => {
    expect(mainCounter(odyssey)?.label).toBe('Sand → Lake')
    expect(mainCounter(null)).toBeNull()
  })

  it('progress counts counters and known steps, not the goal step', () => {
    expect(goalProgress({ goal: false, objective: kh2 })).toBe(0.5)
    expect(goalProgress({ goal: false, objective: odyssey })).toBeCloseTo((1 + 4 / 16) / 2)
    expect(goalProgress({ goal: true, objective: kh2 })).toBe(1)
    expect(goalProgress({ goal: false, objective: null })).toBe(0)
  })

  it('sort: unfinished by progress, then finished, then games without description', () => {
    const slots = [
      mk({ name: 'none' }),
      mk({ name: 'done', goal: true, objective: kh2 }),
      mk({ name: 'half', objective: kh2 }),
      mk({ name: 'ody', objective: odyssey }),
    ]
    expect(sortByGoal(slots).map((s) => s.name)).toEqual(['ody', 'half', 'done', 'none'])
  })

  it('page and card show the goal', () => {
    const w = mount(GoalsView, { props: { slots: [mk({ name: 'a', objective: odyssey }), mk({ name: 'b', goal: true, objective: kh2 })] } })
    expect(w.text()).toContain('1 / 2 buts atteints')
    expect(w.text()).toContain('But : Vaincre Bowser')
    expect(w.text()).toContain('4 / 16')
    expect(w.text()).toContain('But atteint')
    expect(w.findAll('[aria-label="pas visible par un tracker"]').length).toBeGreaterThan(0)
    const card = mount(SlotCard, { props: { summary: mk({ name: 'k', objective: kh2 }) } })
    expect(card.find('.goal-line').text().replace(/\s+/g, ' ')).toContain('But : 40 Lucky Emblems, puis Final Xemnas · Lucky Emblems 20 / 40')
  })
})
