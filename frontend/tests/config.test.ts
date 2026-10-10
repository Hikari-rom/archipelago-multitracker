import { describe, expect, it } from 'vitest'
import {
  ALL_OWNERS, NO_OWNER, buildPutBody, checkByName, distinctOwners, filterByOwner, mergeDiscovered, mergeRows,
  passwordPayload, setAll, showOwnerFilter,
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
