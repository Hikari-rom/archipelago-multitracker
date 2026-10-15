import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import AppV2 from '../../src/v2/AppV2.vue'
import LogsView from '../../src/components/LogsView.vue'
import { installMock } from '../../src/lib/api'
import { setView, tracker } from '../../src/stores/tracker'
import { mk } from '../helpers'

afterEach(() => {
  tracker.slots = []
  tracker.loaded = false
  tracker.roomSleeping = false
  tracker.roomError = ''
  setView('dashboard')
  document.documentElement.removeAttribute('data-v2')
})

describe('AppV2 shell', () => {
  it('tabs, logo home, live state, theme and more menus', async () => {
    tracker.loaded = true
    tracker.sse = 'open'
    tracker.slots = [mk({ name: 'a', logic: { state: 'ok', count: 58, message: null } })]
    installMock({
      getSlot: async () => { throw new Error('no') },
      markSeen: async () => ({ seen: 0 }),
      history: async () => ({ kind: 'sent', total: 0, offset: 0, scout_checked: true, slots: [], items: [] }),
    })
    const w = mount(AppV2, { attachTo: document.body })
    const tabs = w.findAll('nav[aria-label="Navigation"] a, nav[aria-label="Navigation"] button').map((t) => t.text())
    expect(tabs).toEqual(expect.arrayContaining(['Tableau', 'Historique', 'Objectifs']))
    expect(w.text()).toContain('En direct')
    expect(w.find('button[aria-label^="Thème"]').exists()).toBe(true)
    expect(w.find('button[aria-label="Plus"]').exists()).toBe(true)
    await w.find('button[aria-label="Historique"]').trigger('click')
    await flushPromises()
    expect(tracker.view).toBe('history')
    await w.find('a[aria-label="Retour au tableau de bord"]').trigger('click')
    expect(tracker.view).toBe('dashboard')
    expect(document.documentElement.dataset.v2).toBe('nuit')
    w.unmount()
  })
  it('sleeping room banner with wake button', async () => {
    tracker.loaded = true
    tracker.slots = [mk({ name: 'a', status: 'disconnected', updated_at: new Date(2026, 9, 15, 2, 14).getTime() / 1000 })]
    tracker.roomSleeping = true
    tracker.roomError = 'room endormie'
    const w = mount(AppV2)
    await flushPromises()
    expect(w.text()).toContain('La room est endormie')
    expect(w.text()).toContain('02:14')
    expect(w.findAll('button').some((b) => b.text() === 'Réveiller maintenant')).toBe(true)
  })
  it('logs and config views reuse the v1 pages', async () => {
    tracker.loaded = true
    tracker.slots = [mk({ name: 'a' })]
    setView('logs')
    const w = mount(AppV2)
    expect(w.findComponent(LogsView).exists()).toBe(true)
  })
})
