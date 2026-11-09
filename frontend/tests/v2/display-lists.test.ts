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
