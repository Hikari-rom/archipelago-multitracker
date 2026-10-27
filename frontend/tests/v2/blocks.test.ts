import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import BigNumber from '../../src/v2/components/BigNumber.vue'
import DetailTabs from '../../src/v2/components/DetailTabs.vue'
import GameTile from '../../src/v2/components/GameTile.vue'
import StateChips from '../../src/v2/components/StateChips.vue'
import UndoToast from '../../src/v2/components/UndoToast.vue'
import { cardState, type CardCtx } from '../../src/v2/lib/card'
import { undo } from '../../src/v2/lib/undo'
import { tracker } from '../../src/stores/tracker'
import type { SlotDetail } from '../../src/lib/types'
import { mk } from '../helpers'

const NOW = 1_800_000_000_000
const ctx: CardCtx = { nowMs: NOW, activeMinutes: 30, activity: { pinned: null, dismissed: {} }, roomSleeping: false }

afterEach(() => {
  tracker.details = {}
  undo.message = ''
  undo.prev = null
})

describe('card blocks', () => {
  it('big number never shows NaN/undefined', () => {
    for (const logic of [
      { state: 'ok', count: 0, message: null },
      { state: 'ok', count: 21, message: 'yaml' },
      { state: 'pending', count: 0, message: null },
      { state: 'unavailable', count: 0, message: null },
      { state: 'error', count: 0, message: null },
    ] as const) {
      const t = mount(BigNumber, { props: { state: cardState(mk({ name: 'a', logic: { ...logic } }), ctx) } }).text()
      expect(t).not.toMatch(/NaN|undefined/)
    }
    // render `<span aria-label="approximatif">≈</span>{{ big }}` with no whitespace between them
    expect(mount(BigNumber, { props: { state: cardState(mk({ name: 'a', logic: { state: 'ok', count: 21, message: 'x' } }), ctx) } }).text()).toBe('≈21')
  })
  it('knowingly late logic: an hourglass whose tooltip says why, a plain title inside a button', async () => {
    const why = 'Logique minorée : le serveur ne transmet ni l’arbre des technologies'
    const s = mk({ name: 'f', game: 'Factorio', logic: { state: 'ok', count: 12, message: null, note: why } })
    const big = mount(BigNumber, { props: { state: cardState(s, ctx) }, attachTo: document.body })
    expect(big.text()).toBe('12')
    const icon = big.get('button[data-logic-note]')
    expect(icon.attributes('aria-label')).toBe('Logique minorée')
    await icon.trigger('click')
    await flushPromises()
    expect(document.body.textContent).toContain(why)
    big.unmount()
    const inButton = mount(BigNumber, { props: { state: cardState(s, ctx), inButton: true } })
    expect(inButton.find('button').exists()).toBe(false)
    expect(inButton.get('[data-logic-note]').attributes('title')).toBe(why)
    const exact = mk({ name: 'g', logic: { state: 'ok', count: 12, message: null } })
    expect(mount(BigNumber, { props: { state: cardState(exact, ctx) } }).find('[data-logic-note]').exists()).toBe(false)
  })
  it('chips: auto active and error', () => {
    const s = mk({ name: 'a', last_check_at: NOW / 1000 - 12 * 60, status: 'error', error: 'connexion refusée : mot de passe' })
    const t = mount(StateChips, { props: { state: cardState(s, ctx) } }).text()
    expect(t).toContain('◔ Actif · auto · il y a 12 min')
    expect(t).toContain('connexion refusée : mot de passe')
    expect(t).toContain('Réessayer')
  })
  it('logic unavailable: the tile and the chips say why', () => {
    const why = 'apworld non installé pour « Blue Prince » : importe-le depuis ton Archipelago'
    const s = mk({ name: 'ash_blue', game: 'Blue Prince', logic: { state: 'unavailable', count: 0, message: why } })
    expect(mount(StateChips, { props: { state: cardState(s, ctx) } }).get('[data-unavailable]').text()).toBe(`Logique indisponible pour ce jeu : ${why}`)
    expect(mount(GameTile, { props: { summary: s } }).get('[data-unavailable]').text()).toBe(`Logique indisponible : ${why}`)
    const bare = mk({ name: 'b', logic: { state: 'unavailable', count: 0, message: null } })
    expect(mount(GameTile, { props: { summary: bare } }).get('[data-unavailable]').text()).toBe('Logique indisponible')
  })
  it('chips: expiry for auto-active, memorised note for chosen', () => {
    const auto = mount(StateChips, { props: { state: cardState(mk({ name: 'a', last_check_at: NOW / 1000 - 12 * 60 }), ctx) } }).text()
    expect(auto).toContain('Expire dans 18 min')
    expect(auto).not.toContain('Mémorisé')
    const pinned = { ...ctx, activity: { pinned: { name: 'a', at: 1 }, dismissed: {} } }
    const chosen = mount(StateChips, { props: { state: cardState(mk({ name: 'a' }), pinned) } }).text()
    expect(chosen).toContain('Mémorisé sur cet appareil')
    expect(chosen).not.toContain('Expire dans')
  })
  it('detail tabs: origin of server, start, own and foreign items; no literal null', async () => {
    const base = { progression: false, useful: false, trap: false, new: false, received_at: null }
    tracker.details = {
      ww: {
        ...mk({ name: 'ww' }),
        items_list: [
          { ...base, index: 3, name: 'Srv', sender: 'Archipelago', own: false, location: null, origin: 'server' },
          { ...base, index: 2, name: 'Start', sender: 'ww', own: true, location: null, origin: 'start' },
          { ...base, index: 1, name: 'Mine', sender: 'ww', own: true, location: 'Loc A' },
          { ...base, index: 0, name: 'Other', sender: 'kuro', own: false, location: 'Loc B' },
        ],
        hints_mine_elsewhere: [], hints_in_my_world: [], in_logic_locations: [],
      } as unknown as SlotDetail,
    }
    const w = mount(DetailTabs, { props: { name: 'ww', initial: 'received' } })
    await flushPromises()
    const t = w.text()
    expect(t).toContain('donné par le serveur')
    expect(t).toContain('inventaire de départ')
    expect(t).toContain('trouvé par toi · Loc A')
    expect(t).toContain('de kuro · Loc B')
    expect(t).not.toContain('null')
    expect(w.find('[role="tabpanel"]').attributes('aria-labelledby')).toBe(w.find('[aria-selected="true"]').attributes('id'))
  })
  it('detail tabs: no "Marquer comme vu" when nothing is new', async () => {
    tracker.details = { ww: { ...mk({ name: 'ww' }), items_list: [], hints_mine_elsewhere: [], hints_in_my_world: [], in_logic_locations: [] } as unknown as SlotDetail }
    const w = mount(DetailTabs, { props: { name: 'ww', initial: 'new' } })
    await flushPromises()
    expect(w.text()).toContain('Aucun nouvel item')
    expect(w.text()).not.toContain('Marquer comme vu')
  })
  it('detail tabs: regions, hinted locations first, new items', async () => {
    const d = {
      ...mk({ name: 'ww', items: { received: 2, new: 1 } }),
      items_list: [
        { index: 1, name: 'Progressive Sword', sender: 'kuro', own: false, location: 'X', progression: true, useful: false, trap: false, new: true, received_at: null },
        { index: 0, name: 'Rupee', sender: 'kuro', own: false, location: 'Y', progression: false, useful: false, trap: false, new: false, received_at: null },
      ],
      hints_mine_elsewhere: [],
      hints_in_my_world: [],
      in_logic_locations: [
        { id: 1, name: 'Windfall Island - Cafe Bar - Postman', region: 'Windfall Island', hint: null },
        { id: 2, name: 'Windfall Island - Jail - Tingle - First Gift', region: 'Windfall Island', hint: { item: 'Golden Walnut', receiver: 'kuro_valley', progression: true } },
        { id: 3, name: 'Great Sea - Crab', region: 'Great Sea', hint: null },
      ],
    } as SlotDetail
    tracker.details = { ww: d }
    const w = mount(DetailTabs, { props: { name: 'ww' } })
    await flushPromises()
    expect(w.find('[role="tablist"]').exists()).toBe(true)
    const rows = w.findAll('[data-location]').map((r) => r.text())
    expect(rows[0]).toContain('Tingle')
    expect(rows[0]).toContain('hint · Golden Walnut pour kuro_valley')
    await w.find('[role="tab"][data-tab="new"]').trigger('click')
    expect(w.text()).toContain('Progressive Sword')
    expect(w.text()).not.toContain('Rupee')
    expect(w.text()).toContain('Marquer comme vu')
  })
  it('undo toast', async () => {
    undo.message = "Celeste n'est plus actif jusqu'à son prochain check."
    undo.prev = { pinned: null, dismissed: {} }
    const w = mount(UndoToast)
    expect(w.attributes('role')).toBe('status')
    expect(w.text()).toContain('Annuler')
  })
})
