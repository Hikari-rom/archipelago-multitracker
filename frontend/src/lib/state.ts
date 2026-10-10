import type { SlotSummary } from './types'

export interface TrackerState {
  server: string
  slots: SlotSummary[]
  loaded: boolean
}

export type TrackerEvent =
  | { type: 'snapshot'; slots: SlotSummary[]; server?: string }
  | { type: 'slot'; slot: SlotSummary }

export function initialState(): TrackerState {
  return { server: '', slots: [], loaded: false }
}

/** Pure reducer: snapshot replaces everything, slot replaces/adds one summary. */
export function reduce(state: TrackerState, ev: TrackerEvent): TrackerState {
  if (ev.type === 'snapshot') {
    return { server: ev.server ?? state.server, slots: [...ev.slots], loaded: true }
  }
  const i = state.slots.findIndex((s) => s.name === ev.slot.name)
  const slots = [...state.slots]
  if (i >= 0) slots[i] = ev.slot
  else slots.push(ev.slot)
  return { ...state, slots, loaded: true }
}
