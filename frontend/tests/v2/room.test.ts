import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import { installMock } from '../../src/lib/api'
import type { MockApi } from '../../src/lib/api'
import type { RoomFeedPlayer, RoomFeedSlot, RoomFeedStatus, RoomFeedSummary } from '../../src/lib/types'
import { setView, tracker } from '../../src/stores/tracker'
import { hhmm } from '../../src/v2/lib/card'
import RoomHeader from '../../src/v2/components/room/RoomHeader.vue'
import RoomLeaderboard from '../../src/v2/components/room/RoomLeaderboard.vue'
import RoomPlaying from '../../src/v2/components/room/RoomPlaying.vue'
import RoomV2 from '../../src/v2/views/RoomV2.vue'

const slot = (over: Partial<RoomFeedSlot> = {}): RoomFeedSlot => ({
  name: 'S', game: 'G', done: 0, total: 10, goal: false, presence: 'offline', last_check_at: null, bk: null, ...over,
})
const player = (name: string, slots: RoomFeedSlot[], over: Partial<RoomFeedPlayer> = {}): RoomFeedPlayer => ({
  player: name, me: false, done: slots.reduce((n, s) => n + s.done, 0), total: slots.reduce((n, s) => n + s.total, 0),
  goals: slots.filter((s) => s.goal).length, playing: slots.filter((s) => s.presence === 'playing').length,
  last_check_at: null, slots, ...over,
})
// Alice: 50 % (5/10), Bob: 80 % (8/10), Carol: 40 % (40/100, the most checks), toi: 5 % with a BK slot and a goal.
const players = [
  player('Alice', [slot({ name: 'Alice_Hades', game: 'Hades', done: 5, presence: 'playing' })]),
  player('Bob', [slot({ name: 'Bob_OoT', game: 'Ocarina of Time', done: 8, goal: true, presence: 'connected' })]),
  player('Carol', [slot({ name: 'Carol_SM', game: 'Super Metroid', done: 40, total: 100 })]),
  player('toi', [slot({ name: 'Romain_KH2', game: 'Kingdom Hearts 2', done: 1, bk: true }), slot({ name: 'Romain_Celeste', game: 'Celeste', done: 0, bk: false })], { me: true }),
]
const summary: RoomFeedSummary = { room: { done: 54, total: 130, slots: 5, goals: 1, playing: 1 }, players }

function mockFeed(over: Partial<MockApi>) {
  installMock({ getSlot: async () => { throw new Error('no') }, markSeen: async () => ({ seen: 0 }), ...over })
}

const names = (w: ReturnType<typeof mount>) => w.findAll('[data-player-name]').map((e) => e.text())

afterEach(() => {
  tracker.roomDashboard = false
  setView('dashboard')
})

describe('RoomV2', () => {
  it('disabled: message and a button to the configuration', async () => {
    mockFeed({ getRoomFeed: async () => ({ enabled: false }) })
    tracker.roomDashboard = false
    const w = mount(RoomV2)
    await flushPromises()
    expect(w.text()).toContain('Le tableau de bord de la room complète est désactivé.')
    const b = w.findAll('button').find((x) => x.text() === 'Ouvrir la configuration')!
    await b.trigger('click')
    expect(tracker.view).toBe('config')
    w.unmount()
  })

  it('enabled: header, playing, leaderboard sections in order, with a right column left for the next sections', async () => {
    const st: RoomFeedStatus = { enabled: true, state: 'listening', listening_since: 1_700_000_000, catchup_available: true, last_poll_at: 1_700_000_300 }
    mockFeed({ getRoomFeed: async () => st, getRoomFeedSummary: async () => summary })
    tracker.roomDashboard = true
    const w = mount(RoomV2)
    await flushPromises()
    const heads = w.findAll('h3').map((h) => h.text())
    expect(heads).toEqual(['En jeu maintenant', 'Classement'])
    expect(w.text()).toContain('En écoute depuis')
    expect(w.find('[data-room-side]').exists()).toBe(true)
    w.unmount()
  })
})

describe('RoomHeader', () => {
  const room = summary.room
  const mountHeader = (status: RoomFeedStatus) => mount(RoomHeader, { props: { status, room } })

  it('listening: since and last poll times, totals and the help line', () => {
    const w = mountHeader({ enabled: true, state: 'listening', listening_since: 1_700_000_000, last_poll_at: 1_700_000_300, catchup_available: true })
    expect(w.text()).toContain(`En écoute depuis ${hhmm(1_700_000_000)}`)
    expect(w.text()).toContain(`Dernier relevé ${hhmm(1_700_000_300)}`)
    expect(w.text()).toContain('54 / 130')
    expect(w.text()).toContain('42 %')
    expect(w.text()).toContain('1 / 5 buts')
    expect(w.text()).toContain('1 en jeu')
    expect(w.text()).toContain('« En jeu » : client de jeu connecté ou check il y a moins de 10 min.')
  })

  it('disconnected, starting, error', () => {
    expect(mountHeader({ enabled: true, state: 'disconnected', catchup_available: true }).text())
      .toContain('Déconnecté — les checks manqués seront rattrapés')
    expect(mountHeader({ enabled: true, state: 'starting', catchup_available: true }).text()).toContain('Démarrage…')
    const err = mountHeader({ enabled: true, state: 'error', error: 'Connexion refusée', catchup_available: true })
    expect(err.text()).toContain('Connexion refusée')
    expect(err.find('.bg-warn').exists()).toBe(true)
  })

  it('no catch-up without a room link; poll and write errors', () => {
    const w = mountHeader({ enabled: true, state: 'listening', catchup_available: false, poll_error: 'HTTP 500', write_error: 'disque plein' })
    expect(w.text()).toContain('Rattrapage indisponible sans lien de room')
    expect(w.text()).toContain('HTTP 500')
    expect(w.text()).toContain('disque plein')
  })
})

