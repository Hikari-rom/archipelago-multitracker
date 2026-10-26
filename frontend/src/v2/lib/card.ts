// State of a game card in the v2: activity, logic, big number, connection.
import { connectionMessage, isActive, isBK, isChosen, statusLabel, type ActivityOverrides } from '../../lib/logic'
export { isBK }
import type { SlotSummary } from '../../lib/types'
import { computed, type ComputedRef } from 'vue'
import { tracker } from '../../stores/tracker'

export interface CardCtx { nowMs: number; activeMinutes: number; activity: ActivityOverrides; roomSleeping: boolean }
export type CardActivity = { kind: 'chosen' } | { kind: 'auto'; agoMin: number; expiresInMin: number } | null
export type CardLogic =
  | { kind: 'ok'; count: number; approx: boolean; message: string | null }
  | { kind: 'unavailable'; message: string | null }
  | { kind: 'pending'; waiting: boolean }
export type CardConnection = { kind: 'ok' } | { kind: 'connecting' } | { kind: 'sleeping'; since: string | null } | { kind: 'error'; message: string }
export interface CardState { activity: CardActivity; logic: CardLogic; big: string; connection: CardConnection; goalReached: boolean; bk: boolean }


const two = (n: number) => String(n).padStart(2, '0')
export function hhmm(epochSeconds: number): string {
  const d = new Date(epochSeconds * 1000)
  return `${two(d.getHours())}:${two(d.getMinutes())}`
}

function activityOf(s: SlotSummary, c: CardCtx): CardActivity {
  if (isChosen(s.name, c.activity)) return { kind: 'chosen' }
  if (!isActive(s, c.nowMs, c.activeMinutes, c.activity) || !s.last_check_at) return null
  const agoMin = Math.max(0, Math.floor((c.nowMs / 1000 - s.last_check_at) / 60))
  return { kind: 'auto', agoMin, expiresInMin: Math.max(1, c.activeMinutes - agoMin) }
}

function logicOf(s: SlotSummary): CardLogic {
  const l = s.logic
  if (l.state === 'ok') return { kind: 'ok', count: l.count, approx: !!l.message, message: l.message }
  if (l.state === 'pending') return { kind: 'pending', waiting: s.status !== 'connected' }
  return { kind: 'unavailable', message: l.message }
}

function connectionOf(s: SlotSummary, c: CardCtx): CardConnection {
  if (s.status === 'connected') return { kind: 'ok' }
  if (c.roomSleeping) return { kind: 'sleeping', since: s.updated_at ? hhmm(s.updated_at) : null }
  if (s.status === 'error' || s.status === 'disconnected')
    return { kind: 'error', message: connectionMessage(s, false) || statusLabel(s.status) }
  return { kind: 'connecting' }
}

export function cardState(s: SlotSummary, c: CardCtx): CardState {
  const logic = logicOf(s)
  const big = logic.kind === 'ok' ? String(logic.count) : logic.kind === 'pending' ? '··' : '—'
  return { activity: activityOf(s, c), logic, big, connection: connectionOf(s, c), goalReached: s.goal, bk: isBK(s) }
}

/** Class that colours a whole card by its state: gold once the goal is reached, red while BK (theme.css). */
export const stateClass = (s: CardState): string => (s.goalReached ? 'v2-gold' : s.bk ? 'v2-bk' : '')

export function useCardCtx(): ComputedRef<CardCtx> {
  return computed(() => ({ nowMs: tracker.nowMs, activeMinutes: tracker.activeMinutes, activity: tracker.activity, roomSleeping: tracker.roomSleeping }))
}
