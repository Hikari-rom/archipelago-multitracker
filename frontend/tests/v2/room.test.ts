import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { installMock } from '../../src/lib/api'
import type { MockApi } from '../../src/lib/api'
import type {
  RoomFeedActivity, RoomFeedCheck, RoomFeedChecksPage, RoomFeedPlayer, RoomFeedSlot, RoomFeedStatus, RoomFeedSummary,
} from '../../src/lib/types'
import { roomfeedListeners, setView, tracker } from '../../src/stores/tracker'
import { hhmm } from '../../src/v2/lib/card'
import RoomActivity from '../../src/v2/components/room/RoomActivity.vue'
import RoomFeedList from '../../src/v2/components/room/RoomFeedList.vue'
import RoomHeader from '../../src/v2/components/room/RoomHeader.vue'
import RoomLeaderboard from '../../src/v2/components/room/RoomLeaderboard.vue'
import RoomPlaying from '../../src/v2/components/room/RoomPlaying.vue'
import RoomV2 from '../../src/v2/views/RoomV2.vue'

const slot = (over: Partial<RoomFeedSlot> = {}): RoomFeedSlot => ({
  name: 'S', game: 'G', done: 0, total: 10, goal: false, presence: 'offline', last_check_at: null, active_at: null, bk: null, ...over,
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

  it('enabled: header, playing, leaderboard sections in order, activity and feed in the right column', async () => {
    const st: RoomFeedStatus = { enabled: true, state: 'listening', listening_since: 1_700_000_000, catchup_available: true, last_poll_at: 1_700_000_300 }
    mockFeed({
      getRoomFeed: async () => st, getRoomFeedSummary: async () => summary,
      getRoomFeedChecks: async () => ({ total: 0, offset: 0, items: [] }),
      getRoomFeedActivity: async (bucket) => ({ bucket, buckets: [], undated: 0 }),
    })
    tracker.roomDashboard = true
    const w = mount(RoomV2)
    await flushPromises()
    const heads = w.findAll('h3').map((h) => h.text())
    expect(heads).toEqual(['En jeu maintenant', 'Classement', 'Activité', 'Fil des checks'])
    expect(w.text()).toContain('En écoute depuis')
    expect(w.find('[data-room-side]').findAll('h3').map((h) => h.text())).toEqual(['Activité', 'Fil des checks'])
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

  it('disconnected only promises catch-up when it is available; otherwise says why', () => {
    const text = (status: RoomFeedStatus) => mountHeader(status).find('[data-state-line]').text()
    expect(text({ enabled: true, state: 'disconnected', catchup_available: false })).toBe('Déconnecté (room endormie ?)')
    expect(text({ enabled: true, state: 'disconnected', catchup_available: false, error: 'adresse du serveur inconnue (room endormie ?)' }))
      .toBe('Déconnecté — adresse du serveur inconnue (room endormie ?)')
    expect(text({ enabled: true, state: 'disconnected', catchup_available: true, error: 'connexion perdue' }))
      .toBe('Déconnecté — connexion perdue · les checks manqués seront rattrapés')
    expect(text({ enabled: true, state: 'disconnected', catchup_available: false })).not.toContain('rattrapés')
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

  it('« actif il y a N min » for a recent live check only, muted, on the player row and the slot', async () => {
    tracker.nowMs = 1_700_000_000_000
    const ago = (min: number) => 1_700_000_000 - min * 60
    const w = mount(RoomLeaderboard, { props: { players: [
      player('Alice', [slot({ name: 'A1', presence: 'playing', active_at: ago(3) }), slot({ name: 'A2', presence: 'playing', active_at: ago(7) })]),
      player('Bob', [slot({ name: 'B1', presence: 'playing', active_at: ago(30) })]),
      player('Carol', [slot({ name: 'C1', presence: 'playing' })]),
    ] } })
    const rows = w.findAll('[data-row]')
    expect(rows[0].find('[data-active]').text()).toBe('actif il y a 3 min')
    expect(rows[0].find('[data-active]').classes()).toContain('text-muted-foreground')
    expect(rows[1].find('[data-active]').exists()).toBe(false)
    expect(rows[2].find('[data-active]').exists()).toBe(false)
    await rows[0].find('button[aria-expanded]').trigger('click')
    const slots = rows[0].findAll('[data-slots] li').map((li) => li.text())
    expect(slots[0]).toContain('En jeu · actif il y a 3 min')
    expect(slots[1]).toContain('En jeu · actif il y a 7 min')
  })

  it('long names are truncated with a title', () => {
    const w = mount(RoomLeaderboard, { props: { players: [player('P'.repeat(60), [slot()])] } })
    const n = w.find('[data-player-name]')
    expect(n.classes()).toContain('truncate')
    expect(n.attributes('title')).toBe('P'.repeat(60))
  })
})

const T = (d: number, h: number, m: number) => new Date(2026, 9, d, h, m).getTime() / 1000
const chk = (over: Partial<RoomFeedCheck>): RoomFeedCheck => ({
  key: '1:1', at: T(23, 14, 5), after: null, before: null, src: 'live', sender: 'Alice_Hades', sender_game: 'Hades', sender_player: 'Alice',
  receiver: 'Bob_OoT', receiver_game: 'Ocarina of Time', receiver_player: 'Bob', item: 'Boomerang', location: 'Chamber 1',
  category: null, mine: false, self: false, ...over,
})
const feedChecks: RoomFeedCheck[] = [
  chk({ key: '1:1', category: 'PROG', mine: true, receiver: 'Romain_KH2', receiver_game: 'Kingdom Hearts 2', receiver_player: 'toi' }),
  chk({ key: '1:2', at: T(23, 13, 40), self: true, receiver: 'Alice_Hades', receiver_game: 'Hades', receiver_player: 'Alice', item: 'Hammer', location: 'Chamber 2' }),
  chk({ key: '2:3', at: null, after: T(23, 12, 2), before: T(23, 12, 20), src: 'catchup', sender_player: 'Bob', sender_game: 'Ocarina of Time', category: 'PIÈGE', item: 'Trap', location: 'Deku Tree' }),
  chk({ key: '2:4', at: null, src: 'catchup', sender_player: 'Bob', sender_game: 'Ocarina of Time', category: 'UTILE', item: 'Bombs', location: 'Kokiri' }),
  chk({ key: '1:5', at: T(22, 23, 50), item: 'Old', location: 'Chamber 9' }),
]
const feedPage = (items: RoomFeedCheck[], total = items.length): RoomFeedChecksPage => ({ total, offset: 0, items })
const lastCheck = <T,>(xs: T[]): T => xs[xs.length - 1]

describe('RoomFeedList', () => {
  enableAutoUnmount(afterEach) // a leaked list would react to the stream state of the next test
  const setup = (getRoomFeedChecks: (p: any) => Promise<RoomFeedChecksPage>) => {
    mockFeed({ getRoomFeedChecks })
    tracker.nowMs = new Date(2026, 9, 23, 15, 0).getTime()
    return mount(RoomFeedList, { props: { players } })
  }

  afterEach(() => window.scrollTo(0, 0))

  it('rows: time, sender, location, category, item, receiver wording, catch-up mentions, day headings', async () => {
    const w = setup(async () => feedPage(feedChecks))
    await flushPromises()
    const rows = w.findAll('li[data-index]')
    const text = (k: number) => rows.find((r) => r.attributes('data-index') === String(k))!.text()
    expect(w.findAll('[data-day]').map((d) => d.attributes('data-day'))).toEqual(["Aujourd'hui", 'Hier', 'Heure inconnue'])
    expect(text(1)).toContain(hhmm(T(23, 14, 5)))
    expect(text(1)).toContain('Alice · Hades')
    expect(text(1)).toContain('Chamber 1')
    expect(text(1)).toContain('PROG')
    expect(text(1)).toContain('Boomerang')
    expect(text(1)).toContain('pour toi')
    expect(w.find('[data-for="me"]').classes()).toContain('text-logic')
    expect(text(2)).toContain('pour lui-même')
    expect(text(3)).toContain(`~${hhmm((T(23, 12, 2) + T(23, 12, 20)) / 2)}`)
    expect(text(3)).toContain(`rattrapé · entre ${hhmm(T(23, 12, 2))} et ${hhmm(T(23, 12, 20))}`)
    expect(text(3)).toContain('pour Bob · Ocarina of Time')
    expect(text(3)).toContain('PIÈGE')
    const unknown = w.text()
    expect(unknown).toContain('rattrapé · heure inconnue')
    expect(w.find('[data-time-none]').text()).toBe('—')
  })

  it('filters: the player / game selects list the room and refetch page 1 with player / game', async () => {
    const calls: any[] = []
    const w = setup(async (p) => (calls.push(p), feedPage(feedChecks)))
    await flushPromises()
    expect(calls).toEqual([{ limit: 50, offset: 0 }])
    const [pl, gm] = w.findAll('select')
    expect(pl.findAll('option').map((o) => o.text())).toEqual(['tous', 'Alice', 'Bob', 'Carol', 'toi'])
    expect(gm.findAll('option').map((o) => o.text())).toContain('Hades')
    await pl.setValue('Bob')
    await flushPromises()
    expect(lastCheck(calls)).toEqual({ limit: 50, offset: 0, player: 'Bob' })
    await gm.setValue('Ocarina of Time')
    await flushPromises()
    expect(lastCheck(calls)).toEqual({ limit: 50, offset: 0, player: 'Bob', game: 'Ocarina of Time' })
  })

  it('live: an incoming check is prepended once (dedup by key), only if it matches the filters, and bumps the total', async () => {
    const listeners = roomfeedListeners.check.size
    const w = setup(async () => feedPage([feedChecks[4]]))
    await flushPromises()
    expect(w.text()).toContain('1 check')
    const live = chk({ key: '3:99', at: T(23, 14, 59), item: 'Fresh item', location: 'Fresh loc' })
    expect(roomfeedListeners.check.size).toBe(listeners + 1)
    for (const fn of [...roomfeedListeners.check]) fn({ type: 'roomfeed_check', checks: [live] })
    for (const fn of [...roomfeedListeners.check]) fn({ type: 'roomfeed_check', checks: [live] })
    await flushPromises()
    expect(w.text().match(/Fresh item/g)).toHaveLength(1)
    expect(w.text()).toContain('2 checks')
    const rows = w.findAll('li[data-index]').filter((r) => !r.find('[data-day]').exists())
    expect(rows[0].text()).toContain('Fresh item')
    // filtered on Bob: Alice's live check does not match
    await w.findAll('select')[0].setValue('Bob')
    await flushPromises()
    for (const fn of [...roomfeedListeners.check]) fn({ type: 'roomfeed_check', checks: [chk({ key: '3:100', item: 'Not for Bob' })] })
    await flushPromises()
    expect(w.text()).not.toContain('Not for Bob')
    w.unmount()
    expect(roomfeedListeners.check.size).toBe(listeners)
  })

  it('live: a catch-up check from an earlier day is inserted under that day, not on top (no duplicate heading key)', async () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    const w = setup(async () => feedPage([feedChecks[0], feedChecks[1], feedChecks[4]]))
    await flushPromises()
    const old = chk({
      key: '9:1', at: null, after: T(22, 23, 55), before: T(23, 0, 5), src: 'catchup', item: 'Straddle', location: 'Midnight',
    })
    const yesterday = chk({ key: '9:2', at: null, after: T(22, 23, 0), before: T(22, 23, 20), src: 'catchup', item: 'Earlier', location: 'Yday' })
    for (const fn of [...roomfeedListeners.check]) fn({ type: 'roomfeed_check', checks: [yesterday, old] })
    await flushPromises()
    const order = w.findAll('li[data-index]').map((r) => r.find('[data-day]').exists() ? `#${r.text().split(' ·')[0]}` : r.text().match(/Boomerang|Hammer|Straddle|Earlier|Old/)![0])
    // Server order: by `at ?? before`, newest first.
    expect(order).toEqual(['#Aujourd\'hui', 'Boomerang', 'Hammer', 'Straddle', '#Hier', 'Old', 'Earlier'])
    expect(w.text()).toContain('5 checks')
    expect(warn.mock.calls.filter((c) => String(c[0]).includes('Duplicate'))).toEqual([])
    warn.mockRestore()
    w.unmount()
  })

  it('live: a check older than everything loaded is left to the next page (only the total moves)', async () => {
    const w = setup(async () => feedPage([feedChecks[0]], 5))
    await flushPromises()
    for (const fn of [...roomfeedListeners.check]) fn({ type: 'roomfeed_check', checks: [chk({ key: '9:3', at: T(20, 10, 0), item: 'Ancient' })] })
    await flushPromises()
    expect(w.text()).not.toContain('Ancient')
    expect(w.text()).toContain('6 checks')
    w.unmount()
  })

  it('live: within one batch the unloaded rows are counted with the batch (an older row waits for its page)', async () => {
    let calls = 0
    // The next page (asked for by the auto-load) never answers: only the live decision is under test.
    const w = setup(async () => (++calls === 1 ? feedPage([feedChecks[0], feedChecks[1]], 3) : new Promise<RoomFeedChecksPage>(() => {})))
    await flushPromises()
    const newer = chk({ key: '9:1', at: T(23, 14, 59), item: 'Newer one', location: 'N' })
    const older = chk({ key: '9:2', at: T(20, 10, 0), item: 'Older one', location: 'O' })
    for (const fn of [...roomfeedListeners.check]) fn({ type: 'roomfeed_check', checks: [newer, older] })
    await flushPromises()
    expect(w.text()).toContain('Newer one')
    expect(w.text()).not.toContain('Older one')
    expect(w.text()).toContain('5 checks')
    w.unmount()
  })

  it('resync: a refreshed summary refetches the first page and merges the new rows in order, total from the server', async () => {
    let page = feedPage([feedChecks[0], feedChecks[1]])
    const calls: any[] = []
    const w = setup(async (p) => (calls.push(p), page))
    await flushPromises()
    expect(w.text()).toContain('2 checks')
    const fresh = [chk({ key: '7:1', at: T(23, 13, 50), item: 'Missed A', location: 'MA' }), chk({ key: '7:2', at: T(23, 13, 30), item: 'Missed B', location: 'MB' })]
    page = feedPage([feedChecks[0], fresh[0], feedChecks[1], fresh[1]], 4)
    await w.setProps({ players: [...players] })
    await flushPromises()
    expect(calls).toEqual([{ limit: 50, offset: 0 }, { limit: 50, offset: 0 }])
    const order = w.findAll('li[data-index]').filter((r) => !r.find('[data-day]').exists()).map((r) => r.text().match(/Boomerang|Hammer|Missed A|Missed B/)![0])
    expect(order).toEqual(['Boomerang', 'Missed A', 'Hammer', 'Missed B'])
    expect(w.text()).toContain('4 checks')
    w.unmount()
  })

  it('resync: an empty feed fills in once the room has rows (history import)', async () => {
    let page = feedPage([])
    const w = setup(async () => page)
    await flushPromises()
    expect(w.text()).toContain('Aucun check pour ces filtres.')
    page = feedPage([feedChecks[0], feedChecks[1]])
    await w.setProps({ players: [...players] })
    await flushPromises()
    expect(w.text()).toContain('Boomerang')
    expect(w.text()).not.toContain('Aucun check')
    w.unmount()
  })

  it('resync: when the event stream reconnects', async () => {
    const calls: any[] = []
    tracker.sse = 'open'
    const w = setup(async (p) => (calls.push(p), feedPage([feedChecks[0]])))
    await flushPromises()
    tracker.sse = 'reconnecting'
    await flushPromises()
    expect(calls).toHaveLength(1)
    tracker.sse = 'open'
    await flushPromises()
    expect(calls).toHaveLength(2)
    w.unmount()
  })

  it('resync is dropped when the filters changed meanwhile', async () => {
    let release!: () => void
    const gate = new Promise<void>((r) => (release = r))
    let n = 0
    const w = setup(async (p) => {
      n++
      if (n === 2) await gate
      return feedPage(p.player === 'Bob' ? [feedChecks[2]] : [feedChecks[0]])
    })
    await flushPromises()
    await w.setProps({ players: [...players] }) // resync (call 2) waits on the gate
    await w.findAll('select')[0].setValue('Bob')
    await flushPromises()
    release()
    await flushPromises()
    expect(w.text()).toContain('Trap')
    expect(w.text()).not.toContain('Boomerang')
    w.unmount()
  })

  it('paging follows a server cursor: duplicates from local live inserts do not stall « Afficher plus »', async () => {
    const old = Array.from({ length: 130 }, (_, i) => chk({ key: `1:${i}`, at: T(23, 10, 0) - i * 60, location: `L${i}`, item: `old${i}` }))
    let server = [...old]
    const calls: any[] = []
    const w = setup(async (p) => (calls.push(p), { total: server.length, offset: p.offset, items: server.slice(p.offset, p.offset + p.limit) }))
    await flushPromises()
    // 60 checks happen live (the page receives them by SSE, the server list has them at its head)
    const live = Array.from({ length: 60 }, (_, i) => chk({ key: `5:${i}`, at: T(23, 14, 0) + i * 10, location: `X${i}`, item: `live${i}` }))
    server = [...live].reverse().concat(server)
    for (const fn of [...roomfeedListeners.check]) fn({ type: 'roomfeed_check', checks: [...live].reverse() })
    await flushPromises()
    await w.find('button.mt-3').trigger('click')
    await flushPromises()
    // offset 50 only returns rows already known; the cursor moves on by itself until new rows come
    expect(calls.map((c) => c.offset)).toEqual([0, 50, 100])
    const keys = (w.vm as any).items.map((c: RoomFeedCheck) => c.key)
    expect(keys).toHaveLength(150) // 60 live rows + old0..old89, none twice, in server order
    expect(new Set(keys).size).toBe(keys.length)
    expect(keys.slice(0, 3)).toEqual(['5:59', '5:58', '5:57'])
    expect(keys.at(-1)).toBe('1:89')
    w.unmount()
  })

  it('tied rows (a history import stamped with one poll time) keep the server order across pages and resyncs', async () => {
    const poll = T(23, 12, 0)
    const imported = (k: number) => chk({ key: `9:${k}`, at: null, after: null, before: poll, src: 'catchup', location: `I${k}` })
    // server order for ties: the most recently logged first
    let server = Array.from({ length: 80 }, (_, i) => imported(79 - i))
    const w = setup(async (p) => ({ total: server.length, offset: p.offset, items: server.slice(p.offset, p.offset + p.limit) }))
    await flushPromises()
    await w.find('button.mt-3').trigger('click')
    await flushPromises()
    const keys = () => (w.vm as any).items.map((c: RoomFeedCheck) => c.key)
    expect(keys()).toEqual(server.map((c) => c.key))
    // two more rows logged by the next poll with the same stamp, then a resync of page 1
    server = [imported(81), imported(80), ...server]
    await w.setProps({ players: [...players] })
    await flushPromises()
    expect(keys()).toEqual(server.map((c) => c.key))
    w.unmount()
  })

  it('an empty page with a total that says more does not loop', async () => {
    const calls: any[] = []
    const w = setup(async (p) => (calls.push(p), p.offset === 0 ? feedPage([feedChecks[0]], 5) : { total: 5, offset: p.offset, items: [] }))
    await flushPromises()
    expect(calls.map((c) => c.offset)).toEqual([0, 1])
    expect(w.find('button.mt-3').exists()).toBe(false)
    w.unmount()
  })

  it('catch-up windows over two days show the date of the start', async () => {
    const straddle = chk({ key: '8:1', at: null, after: T(22, 23, 40), before: T(23, 0, 20), src: 'catchup', item: 'Straddle', location: 'Midnight' })
    const days = chk({ key: '8:2', at: null, after: T(18, 9, 0), before: T(23, 0, 30), src: 'catchup', item: 'Long', location: 'Away' })
    const w = setup(async () => feedPage([straddle, days]))
    await flushPromises()
    expect(w.text()).toContain('rattrapé · entre 22 oct. 23:40 et 00:20')
    expect(w.text()).toContain('rattrapé · entre 18 oct. 09:00 et 23 oct. 00:30')
    w.unmount()
  })

  it('a failed reload clears the rows of the previous filters', async () => {
    let fail = false
    const w = setup(async () => { if (fail) throw new Error('boom'); return feedPage([feedChecks[0]]) })
    await flushPromises()
    expect(w.text()).toContain('Boomerang')
    fail = true
    await w.findAll('select')[0].setValue('Bob')
    await flushPromises()
    expect(w.text()).not.toContain('Boomerang')
    expect(w.find('[role="alert"]').text()).toContain('boom')
    w.unmount()
  })

  it('loads 50 checks per page and fetches the next page when the end of the list comes into view', async () => {
    const all = Array.from({ length: 120 }, (_, i) => chk({ key: `1:${i}`, at: T(23, 14, 0) - i * 60, location: `L${i}` }))
    const calls: any[] = []
    const w = setup(async (p) => (calls.push(p), { total: all.length, offset: p.offset, items: all.slice(p.offset, p.offset + p.limit) }))
    await flushPromises()
    expect(calls).toEqual([{ limit: 50, offset: 0 }])
    expect(w.findAll('li[data-index]').length).toBeLessThan(51)
    window.scrollTo(0, 50 * 40)
    window.dispatchEvent(new Event('scroll'))
    await flushPromises()
    expect(calls.map((c) => c.offset)).toEqual([0, 50])
    w.unmount()
  })

  it('empty feed and error message', async () => {
    const w = setup(async () => feedPage([]))
    await flushPromises()
    expect(w.text()).toContain('Aucun check pour ces filtres.')
    w.unmount()
    const e = setup(async () => { throw new Error('boom') })
    await flushPromises()
    expect(e.find('[role="alert"]').text()).toContain('boom')
    e.unmount()
  })
})

describe('RoomActivity', () => {
  const act = (bucket: 'hour' | 'day', n: number, undated = 0): RoomFeedActivity => ({
    bucket, undated,
    buckets: Array.from({ length: n }, (_, i) => ({
      start: bucket === 'hour' ? new Date(2026, 9, 22, 14 + i).getTime() / 1000 : new Date(2026, 8, 24 + i).getTime() / 1000,
      count: i === 1 ? 23 : i === 2 ? 1 : 0, by_player: {},
    })),
  })
  const setup = (calls: any[], undated = 3) => {
    mockFeed({ getRoomFeedActivity: async (b, p) => (calls.push([b, p]), act(b, b === 'hour' ? 48 : 30, undated)) })
    return mount(RoomActivity, { props: { players } })
  }

  it('one bar per bucket with its title, scaled to the max; max label; undated line', async () => {
    const calls: any[] = []
    const w = setup(calls)
    await flushPromises()
    expect(calls).toEqual([['hour', undefined]])
    const bars = w.findAll('svg rect')
    expect(bars).toHaveLength(48)
    expect(w.find('svg').attributes('viewBox')).toBe('0 0 480 100')
    expect(bars[1].find('title').text()).toBe(`${hhmm(new Date(2026, 9, 22, 15).getTime() / 1000)} · 23 checks`)
    expect(bars[2].find('title').text()).toContain('· 1 check')
    expect(bars[2].find('title').text()).not.toContain('checks')
    expect(Number(bars[1].attributes('height'))).toBe(100)
    expect(Number(bars[2].attributes('height'))).toBeLessThan(10)
    expect(w.find('g').classes()).toContain('text-logic')
    expect(w.find('[data-max]').text()).toContain('23')
    expect(w.text()).toContain('3 checks sans heure')
    expect(w.findAll('[data-xlabel]').length).toBe(8)
  })

  it('no undated line when undated is 0', async () => {
    const w = setup([], 0)
    await flushPromises()
    expect(w.text()).not.toContain('sans heure')
  })

  it('toggle 48 h / 30 jours and the player select refetch', async () => {
    const calls: any[] = []
    const w = setup(calls)
    await flushPromises()
    const days = w.findAll('button').find((b) => b.text() === '30 jours')!
    const hours = w.findAll('button').find((b) => b.text() === '48 h')!
    expect(hours.attributes('aria-pressed')).toBe('true')
    await days.trigger('click')
    await flushPromises()
    expect(days.attributes('aria-pressed')).toBe('true')
    expect(lastCheck(calls)).toEqual(['day', undefined])
    expect(w.findAll('svg rect')).toHaveLength(30)
    expect(w.find('svg').attributes('viewBox')).toBe('0 0 300 100')
    const sel = w.find('select')
    expect(sel.findAll('option').map((o) => o.text())).toEqual(['toute la room', 'Alice', 'Bob', 'Carol', 'toi'])
    await sel.setValue('Carol')
    await flushPromises()
    expect(lastCheck(calls)).toEqual(['day', 'Carol'])
  })

  it('refetches when the players (summary) are refreshed', async () => {
    const calls: any[] = []
    const w = setup(calls)
    await flushPromises()
    await w.setProps({ players: [...players] })
    await flushPromises()
    expect(calls).toHaveLength(2)
  })
})

describe('Task 10 review fixes', () => {
  it('header error spans wrap long tokens', () => {
    const w = mount(RoomHeader, { props: { status: { enabled: true, state: 'error', error: 'x'.repeat(200), poll_error: 'y'.repeat(200), write_error: 'z'.repeat(200) }, room: null } })
    for (const sel of ['[data-state-line]', '[role="alert"]']) for (const e of w.findAll(sel)) expect(e.classes().join(' ')).toMatch(/break-/)
  })
  it('leaderboard ids do not collide for non-ASCII names', async () => {
    const w = mount(RoomLeaderboard, { props: { players: [player('日本', [slot()]), player('中文', [slot()])] } })
    const ids = w.findAll('button[aria-controls]').map((b) => b.attributes('aria-controls'))
    expect(new Set(ids).size).toBe(2)
  })
})
