import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import NewsTicker from '../../src/v2/components/NewsTicker.vue'
import RecentStrip from '../../src/v2/components/RecentStrip.vue'
import { historyTab } from '../../src/v2/lib/nav'
import { tracker } from '../../src/stores/tracker'
import type { RecentItem } from '../../src/lib/types'
import { mk } from '../helpers'

const NOW = 1_800_000_000_000
const item = (index: number, over: Partial<RecentItem> = {}): RecentItem => ({
  index, name: `Item ${index}`, sender: 'kuro', own: false, location: 'Somewhere', progression: false, useful: false,
  trap: false, new: false, slot: 'romain_celeste', game: 'Celeste (Open World)', received_at: NOW / 1000 - index * 60, ...over,
})

afterEach(() => {
  tracker.ticker = 'off'
  tracker.recent = []
  tracker.view = 'dashboard'
})

describe('news ticker', () => {
  it('the static strip stays the default', () => {
    tracker.nowMs = NOW
    tracker.recent = [item(1)]
    const w = mount(RecentStrip, { props: { slots: [mk({ name: 'romain_celeste' })] } })
    expect(w.find('[data-ticker]').exists()).toBe(false)
    expect(w.text()).toContain('Item 1')
  })

  it('replaces the strip with the chosen look, filtered on the selected slots', () => {
    tracker.nowMs = NOW
    tracker.ticker = 'agence'
    tracker.recent = [item(1), item(2, { slot: 'other' }), item(3)]
    const w = mount(RecentStrip, { props: { slots: [mk({ name: 'romain_celeste' })] } })
    const t = w.find('[data-ticker]')
    expect(t.attributes('data-variant')).toBe('agence')
    expect(t.text()).toContain('Item 1')
    expect(t.text()).toContain('Item 3')
    expect(t.text()).not.toContain('Item 2')
  })

  it('board look: time, category and sender; counts the new items', () => {
    tracker.nowMs = NOW
    const w = mount(NewsTicker, {
      props: { variant: 'arrivees', items: [item(1, { progression: true, new: true }), item(2, { trap: true, own: true }), item(3, { received_at: null as unknown as number })] },
    })
    const t = w.text()
    expect(t).toContain('★ 1 nouveau')
    expect(t).toContain('PROG')
    expect(t).toContain('PIÈGE')
    expect(t).toContain('ITEM')
    expect(t).toContain('de kuro')
    expect(t).toContain('toi')
    expect(t).toContain('—')
    expect(t).not.toMatch(/undefined|null|NaN/)
  })

  it('ribbon look: progression items are highlighted; a click opens the received history', async () => {
    tracker.nowMs = NOW
    const w = mount(NewsTicker, { props: { variant: 'ruban', items: [item(1, { progression: true }), item(2)] } })
    const pills = w.findAll('button').filter((b) => b.text().includes('Item'))
    expect(pills[0].classes()).toContain('border-gold-line')
    expect(pills[1].classes()).not.toContain('border-gold-line')
    await pills[1].trigger('click')
    expect(tracker.view).toBe('history')
    expect(historyTab.value).toBe('received')
  })
})
