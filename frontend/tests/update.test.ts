import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import UpdateBanner from '../src/components/UpdateBanner.vue'
import UpdatePanel from '../src/components/UpdatePanel.vue'
import { latestLabel, phaseOf, type UpdateInfo } from '../src/lib/update'
import { tracker } from '../src/stores/tracker'

const base = (over: Partial<UpdateInfo> = {}): UpdateInfo => ({
  mode: 'portable',
  current: { version: 'v0.1.0' },
  latest: { version: 'v0.2.0', url: 'https://github.com/x/releases/tag/v0.2.0', notes: 'Nouveautés' },
  available: true,
  blocked: null,
  checked_at: 1000,
  check_error: null,
  running: false,
  status: null,
  ...over,
})

function stubFetch(handler: (url: string, init?: RequestInit) => unknown) {
  const fn = vi.fn(async (url: string, init?: RequestInit) => {
    const body = handler(url, init)
    if (body instanceof Error) throw body
    return new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } })
  })
  vi.stubGlobal('fetch', fn)
  return fn
}

afterEach(() => {
  vi.unstubAllGlobals()
  vi.useRealTimers()
  localStorage.clear()
})

describe('update helpers', () => {
  it('labels the new version', () => {
    expect(latestLabel(base())).toBe('version v0.2.0')
    expect(latestLabel(base({ mode: 'git', latest: { version: 'abc', behind: 1, commits: [] } }))).toBe('1 nouveau commit sur main')
    expect(latestLabel(base({ mode: 'git', latest: { version: 'abc', behind: 3, commits: [] } }))).toBe('3 nouveaux commits sur main')
  })

  it('follows an update from the status written by the server', () => {
    const t = 2000
    expect(phaseOf(null, t)).toEqual({ kind: 'waiting', text: 'Redémarrage de l’app…' })
    // status of a previous update: ignored
    expect(phaseOf(base({ status: { state: 'done', at: 100 } }), t).kind).toBe('waiting')
    const running = base({ status: { state: 'running', step: 'Téléchargement', at: t, progress: { done: 25, total: 100 } } })
    expect(phaseOf(running, t)).toEqual({ kind: 'waiting', text: 'Téléchargement… 25 %' })
    expect(phaseOf(base({ status: { state: 'done', at: t + 9 } }), t)).toEqual({ kind: 'done' })
    expect(phaseOf(base({ status: { state: 'error', step: 'x', message: 'empreinte', at: t } }), t)).toEqual({ kind: 'error', text: 'empreinte' })
  })
})

