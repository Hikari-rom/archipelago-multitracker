import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import SkyBackground from '../../src/v2/components/SkyBackground.vue'
import { skyLayers } from '../../src/v2/lib/sky'

describe('sky', () => {
  it('densities, durations and bounds from the mockup', () => {
    const [far, near] = skyLayers(false)
    expect([far.stars.length, near.stars.length, far.duration, near.duration]).toEqual([150, 34, 260, 150])
    const [pf, pn] = skyLayers(true)
    expect([pf.stars.length, pn.stars.length]).toEqual([55, 14])
    for (const s of far.stars) {
      expect(s.x).toBeGreaterThanOrEqual(0)
      expect(s.x).toBeLessThan(100)
      expect(s.y).toBeLessThan(50)
      expect(s.size).toBeGreaterThanOrEqual(0.8)
      expect(s.size).toBeLessThanOrEqual(1.3)
    }
  })
  it('is deterministic', () => expect(skyLayers(false)).toEqual(skyLayers(false)))
  it('renders each star twice (seamless loop) and stops when not animated', () => {
    const w = mount(SkyBackground, { props: { animated: false } })
    expect(w.attributes('aria-hidden')).toBe('true')
    const stars = w.findAll('[data-star]')
    expect(stars.length).toBe((150 + 34) * 2)
    expect(w.findAll('[data-sky]').every((l) => !(l.attributes('style') ?? '').includes('v2-drift'))).toBe(true)
    expect(mount(SkyBackground, { props: { animated: true } }).find('[data-sky]').attributes('style')).toContain('v2-drift')
  })
})
