import { describe, expect, it } from 'vitest'
import {
  ALL_OWNERS, NO_OWNER, autoAssociate, buildPutBody, checkByName, diagnose, distinctGames, distinctOwners,
  filterByOwner, filterRows, mergeDiscovered, mergeRows, nameMatches, passwordPayload, probeMessage, roomFromLocation,
  setAll, setChecked, showOwnerFilter,
} from '../src/lib/config'
import { summaryText } from '../src/lib/logic'
import { mk } from './helpers'

const configured = [
  { name: 'Romain_KH2', game: 'Kingdom Hearts 2', owner: 'Romain', yaml: 'config/players/kh2.yaml' },
  { name: 'Old_Slot', game: 'Hades', owner: null, yaml: null },
]
const found = [
  { name: 'Romain_KH2', game: 'Kingdom Hearts 2' },
  { name: 'Alice_Hades', game: 'Hades' },
]

describe('config rows', () => {
  it('merges discovered and configured slots', () => {
    const rows = mergeRows(configured, found)
    expect(rows.map((r) => [r.name, r.checked])).toEqual([['Romain_KH2', true], ['Alice_Hades', false], ['Old_Slot', true]])
    expect(rows[0]).toMatchObject({ yaml: 'config/players/kh2.yaml', owner: 'Romain' })
  })
  it('without discover shows configured ones, checked', () => {
    expect(mergeRows(configured, null).every((r) => r.checked)).toBe(true)
  })
  it('mergeDiscovered keeps edits and adds new unchecked', () => {
    const rows = mergeRows(configured, null)
    rows[0].owner = 'Zed'
    const out = mergeDiscovered(rows, found)
    expect(out).toHaveLength(3)
    expect(out[0].owner).toBe('Zed')
    expect(out[2]).toMatchObject({ name: 'Alice_Hades', checked: false })
  })
  it('quick actions', () => {
    const rows = setAll(mergeRows(configured, found), false)
    expect(rows.some((r) => r.checked)).toBe(false)
    expect(checkByName(rows, 'romain').filter((r) => r.checked).map((r) => r.name)).toEqual(['Romain_KH2'])
    expect(checkByName(rows, '  ')).toBe(rows)
    expect(setAll(rows, true).every((r) => r.checked)).toBe(true)
  })
})

describe('PUT payload', () => {
  it('password: null / "" / value', () => {
    expect(passwordPayload({ value: '', clear: false })).toBeNull()
    expect(passwordPayload({ value: 'x', clear: true })).toBe('')
    expect(passwordPayload({ value: 'pw', clear: false })).toBe('pw')
  })
  it('only checked slots, normalized owner/yaml', () => {
    const rows = mergeRows(configured, found)
    rows[1].checked = true
    rows[1].owner = '  Alice '
    rows[2].checked = false
    const b = buildPutBody({ roomUrl: ' https://archipelago.gg/room/X ', server: 'h:1', password: { value: '', clear: false }, rows })
    expect(b.room_url).toBe('https://archipelago.gg/room/X')
    expect(b.server).toBeUndefined()
    expect(b.password).toBeNull()
    expect(b.slots).toEqual([
      { name: 'Romain_KH2', game: 'Kingdom Hearts 2', owner: 'Romain', yaml: 'config/players/kh2.yaml' },
      { name: 'Alice_Hades', game: 'Hades', owner: 'Alice', yaml: null },
    ])
  })
  it('server when no room url', () => {
    const b = buildPutBody({ roomUrl: '', server: ' h:38281 ', password: { value: 'p', clear: false }, rows: [] })
    expect(b).toEqual({ server: 'h:38281', password: 'p', slots: [] })
  })
})

describe('owner filter', () => {
  const slots = [
    mk({ name: 'a', owner: 'Romain', logic: { state: 'ok', count: 3, message: null } }),
    mk({ name: 'b', owner: 'Alice', logic: { state: 'ok', count: 2, message: null } }),
    mk({ name: 'c', owner: null, logic: { state: 'ok', count: 1, message: null } }),
  ]
  it('detects owners', () => {
    expect(distinctOwners(slots)).toEqual(['Alice', 'Romain'])
    expect(showOwnerFilter(slots)).toBe(true)
    expect(showOwnerFilter(slots.slice(0, 1))).toBe(false)
    expect(showOwnerFilter([slots[0], slots[2]])).toBe(false)
  })
  it('filters', () => {
    expect(filterByOwner(slots, ALL_OWNERS)).toHaveLength(3)
    expect(filterByOwner(slots, 'Romain').map((s) => s.name)).toEqual(['a'])
    expect(filterByOwner(slots, NO_OWNER).map((s) => s.name)).toEqual(['c'])
    expect(filterByOwner(slots.slice(0, 1), 'Zed')).toHaveLength(1) // no filter with < 2 owners
  })
  it('summary counts only visible slots', () => {
    expect(summaryText(slots)).toBe('3 jeux où avancer')
    expect(summaryText(filterByOwner(slots, 'Romain'))).toBe('1 jeu où avancer')
  })
})

