import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import DisplayInfos from '../../src/v2/components/DisplayInfos.vue'
import { setDisplay, tracker } from '../../src/stores/tracker'
import { applyPreset, INFO_KEYS } from '../../src/v2/lib/display'

afterEach(() => {
  setDisplay(applyPreset('complet'))
  localStorage.clear()
})

const checked = (w: ReturnType<typeof mount>) =>
  w.findAll('[data-info]').filter((c) => (c.element as HTMLInputElement).checked).map((c) => c.attributes('data-info'))
const pressed = (w: ReturnType<typeof mount>) =>
  w.findAll('[data-density]').filter((b) => b.attributes('aria-pressed') === 'true').map((b) => b.attributes('data-density'))

describe('Configuration › Infos du tableau de bord', () => {
  it('Complet by default: every box checked', () => {
    const w = mount(DisplayInfos)
    expect(checked(w)).toEqual([...INFO_KEYS])
    expect(pressed(w)).toEqual(['complet'])
    expect(w.find('[data-custom]').exists()).toBe(false)
    expect(w.text()).toContain('restent toujours affichés')
  })
  it('a preset checks its boxes and is saved', async () => {
    const w = mount(DisplayInfos)
    await w.find('[data-density="essentiel"]').trigger('click')
    expect(checked(w)).toEqual(['newItems', 'hints', 'goal'])
    expect(pressed(w)).toEqual(['essentiel'])
    expect(JSON.parse(localStorage.getItem('amt-v2-display')!).preset).toBe('essentiel')
  })
  it('a box out of the preset shows « Personnalisé », back in names the preset again', async () => {
    const w = mount(DisplayInfos)
    await w.find('[data-density="essentiel"]').trigger('click')
    await w.find('[data-info="hints"]').setValue(false)
    expect(w.find('[data-custom]').text()).toContain('Personnalisé')
    expect(pressed(w)).toEqual([])
    expect(tracker.display.shown).toEqual(['newItems', 'goal'])
    await w.find('[data-info="hints"]').setValue(true)
    expect(pressed(w)).toEqual(['essentiel'])
    expect(w.find('[data-custom]').exists()).toBe(false)
  })
})
