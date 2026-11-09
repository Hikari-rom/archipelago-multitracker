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