describe('yaml association and diagnosis', () => {
  const yamls = [
    { path: 'config/players/romain/kh2.yaml', players: [{ name: 'romain_kh2', game: 'Kingdom Hearts 2' }], error: null },
    { path: 'config/players/multi.yaml', players: [{ name: 'Bob{number}', game: 'Celeste (Open World)' }, { name: 'Bob', game: 'Jak 3' }], error: null },
    { path: 'config/players/bad.yaml', players: [], error: 'yaml illisible' },
    { path: 'config/players/other.yaml', players: [{ name: 'romain_kh2', game: 'Kingdom Hearts 2' }], error: null },
  ]
  const games = {
    'Kingdom Hearts 2': { logic: true, needs_yaml: true },
    'Celeste (Open World)': { logic: true, needs_yaml: true },
    PokePark: { logic: false, needs_yaml: false },
  }
  const row = (name: string, game: string, yaml = '') => ({ name, game, yaml, checked: false, owner: '' })

  it('name placeholders', () => {
    expect(nameMatches('Bob{number}', 'Bob2')).toBe(true)
    expect(nameMatches('Bob{number}', 'Bob')).toBe(true)
    expect(nameMatches('Bob{number}', 'Bobby')).toBe(false)
    expect(nameMatches('a.b', 'axb')).toBe(false)
    expect(nameMatches('P{player}_x', 'P12_x')).toBe(true)
  })
  it('associates only unambiguous matches', () => {
    const rows = [row('romain_kh2', 'Kingdom Hearts 2'), row('Bob3', 'Celeste (Open World)'), row('Bob', 'Hades')]
    const { rows: out, matched } = autoAssociate(rows, yamls, true)
    expect(matched).toBe(1)
    expect(out[0].yaml).toBe('') // two yamls describe romain_kh2: ambiguous
    expect(out[1]).toMatchObject({ yaml: 'config/players/multi.yaml', checked: true })
    expect(out[2].yaml).toBe('')
  })
  it('diagnoses', () => {
    const texts = (r: ReturnType<typeof row>) => diagnose(r, yamls, games).map((d) => `${d.level}:${d.text}`)
    expect(texts(row('x', 'Kingdom Hearts 2'))).toEqual(['warn:yaml nécessaire pour la logique'])
    expect(texts(row('x', 'Hades'))).toEqual(["info:pas d'apworld : suivi des checks seulement"])
    expect(texts(row('x', 'PokePark'))).toEqual(['info:logique pas encore validée pour ce jeu'])
    expect(texts(row('romain_kh2', 'Celeste (Open World)', 'config/players/romain/kh2.yaml'))).toEqual([
      'error:ce yaml est pour Kingdom Hearts 2',
    ])
    expect(texts(row('Alice', 'Kingdom Hearts 2', 'config/players/romain/kh2.yaml'))).toEqual([
      'warn:nom différent dans le yaml (romain_kh2)',
    ])
    expect(texts(row('romain_kh2', 'Kingdom Hearts 2', 'config/players/bad.yaml'))[0]).toMatch(/^error:yaml illisible/)
    expect(texts(row('romain_kh2', 'Kingdom Hearts 2', 'config/players/romain/kh2.yaml'))).toEqual([])
    expect(texts(row('romain_kh2', 'Kingdom Hearts 2', 'config/players/gone.yaml'))).toEqual([
      'warn:yaml introuvable dans config/players/',
    ])
  })
  it('filters and bulk checks visible rows', () => {
    const rows = [row('romain_kh2', 'Kingdom Hearts 2'), row('Bob', 'Hades'), { ...row('Ann', 'Hades'), checked: true }]
    expect(filterRows(rows, { text: 'hades', game: '', checkedOnly: false }).map((r) => r.name)).toEqual(['Bob', 'Ann'])
    expect(filterRows(rows, { text: '', game: 'Hades', checkedOnly: true }).map((r) => r.name)).toEqual(['Ann'])
    const out = setChecked(rows, new Set(['Bob']), true)
    expect(out.filter((r) => r.checked).map((r) => r.name)).toEqual(['Bob', 'Ann'])
    expect(distinctGames(rows)).toEqual(['Hades', 'Kingdom Hearts 2'])
  })
  it('room link from the location', () => {
    expect(roomFromLocation('#config?room=https%3A%2F%2Farchipelago.gg%2Froom%2FAbc', '')).toBe('https://archipelago.gg/room/Abc')
    expect(roomFromLocation('#config', '?room=https://archipelago.gg/room/X')).toBe('https://archipelago.gg/room/X')
    expect(roomFromLocation('#config', '')).toBe('')
  })
  it('probe messages', () => {
    expect(probeMessage({ ok: false, errors: ['InvalidPassword'] }, 'a')).toBe('Échec : mot de passe refusé')
    expect(probeMessage({ ok: true, errors: [], game: 'Jak 3' }, 'a')).toBe('Connexion réussie (slot a, Jak 3).')
  })
})
