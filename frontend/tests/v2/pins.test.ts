import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { installMock } from '../../src/lib/api'
import type { HintRow, Pin } from '../../src/lib/types'
import { isPinned, togglePin, tracker } from '../../src/stores/tracker'
import HintsTable from '../../src/v2/components/HintsTable.vue'
import ThemeMenu from '../../src/v2/components/ThemeMenu.vue'

const pin = (slot: string, location: number, name: string): Pin => ({ slot, game: 'G', location, name, at: 1 })

function server(initial: Pin[] = []) {
  let pins = [...initial]
  const putPin = vi.fn(async (slot: string, location: number, pinned: boolean) => {
    pins = pinned ? [...pins, pin(slot, location, `#${location}`)] : pins.filter((p) => !(p.slot === slot && p.location === location))
    return { pins }
  })
  installMock({ getSlot: async () => { throw new Error('no') }, markSeen: async () => ({ seen: 0 }), getPins: async () => ({ pins }), putPin })
  return putPin
}

afterEach(() => {
  tracker.pins = []
  tracker.pinError = ''
  document.body.innerHTML = ''
})

describe('pinned checks', () => {
  it('toggle: shown at once, then the server list; put back on error', async () => {
    const putPin = server()
    const p = togglePin('Me_A', 100, 'Chest')
    expect(isPinned('Me_A', 100)).toBe(true)
    await p
    expect(putPin).toHaveBeenCalledWith('Me_A', 100, true)
    expect(tracker.pins.map((x) => x.name)).toEqual(['#100'])
    installMock({ getSlot: async () => { throw new Error('no') }, markSeen: async () => ({ seen: 0 }), putPin: async () => { throw new Error('hors ligne') } })
    await togglePin('Me_A', 100, 'Chest')
    expect(isPinned('Me_A', 100)).toBe(true)
    expect(tracker.pinError).toContain('hors ligne')
  })

  it('Indices table: pinned rows stay on top whatever the sort', () => {
    const row = (item: string, location_id: number): HintRow => ({
      item, location: `L${location_id}`, location_id, finder: 'F', finder_slot: 'F', finder_game: 'G', receiver: 'Me_A', receiver_slot: 'Me_A',
      receiver_game: 'A', found: false, progression: false, useful: false, trap: false, finder_tracked: false, receiver_tracked: true,
      slots: ['Me_A'], access: { state: 'ok' },
    })
    tracker.pins = [pin('F', 3, 'L3')]
    const w = mount(HintsTable, {
      props: { rows: [row('A', 1), row('B', 2), row('C', 3)], columns: ['item'], label: 'x', sort: { key: 'item', dir: 1 } },
    })
    expect(w.findAll('[data-hint]').map((r) => r.attributes('data-hint'))).toEqual(['C', 'A', 'B'])
    expect(w.find('[data-hint="C"]').attributes('data-pinned')).toBe('true')
  })
})

describe('theme menu', () => {
  async function open(resolved: 'nuit' | 'plan') {
    const w = mount(ThemeMenu, { props: { choice: resolved, resolved, sky: true }, attachTo: document.body })
    const trigger = w.find('button[aria-label^="Thème"]')
    await trigger.trigger('pointerdown', { button: 0, ctrlKey: false, pointerType: 'mouse' })
    await trigger.trigger('keydown', { key: 'Enter' })
    await flushPromises()
    return w
  }
  it('the animated sky option only in Nuit', async () => {
    const nuit = await open('nuit')
    expect(document.body.textContent).toContain('Plan')
    expect(document.body.textContent).toContain('Ciel animé')
    nuit.unmount()
    document.body.innerHTML = ''
    const plan = await open('plan')
    expect(document.body.textContent).toContain('grille de dessin') // the menu is open
    expect(document.body.textContent).not.toContain('Ciel animé')
    plan.unmount()
  })
})
