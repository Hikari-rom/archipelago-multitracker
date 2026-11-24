import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { useConfigForm, type ConfigForm } from '../src/components/config/form'

afterEach(() => {
  vi.unstubAllGlobals()
})

function stubFetch(config: Record<string, unknown>, players: { name: string; game: string }[] = []) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      let body: unknown = {}
      if (url === '/api/config') {
        body = {
          room_url: null, server: '127.0.0.1:1', has_password: false, player_yamls: [], yamls: [],
          games: { 'Kingdom Hearts 2': { logic: true, needs_yaml: false } }, ...config,
        }
      } else if (url === '/api/discover') {
        body = { room_url: 'https://archipelago.gg/room/x', server: 'archipelago.gg:1', players }
      }
      return new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } })
    }),
  )
}

async function mountForm(): Promise<ConfigForm> {
  let form!: ConfigForm
  mount(defineComponent({ setup() { form = useConfigForm(); return () => h('div') } }))
  await form.load()
  await flushPromises()
  return form
}

const A = { name: 'A', game: 'Kingdom Hearts 2', owner: null, yaml: null, goal: {} }

describe('useConfigForm', () => {
  it('nothing to save right after loading; a change, then « Annuler »', async () => {
    stubFetch({ slots: [A] })
    const form = await mountForm()
    expect(form.dirty.value).toBe(false)
    form.rows.value[0].goalNeeds = false
    expect(form.dirty.value).toBe(true)
    form.reset()
    expect(form.dirty.value).toBe(false)
    expect(form.rows.value[0].goalNeeds).toBe(true)
  })

  it('a typed password is a change', async () => {
    stubFetch({ slots: [A] })
    const form = await mountForm()
    form.password.value = 'x'
    expect(form.dirty.value).toBe(true)
  })

  it('a yaml matched automatically on opening is a change to save', async () => {
    stubFetch({ slots: [A], yamls: [{ path: 'config/players/a.yaml', players: [{ name: 'A', game: 'Kingdom Hearts 2' }], error: null }] })
    const form = await mountForm()
    expect(form.rows.value[0].yaml).toBe('config/players/a.yaml')
    expect(form.dirty.value).toBe(true)
  })

  it('slots found in the room but not ticked are no change', async () => {
    stubFetch({ slots: [A], room_url: 'https://archipelago.gg/room/x', server: null }, [{ name: 'A', game: 'Kingdom Hearts 2' }, { name: 'B', game: 'Hades' }])
    const form = await mountForm() // the room link is discovered on loading
    expect(form.rows.value.map((r) => r.name)).toContain('B')
    expect(form.dirty.value).toBe(false)
  })
})
