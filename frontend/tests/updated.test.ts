import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import UpdatedNotice from '../src/components/UpdatedNotice.vue'
import { noteLines, runningId, type UpdateInfo } from '../src/lib/update'

const info = (over: Partial<UpdateInfo> = {}): UpdateInfo => ({
  mode: 'portable',
  current: { version: 'v0.2.17' },
  latest: { version: 'v0.2.17', url: 'https://github.com/x/releases/tag/v0.2.17', notes: '## Nouveautés\n- Page **Indices**\n- `hints`' },
  available: false,
  blocked: null,
  checked_at: 1000,
  check_error: null,
  running: false,
  status: null,
  ...over,
})

function stub(body: UpdateInfo) {
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } })))
}

afterEach(() => {
  vi.unstubAllGlobals()
  localStorage.clear()
})

describe('post-update notice', () => {
  it('ids and notes', () => {
    expect(runningId(info())).toBe('v0.2.17')
    expect(runningId(info({ mode: 'git', current: { version: 'v0.2.16-1-gabc', commit: 'abc', running: 'def' } }))).toBe('def')
    expect(noteLines('## Nouveautés\n\n- Page **Indices**\n- `hints`')).toEqual([
      { text: 'Nouveautés', heading: true },
      { text: '• Page Indices', heading: false },
      { text: '• hints', heading: false },
    ])
  })

  it('first visit: silent, remembers the version', async () => {
    stub(info())
    const w = mount(UpdatedNotice)
    await flushPromises()
    expect(w.find('[data-updated-notice]').exists()).toBe(false)
    expect(localStorage.getItem('amt-seen-version')).toBe('v0.2.17')
  })

  it('after an update: says it once, with the notes', async () => {
    localStorage.setItem('amt-seen-version', 'v0.2.16')
    stub(info())
    const w = mount(UpdatedNotice)
    await flushPromises()
    const n = w.find('[data-updated-notice]')
    expect(n.text()).toContain('Mise à jour installée : v0.2.17')
    expect(n.text()).toContain('• Page Indices')
    expect(n.find('a').attributes('href')).toContain('v0.2.17')
    await w.find('button[aria-label="Fermer"]').trigger('click')
    expect(w.find('[data-updated-notice]').exists()).toBe(false)
    expect(localStorage.getItem('amt-seen-version')).toBe('v0.2.17')
  })
})