describe('UpdatePanel', () => {
  let reload: ReturnType<typeof vi.fn>
  beforeEach(() => {
    reload = vi.fn()
    vi.stubGlobal('location', { ...window.location, reload })
  })

  it('shows the installed version and the release, checks on demand', async () => {
    const fetch = stubFetch((url) => (url === '/api/update' ? base({ available: false, latest: null, checked_at: null }) : base()))
    const w = mount(UpdatePanel)
    await flushPromises()
    expect(w.find('[data-current]').text()).toBe('v0.1.0')
    expect(w.find('[data-apply]').attributes('disabled')).toBeDefined()
    await w.findAll('button').find((b) => b.text().includes('Vérifier maintenant'))!.trigger('click')
    await flushPromises()
    expect(fetch).toHaveBeenCalledWith('/api/update/check', expect.objectContaining({ method: 'POST' }))
    expect(w.find('[data-available]').text()).toContain('version v0.2.0')
    expect(w.find('[data-available]').text()).toContain('Nouveautés')
    expect(w.find('[data-apply]').attributes('disabled')).toBeUndefined()
  })

  it('lists the commits on the Pi and says why it cannot update', async () => {
    const commits = [{ commit: 'abc1234', date: 1, subject: 'Fix the thing' }]
    stubFetch(() => base({ mode: 'git', current: { version: 'v0.1.0-3-gdef', commit: 'def', date: 1 }, latest: { version: 'abc1234', behind: 1, commits } }))
    const w = mount(UpdatePanel)
    await flushPromises()
    expect(w.find('[data-available]').text()).toContain('abc1234 Fix the thing')
    stubFetch(() => base({ mode: 'git', available: false, blocked: '1 commit(s) local(aux) pas encore poussé(s)', latest: { version: 'a', behind: 1 } }))
    const w2 = mount(UpdatePanel)
    await flushPromises()
    expect(w2.text()).toContain('pas encore poussé')
  })

  it('applies, follows the restart and reloads the page', async () => {
    vi.useFakeTimers({ toFake: ['setTimeout', 'Date'] })
    vi.setSystemTime(new Date(5_000_000))
    const now = 5000
    let calls = 0
    stubFetch((url, init) => {
      if (url === '/api/update/apply') return base({ running: true, status: { state: 'running', step: 'Téléchargement', at: now } })
      if (init?.method) return base()
      calls++
      if (calls === 1) return base()
      if (calls === 2) return base({ running: true, status: { state: 'running', step: 'Téléchargement', at: now, progress: { done: 1, total: 2 } } })
      if (calls === 3) return new TypeError('Failed to fetch') // the app restarts
      return base({ current: { version: 'v0.2.0' }, available: false, status: { state: 'done', at: now + 30, from: 'v0.1.0', to: 'v0.2.0' } })
    })
    const w = mount(UpdatePanel)
    await flushPromises()
    await w.find('[data-apply]').trigger('click')
    await flushPromises()
    expect(w.find('[data-phase]').text()).toBe('Démarrage…')
    await vi.advanceTimersByTimeAsync(1500)
    expect(w.find('[data-phase]').text()).toBe('Téléchargement… 50 %')
    await vi.advanceTimersByTimeAsync(1500)
    expect(w.find('[data-phase]').text()).toBe('Redémarrage de l’app…')
    expect(reload).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(1500)
    expect(reload).toHaveBeenCalled()
  })

  it('shows a failed update and keeps the buttons', async () => {
    vi.useFakeTimers({ toFake: ['setTimeout', 'Date'] })
    vi.setSystemTime(new Date(5_000_000))
    let n = 0
    stubFetch((url) => {
      if (url === '/api/update/apply') return base({ running: true })
      return n++ === 0 ? base() : base({ status: { state: 'error', step: 'Téléchargement', message: 'empreinte', at: 5000 } })
    })
    const w = mount(UpdatePanel)
    await flushPromises()
    await w.find('[data-apply]').trigger('click')
    await flushPromises()
    await vi.advanceTimersByTimeAsync(1500)
    expect(w.text()).toContain('Mise à jour échouée : empreinte')
    expect(w.find('[data-apply]').exists()).toBe(true)
    expect(reload).not.toHaveBeenCalled()
  })
})

describe('UpdateBanner', () => {
  beforeEach(() => {
    tracker.view = 'dashboard'
  })

  it('appears when a version is available, until dismissed for that version', async () => {
    stubFetch(() => base())
    const w = mount(UpdateBanner)
    await flushPromises()
    expect(w.find('[data-update-banner]').text()).toContain('version v0.2.0')
    await w.find('button[aria-label]').trigger('click')
    expect(w.find('[data-update-banner]').exists()).toBe(false)
    expect(localStorage.getItem('amt-update-dismissed')).toBe('v0.2.0')
    const again = mount(UpdateBanner)
    await flushPromises()
    expect(again.find('[data-update-banner]').exists()).toBe(false)
    stubFetch(() => base({ latest: { version: 'v0.3.0' } }))
    const next = mount(UpdateBanner)
    await flushPromises()
    expect(next.find('[data-update-banner]').exists()).toBe(true)
  })

  it('stays hidden when up to date, on the Configuration page, or without server', async () => {
    stubFetch(() => base({ available: false }))
    let w = mount(UpdateBanner)
    await flushPromises()
    expect(w.find('[data-update-banner]').exists()).toBe(false)
    tracker.view = 'config'
    stubFetch(() => base())
    w = mount(UpdateBanner)
    await flushPromises()
    expect(w.find('[data-update-banner]').exists()).toBe(false)
    tracker.view = 'dashboard'
    stubFetch(() => new TypeError('Failed to fetch'))
    w = mount(UpdateBanner)
    await flushPromises()
    expect(w.find('[data-update-banner]').exists()).toBe(false)
  })
})
