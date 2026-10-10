import type { ConfigResponse, DiscoverResponse } from '../lib/config'
import type { Hint, SlotDetail, SlotSummary } from '../lib/types'

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
    items: { received: 12, new: 2 }, hints: { mine_elsewhere: 1, in_my_world: 2, in_my_world_in_logic: 1 },
    logic: { state: 'ok', count: 14, message: null } }),
  slot({ name: 'Romain_TWW', owner: 'Romain', game: 'The Wind Waker HD', checks: { done: 40, total: 300, remaining: 260 },
    items: { received: 55, new: 0 }, hints: { mine_elsewhere: 3, in_my_world: 1, in_my_world_in_logic: 0 },
    logic: { state: 'ok', count: 1, message: null } }),
  slot({ name: 'Romain_KH2', game: 'Kingdom Hearts 2', checks: { done: 10, total: 450, remaining: 440 },
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
  room_url: mockConfig.room_url,
  server: 'archipelago.gg:38281',
  players: [
    { name: 'Romain_KH2', game: 'Kingdom Hearts 2' },
    { name: 'Romain_Celeste', game: 'Celeste (Open World)' },
    { name: 'Alice_Hades', game: 'Hades' },
    { name: 'Alice_A Link to the Past with a very long slot name', game: 'A Link to the Past' },
  ],
}
