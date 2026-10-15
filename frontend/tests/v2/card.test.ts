import { describe, expect, it } from 'vitest'
import { cardState, type CardCtx } from '../../src/v2/lib/card'
import { mk } from '../helpers'

const NOW = 1_800_000_000_000
const ago = (min: number) => NOW / 1000 - min * 60
const ctx = (p: Partial<CardCtx> = {}): CardCtx => ({
  nowMs: NOW, activeMinutes: 30, activity: { pinned: null, dismissed: {} }, roomSleeping: false, ...p,
})

describe('cardState', () => {
  it('auto active: minutes ago and minutes left, never negative', () => {
    const s = mk({ name: 'a', last_check_at: ago(12), logic: { state: 'ok', count: 7, message: null } })
    expect(cardState(s, ctx()).activity).toEqual({ kind: 'auto', agoMin: 12, expiresInMin: 18 })
    expect(cardState(mk({ name: 'b', last_check_at: ago(29.9) }), ctx()).activity).toEqual({ kind: 'auto', agoMin: 29, expiresInMin: 1 })
    expect(cardState(mk({ name: 'c', last_check_at: ago(30) }), ctx()).activity).toBeNull()
  })
  it('chosen by hand wins over auto', () => {
    const s = mk({ name: 'a', last_check_at: ago(5) })
    expect(cardState(s, ctx({ activity: { pinned: { name: 'a', at: ago(1) }, dismissed: {} } })).activity).toEqual({ kind: 'chosen' })
  })
  it('big number for every logic state', () => {
    expect(cardState(mk({ name: 'a', logic: { state: 'ok', count: 58, message: null } }), ctx()).big).toBe('58')
    expect(cardState(mk({ name: 'a', logic: { state: 'ok', count: 21, message: 'options aléatoires' } }), ctx())).toMatchObject({
      big: '21', logic: { kind: 'ok', approx: true },
    })
    expect(cardState(mk({ name: 'a', logic: { state: 'unavailable', count: 0, message: null } }), ctx()).big).toBe('—')
    expect(cardState(mk({ name: 'a', logic: { state: 'error', count: 0, message: 'x' } }), ctx()).big).toBe('—')
    expect(cardState(mk({ name: 'a', logic: { state: 'pending', count: 0, message: null } }), ctx())).toMatchObject({
      big: '··', logic: { kind: 'pending', waiting: false },
    })
    expect(cardState(mk({ name: 'a', status: 'connecting', logic: { state: 'pending', count: 0, message: null } }), ctx()).logic).toEqual({
      kind: 'pending', waiting: true,
    })
  })
  it('connection: ok, sleeping room, error message', () => {
    expect(cardState(mk({ name: 'a' }), ctx()).connection).toEqual({ kind: 'ok' })
    const off = mk({ name: 'a', status: 'disconnected', error: 'ConnectionRefusedError', updated_at: NOW / 1000 - 3600 })
    expect(cardState(off, ctx({ roomSleeping: true })).connection.kind).toBe('sleeping')
    expect(cardState(off, ctx()).connection).toEqual({ kind: 'error', message: 'Serveur injoignable, nouvel essai automatique.' })
    expect(cardState(mk({ name: 'a', status: 'error', error: null }), ctx()).connection).toEqual({ kind: 'error', message: 'Erreur' })
    expect(cardState(mk({ name: 'a', status: 'connecting' }), ctx()).connection).toEqual({ kind: 'connecting' })
  })
  it('goal reached', () => {
    expect(cardState(mk({ name: 'a', goal: true }), ctx()).goalReached).toBe(true)
  })
})
