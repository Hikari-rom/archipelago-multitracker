import { describe, expect, it } from 'vitest'
import { hintInMyWorld, hintMineElsewhere, logicBadge, sortSlots, summaryText } from '../src/lib/logic'
import type { Hint } from '../src/lib/types'
import { mk } from './helpers'

describe('logicBadge', () => {
  it('plural', () => {
    expect(logicBadge(mk({ name: 'a', logic: { state: 'ok', count: 14, message: null } }))).toEqual({
      text: 'Tu peux avancer : 14 checks en logique', variant: 'good' })
  })
  it('singular', () => {
    expect(logicBadge(mk({ name: 'a', logic: { state: 'ok', count: 1, message: null } })).text)
      .toBe('Tu peux avancer : 1 check en logique')
  })
  it('zero', () => {
    const b = logicBadge(mk({ name: 'a' }))
    expect(b.text).toBe("Rien en logique pour l'instant")
    expect(b.variant).toBe('neutral')
  })
  it('unavailable and error carry message', () => {
    for (const state of ['unavailable', 'error'] as const) {
      const b = logicBadge(mk({ name: 'a', logic: { state, count: 0, message: 'pourquoi' } }))
      expect(b).toEqual({ text: 'Logique indisponible pour ce jeu', variant: 'muted', secondary: 'pourquoi' })
    }
  })
  it('pending', () => {
    expect(logicBadge(mk({ name: 'a', logic: { state: 'pending', count: 0, message: null } }))).toMatchObject({
      text: 'Calcul de la logique…', variant: 'pending' })
  })
})

describe('sortSlots', () => {
  const names = (l: ReturnType<typeof sortSlots>) => l.map((s) => s.name)
  it('orders groups and ranks', () => {
    const slots = [
      mk({ name: 'goal', goal: true, logic: { state: 'ok', count: 9, message: null } }),
      mk({ name: 'idle' }),
      mk({ name: 'logic3', logic: { state: 'ok', count: 3, message: null } }),
      mk({ name: 'logic8', logic: { state: 'ok', count: 8, message: null } }),
      mk({ name: 'new5', logic: { state: 'unavailable', count: 0, message: null }, items: { received: 5, new: 5 } }),
      mk({ name: 'hint', hints: { mine_elsewhere: 0, in_my_world: 1, in_my_world_in_logic: 1 } }),
      mk({ name: 'err', status: 'error', logic: { state: 'error', count: 0, message: null } }),
    ]
    expect(names(sortSlots(slots))).toEqual(['hint', 'logic8', 'logic3', 'new5', 'idle', 'err', 'goal'])
  })
  it('does not mutate and is stable', () => {
    const slots = [mk({ name: 'x' }), mk({ name: 'y' })]
    expect(names(sortSlots(slots))).toEqual(['x', 'y'])
    expect(names(slots)).toEqual(['x', 'y'])
  })
})

describe('hint formatting', () => {
  const h = { item: 'Hookshot', location: 'Chest', finder: 'TWWHD', finder_game: 'The Wind Waker HD',
    receiver: 'KH2', receiver_game: 'KH2' } as Hint
  it('mine elsewhere', () => {
    expect(hintMineElsewhere(h)).toBe('Ton Hookshot est à Chest dans le monde de TWWHD (The Wind Waker HD)')
  })
  it('in my world', () => {
    expect(hintInMyWorld(h)).toBe('Chest contient Hookshot pour KH2')
  })
})

describe('summaryText', () => {
  it('counts', () => {
    const ok = (n: string) => mk({ name: n, logic: { state: 'ok', count: 2, message: null } })
    expect(summaryText([ok('a'), ok('b'), ok('c')])).toBe('3 jeux où avancer')
    expect(summaryText([ok('a')])).toBe('1 jeu où avancer')
    expect(summaryText([])).toBe('Aucun jeu où avancer en logique')
  })
})

import { groupLocations } from '../src/lib/logic'

describe('groupLocations', () => {
  const loc = (id: number, name: string, region: string | null, hint = false) => ({
    id, name, region, hint: hint ? { item: 'X', receiver: 'Y', progression: true } : null,
  })
  it('keeps short lists flat, hinted first', () => {
    const g = groupLocations([loc(1, 'a', 'R1'), loc(2, 'b', 'R2', true)])
    expect(g.map((x) => x.title)).toEqual(['Hintées', 'Autres'])
  })
  it('groups long lists by region', () => {
    const locs = Array.from({ length: 14 }, (_, i) => loc(i, `l${i}`, i % 2 ? 'Zone B' : 'Zone A'))
    const g = groupLocations(locs)
    expect(g.map((x) => x.title)).toEqual(['Zone A', 'Zone B'])
    expect(g[0].locations).toHaveLength(7)
  })
  it('does not group when regions are unknown', () => {
    const g = groupLocations(Array.from({ length: 20 }, (_, i) => loc(i, `l${i}`, null)))
    expect(g).toHaveLength(1)
    expect(g[0].title).toBeNull()
  })
})
