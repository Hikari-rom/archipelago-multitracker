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
