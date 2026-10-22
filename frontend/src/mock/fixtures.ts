import type { ConfigResponse, DiscoverResponse } from '../lib/config'
import type { Hint, HistoryPage, HistorySlot, ReceivedEntry, RecentItem, SentCheck, SlotDetail, SlotSummary } from '../lib/types'

function slot(p: Partial<SlotSummary> & { name: string; game: string }): SlotSummary {
  const total = p.checks?.total ?? 100
  const done = p.checks?.done ?? 0
  return {
    owner: null,
    status: 'connected',
    error: null,
    seed_name: 'mock',
    items: { received: 0, new: 0 },
    hints: { mine_elsewhere: 0, in_my_world: 0, in_my_world_in_logic: 0 },
    goal: false,
    logic: { state: 'ok', count: 0, message: null },
    ...p,
    checks: { done, total, remaining: total - done },
  }
}

export const mockSlots: SlotSummary[] = [
  slot({ name: 'Romain_Celeste', game: 'Celeste (Open World)', checks: { done: 3, total: 233, remaining: 230 },
    objective: { summary: '40 fraises, puis The Summit A', source: 'slot_data + yaml',
      counters: [{ label: 'Strawberry', current: 40, target: 40 }],
      steps: [{ label: 'Finir The Summit A (The Summit A - Level Clear)', done: true }, { label: 'Ascension (event)', done: null }, { label: 'Épilogue', done: false }] },
    items: { received: 12, new: 2 }, hints: { mine_elsewhere: 1, in_my_world: 2, in_my_world_in_logic: 1 },
    logic: { state: 'ok', count: 14, message: null } }),
  slot({ name: 'Romain_TWW', owner: 'Romain', last_check_at: Date.now() / 1000 - 4 * 60, game: 'The Wind Waker HD', checks: { done: 40, total: 300, remaining: 260 },
    objective: { summary: 'Les 8 Triforce Shards, puis Ganondorf', source: 'slot_data',
      counters: [{ label: 'Triforce Shards', current: 3, target: 8 }], steps: [{ label: 'Vaincre Ganondorf', done: false }] },
    items: { received: 55, new: 0 }, hints: { mine_elsewhere: 3, in_my_world: 1, in_my_world_in_logic: 0 },
    logic: { state: 'ok', count: 1, message: null } }),
  slot({ name: 'Romain_KH2', game: 'Kingdom Hearts 2', checks: { done: 10, total: 450, remaining: 440 },
    objective: { summary: '40 Lucky Emblems, puis Final Xemnas', source: 'slot_data',
      counters: [{ label: 'Lucky Emblems', current: 23, target: 40 }], steps: [{ label: 'Vaincre Final Xemnas', done: false }] },
    items: { received: 20, new: 7 },
    logic: { state: 'unavailable', count: 0, message: "Pas d'apworld compatible pour ce jeu (logique non calculable sans lancer le jeu)." } }),
  slot({ name: 'Romain_Hades', owner: 'Alice', game: 'Hades', checks: { done: 5, total: 90, remaining: 85 },
    items: { received: 3, new: 0 }, logic: { state: 'ok', count: 0, message: null } }),
  slot({ name: 'Romain_Pokemon', game: 'Pokemon Emerald', checks: { done: 12, total: 250, remaining: 238 },
    logic: { state: 'pending', count: 0, message: null } }),
  slot({ name: 'Romain_Sonic', game: 'Sonic Adventure 2: Battle', checks: { done: 0, total: 160, remaining: 160 },
    status: 'error', error: 'Mot de passe refusé par le serveur.',
    logic: { state: 'error', count: 0, message: 'Erreur de calcul : slot inconnu.' } }),
  slot({ name: 'Romain_Zelda', game: 'A Link to the Past', checks: { done: 80, total: 216, remaining: 136 },
    status: 'disconnected', error: 'Connexion perdue, nouvelle tentative…',
    items: { received: 90, new: 0 }, logic: { state: 'ok', count: 0, message: null } }),
  slot({ name: 'Romain_Dino', game: 'Dinosaur Planet', checks: { done: 77, total: 77, remaining: 0 },
    goal: true, items: { received: 40, new: 0 }, logic: { state: 'ok', count: 0, message: null } }),
]

const hint = (h: Partial<Hint> & { item: string; location: string }): Hint => ({
  finder: 'TWWHD', finder_game: 'The Wind Waker HD', receiver: 'Romain_Celeste',
  receiver_game: 'Celeste (Open World)', found: false, progression: false, useful: false,
  trap: false, in_logic: false, status: 'priority', ...h,
})

