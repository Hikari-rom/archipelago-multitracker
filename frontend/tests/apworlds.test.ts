import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import UserApworldsPanel from '../src/components/UserApworldsPanel.vue'
import { importSummary, type ApworldsInfo } from '../src/lib/apworlds'
import { diagnose } from '../src/lib/config'

const SRC = 'C:\\ProgramData\\Archipelago\\custom_worlds'
const base = (over: Partial<ApworldsInfo> = {}): ApworldsInfo => ({ dir: 'data/apworlds', default_source: SRC, files: [], ...over })

function stubFetch(handler: (url: string, init?: RequestInit) => unknown) {
  const fn = vi.fn(async (url: string, init?: RequestInit) => {
    const body = handler(url, init)
    const status = body instanceof Error ? 400 : 200
    return new Response(JSON.stringify(body instanceof Error ? { detail: body.message } : body), {
      status, headers: { 'Content-Type': 'application/json' },
    })
  })
  vi.stubGlobal('fetch', fn)
  return fn
}

afterEach(() => vi.unstubAllGlobals())

describe('apworld helpers', () => {
  it('summarizes an import', () => {
    expect(importSummary([])).toBe('aucun fichier .apworld dans ce dossier')
    expect(importSummary([
      { file: 'a.apworld', game: 'A', status: 'imported' },
      { file: 'b.apworld', game: 'B', status: 'shipped' },
      { file: 'c.apworld', game: 'C', status: 'shipped' },
      { file: 'd.apworld', game: null, status: 'unreadable' },
    ])).toBe('1 importé, 2 déjà fournis par l’app, 1 illisible')
  })

  it('says when a game’s apworld still has to be imported', () => {
    const row = { name: 'P1', game: 'Cookie Clicker', yaml: null, checked: true } as any
    const texts = (games: any) => diagnose(row, [], games).map((d) => d.text)
    expect(texts({ 'Cookie Clicker': { logic: true, needs_yaml: false, user: true, imported: false } })[0]).toContain('apworld à importer')
    expect(texts({ 'Cookie Clicker': { logic: true, needs_yaml: false, user: true, imported: true } })).toEqual([])
  })
})

describe('UserApworldsPanel', () => {
  it('prefills the usual folder, imports and reports', async () => {
    const fetch = stubFetch((url) => url === '/api/apworlds' ? base() : base({
      files: [{ file: 'cookieclicker.apworld', game: 'Cookie Clicker', in_room: true }],
      report: [
        { file: 'cookieclicker.apworld', game: 'Cookie Clicker', status: 'imported' },
        { file: 'sm64ex.apworld', game: 'Super Mario 64', status: 'shipped' },
      ],
    }))
    const w = mount(UserApworldsPanel)
    await flushPromises()
    expect((w.find('[data-source]').element as HTMLInputElement).value).toBe(SRC)
    expect(w.find('[data-empty]').exists()).toBe(true)
    await w.find('form').trigger('submit')
    await flushPromises()
    expect(fetch).toHaveBeenCalledWith('/api/apworlds/import', expect.objectContaining({ method: 'POST', body: JSON.stringify({ path: SRC }) }))
    expect(w.find('[data-report]').text()).toContain('1 importé, 1 déjà fourni par l’app')
    expect(w.find('[data-skipped]').text()).toContain('sm64ex.apworld')
    expect(w.find('[data-files]').text()).toContain('Cookie Clicker')
    expect(w.emitted('imported')).toHaveLength(1)
  })

  it('checks the versions against the room', async () => {
    const files = [{ file: 'a.apworld', game: 'A', in_room: true }, { file: 'b.apworld', game: 'B', in_room: true }]
    stubFetch((url) => url === '/api/apworlds' ? base({ files }) : base({
      files: [{ ...files[0], version: 'room' }, { ...files[1], version: 'other' }],
    }))
    const w = mount(UserApworldsPanel)
    await flushPromises()
    await w.find('[data-check]').trigger('click')
    await flushPromises()
    const versions = w.findAll('[data-version]').map((e) => e.text())
    expect(versions).toEqual(['version de la room', 'pas la version de la room : logique refusée'])
  })

  it('shows the server error and asks for a path without a usual install', async () => {
    stubFetch((url) => url === '/api/apworlds' ? base({ default_source: null }) : new Error('dossier introuvable : X'))
    const w = mount(UserApworldsPanel)
    await flushPromises()
    expect(w.find('[data-no-default]').exists()).toBe(true)
    expect(w.find('[data-import]').attributes('disabled')).toBeDefined()
    await w.find('[data-source]').setValue('/home/x/custom_worlds')
    await w.find('form').trigger('submit')
    await flushPromises()
    expect(w.find('[role=alert]').text()).toBe('dossier introuvable : X')
    expect(w.emitted('imported')).toBeUndefined()
  })
})