describe('RoomPlaying', () => {
  it('playing chips first (player · game, sorted by player), then connected ones muted', () => {
    const ps = [
      player('Zed', [slot({ game: 'Hades', presence: 'playing' })]),
      player('Bob', [slot({ game: 'Celeste', presence: 'connected' }), slot({ game: 'Terraria', presence: 'playing' })]),
      player('Amy', [slot({ game: 'Doom', presence: 'offline' })]),
    ]
    const w = mount(RoomPlaying, { props: { players: ps } })
    const chips = w.findAll('[data-chip]')
    expect(chips.map((c) => c.text())).toEqual(['Bob · Terraria', 'Zed · Hades', 'Bob · Celeste'])
    expect(chips.map((c) => c.attributes('data-chip'))).toEqual(['playing', 'playing', 'connected'])
    expect(chips[2].classes()).toContain('text-muted-foreground')
    expect(w.text()).not.toContain('Doom')
  })
  it('empty', () => {
    const w = mount(RoomPlaying, { props: { players: [player('Amy', [slot()])] } })
    expect(w.text()).toContain('Personne pour l\'instant.')
  })
})

describe('RoomLeaderboard', () => {
  const mountBoard = () => mount(RoomLeaderboard, { props: { players } })

  it('sorted by % then by checks (aria-pressed toggles)', async () => {
    const w = mountBoard()
    expect(names(w)).toEqual(['Bob', 'Alice', 'Carol', 'toi'])
    const pct = w.findAll('button').find((b) => b.text() === '%')!
    const checks = w.findAll('button').find((b) => b.text() === 'Checks')!
    expect(pct.attributes('aria-pressed')).toBe('true')
    expect(checks.attributes('aria-pressed')).toBe('false')
    await checks.trigger('click')
    expect(checks.attributes('aria-pressed')).toBe('true')
    expect(pct.attributes('aria-pressed')).toBe('false')
    expect(names(w)).toEqual(['Carol', 'Bob', 'Alice', 'toi'])
    expect(w.findAll('[data-rank]').map((e) => e.text())).toEqual(['1', '2', '3', '4'])
  })

  it('shows totals, goals, playing dot and the « toi » badge only on me', () => {
    const w = mountBoard()
    const rows = w.findAll('[data-row]')
    expect(rows[0].text()).toContain('8 / 10')
    expect(rows[0].text()).toContain('80 %')
    expect(rows[0].text()).toContain('1/1')
    expect(rows[0].find('[data-playing-dot]').exists()).toBe(false)
    expect(rows[1].find('[data-playing-dot]').exists()).toBe(true)
    expect(w.findAll('[data-me]')).toHaveLength(1)
    expect(rows[3].find('[data-me]').text()).toBe('toi')
    expect(rows[3].find('.bg-done').attributes('style')).toContain('width: 5%')
  })

  it('a row expands on click to list its slots with goal check, BK and presence', async () => {
    const w = mountBoard()
    expect(w.find('[data-slots]').exists()).toBe(false)
    const rows = w.findAll('[data-row]')
    const btn = rows[3].find('button[aria-expanded]')
    expect(btn.attributes('aria-expanded')).toBe('false')
    await btn.trigger('click')
    expect(btn.attributes('aria-expanded')).toBe('true')
    const list = w.find('[data-slots]')
    expect(list.text()).toContain('Kingdom Hearts 2')
    expect(list.text()).toContain('Romain_KH2')
    expect(list.text()).toContain('1 / 10')
    expect(list.findAll('[data-bk]')).toHaveLength(1)
    expect(list.text()).toContain('Hors ligne')
    await rows[0].find('button[aria-expanded]').trigger('click')
    const bob = w.findAll('[data-slots]')
    expect(bob).toHaveLength(2)
    expect(bob[0].text()).toContain('✓')
    expect(bob[0].text()).toContain('Connecté')
    await btn.trigger('click')
    expect(w.findAll('[data-slots]')).toHaveLength(1)
  })

  it('long names are truncated with a title', () => {
    const w = mount(RoomLeaderboard, { props: { players: [player('P'.repeat(60), [slot()])] } })
    const n = w.find('[data-player-name]')
    expect(n.classes()).toContain('truncate')
    expect(n.attributes('title')).toBe('P'.repeat(60))
  })
})