export function mockDetail(name: string): SlotDetail {
  const s = mockSlots.find((x) => x.name === name) ?? mockSlots[0]
  const n = s.items.received
  const items = Array.from({ length: Math.min(n, 14) }, (_, i) => ({
    index: n - 1 - i,
    name: ['Dash Refill', 'Hookshot', 'Rupee (50)', 'Bomb Trap', 'Strawberry', 'Heart Container', 'Key'][i % 7],
    sender: i % 3 === 0 ? s.name : ['KH2', 'TWWHD', 'Hades'][i % 3],
    own: i % 3 === 0,
    location: 'Forsaken City - Strawberry ' + (i + 1),
    progression: i % 7 === 1 || i % 7 === 0,
    useful: i % 7 === 5,
    trap: i % 7 === 3,
    new: i < s.items.new,
    received_at: i < 9 ? Date.now() / 1000 - i * i * 1500 : null,
  }))
  const logicLocs = Array.from({ length: s.logic.state === 'ok' ? s.logic.count : 0 }, (_, i) => ({
    id: 211877922 + i,
    name: `Forsaken City - Strawberry ${i + 1}`,
    hint: i < s.hints.in_my_world_in_logic ? { item: 'Hookshot', receiver: 'TWWHD', progression: true } : null,
  }))
  return {
    ...s,
    items_list: items,
    in_logic_locations: logicLocs,
    hints_mine_elsewhere: s.hints.mine_elsewhere
      ? [hint({ item: 'Strawberry', location: 'Hyrule - Chest', progression: true }),
         hint({ item: 'Dash Refill', location: 'Outset Island - Crate', found: true })]
      : [],
    hints_in_my_world: s.hints.in_my_world
      ? [hint({ item: 'Hookshot', location: 'Forsaken City - Strawberry 1', receiver: 'TWWHD', in_logic: true, progression: true }),
         hint({ item: 'Rupee (50)', location: 'Old Site - Key', receiver: 'KH2' }),
         hint({ item: 'Bomb Trap', location: 'Resort - Pool', receiver: 'Hades', found: true, trap: true })]
      : [],
    players: {},
  }
}

export function mockRecent(): RecentItem[] {
  const now = Date.now() / 1000
  const names = ['Hookshot', 'Dash Refill', 'Bomb Trap', 'Fire', 'Progressive Sword', 'Rupee (50)', 'Heart Container']
  return Array.from({ length: 12 }, (_, i) => {
    const s = mockSlots[i % 4]
    return {
      index: 40 - i, name: names[i % names.length], sender: ['Alice_OoT', 'Bob_SM64', 'Carol_Hades'][i % 3],
      own: false, origin: 'other' as const, location: 'Some Location ' + i, progression: i % 3 === 0,
      useful: i % 7 === 6, trap: i % 7 === 2, new: i < 2, received_at: now - 40 - i * i * 400, received_after: null,
      slot: s.name, game: s.game, owner: s.owner,
    }
  })
}

export function mockHistory(kind: 'sent' | 'received', slots: string[], limit = 200, offset = 0): HistoryPage<any> {
  const chosen = mockSlots.filter((s) => slots.length === 0 || slots.includes(s.name))
  const names = new Set(chosen.map((s) => s.name))
  const hslots: HistorySlot[] = chosen.map((s) => ({
    name: s.name, game: s.game, owner: s.owner, checks: { done: s.checks.done, total: s.checks.total },
    sent: s.sent ?? { known: 0, to_others: 0 }, received: s.items.received,
  }))
  let items: Array<SentCheck | ReceivedEntry>
  if (kind === 'sent') {
    const now = Date.now() / 1000
    const pool = chosen.length ? chosen : mockSlots
    items = Array.from({ length: 130 }, (_, i) => {
      const s = pool[i % pool.length]
      const day = i < 5 ? 0 : i < 9 ? 1 : i < 125 ? 2 + Math.floor((i - 9) / 20) : null
      const checked_at = day === null ? null : now - day * 86400 - i * 1800
      const item = i === 11 ? null : ['Hookshot', 'Dash Refill', 'Bomb Trap', 'Fire', 'Rupee (50)'][i % 5]
      return {
        slot: s.name, game: s.game, owner: s.owner, location_id: 1000 + i, location: 'Mock Location ' + i,
        checked_at, checked_after: null, item, receiver: item ? (i % 2 ? 'Alice_Hades' : s.name) : null,
        receiver_game: item ? (i % 2 ? 'Hades' : s.game) : null, to_self: item ? i % 2 === 0 : null,
        progression: i % 3 === 0, useful: i % 7 === 6, trap: i % 5 === 3,
      }
    })
  } else {
    items = mockRecent().filter((r) => names.has(r.slot)) as unknown as ReceivedEntry[]
  }
  return { kind, total: items.length, offset, items: items.slice(offset, offset + limit), slots: hslots, scout_checked: true }
}

export const mockConfig: ConfigResponse = {
  room_url: 'https://archipelago.gg/room/AbCdEfGhIjKlMnOpQrSt',
  server: 'archipelago.gg:38281',
  has_password: true,
  slots: [
    { name: 'Romain_KH2', game: 'Kingdom Hearts 2', owner: 'Romain', yaml: 'config/players/kh2.yaml' },
    { name: 'Romain_Celeste', game: 'Celeste (Open World)', owner: 'Romain', yaml: null },
  ],
  player_yamls: ['config/players/kh2.yaml', 'config/players/celeste.yaml'],
}
export const mockDiscover: DiscoverResponse = {
  room_url: mockConfig.room_url ?? '',
  server: 'archipelago.gg:38281',
  players: [
    { name: 'Romain_KH2', game: 'Kingdom Hearts 2' },
    { name: 'Romain_Celeste', game: 'Celeste (Open World)' },
    { name: 'Alice_Hades', game: 'Hades' },
    { name: 'Alice_A Link to the Past with a very long slot name', game: 'A Link to the Past' },
  ],
}
