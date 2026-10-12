export type SlotStatus = 'idle' | 'connecting' | 'connected' | 'disconnected' | 'error'
export type LogicState = 'ok' | 'unavailable' | 'pending' | 'error'

export interface GoalCounter {
  label: string
  current: number
  target: number
  /** what is counted, when the label is short */
  detail?: string
}

export interface GoalStep {
  label: string
  /** null: not visible to a tracker (an event of the game) */
  done: boolean | null
}

/** Goal of the slot and how far it is (backend goals.py); null when the game has no description yet. */
export interface Objective {
  summary: string
  counters: GoalCounter[]
  steps: GoalStep[]
  /** explanation shown once under the summary */
  note?: string
  /** where the options came from: "slot_data", "yaml" or "slot_data + yaml" */
  source: string | null
}

export interface SlotSummary {
  name: string
  game: string
  owner?: string | null
  status: SlotStatus
  error: string | null
  seed_name?: string | null
  checks: { done: number; total: number; remaining: number }
  items: { received: number; new: number }
  hints: { mine_elsewhere: number; in_my_world: number; in_my_world_in_logic: number }
  goal: boolean
  /** epoch seconds of the slot's last location check seen by the app (null = none since tracking) */
  last_check_at?: number | null
  logic: {
    state: LogicState
    count: number
    message: string | null
    computed_at?: number | null
    seconds?: number | null
  }
  objective?: Objective | null
  updated_at?: number
}

export interface ItemEntry {
  index: number
  name: string
  sender: string
  own: boolean
  origin?: 'start' | 'server' | 'own' | 'other'
  location: string
  progression: boolean
  useful: boolean
  trap: boolean
  new: boolean
  /** epoch seconds when the app received it; null = before the app tracked this slot */
  received_at?: number | null
  /** set when the item arrived while the app was not watching: between received_after and received_at */
  received_after?: number | null
}

/** Item of the dashboard feed (/api/items/recent): an item of a slot, with that slot. */
export interface RecentItem extends ItemEntry {
  slot: string
  game: string
  owner?: string | null
  received_at: number
}

export interface Hint {
  item: string
  item_id?: number
  location: string
  location_id?: number
  finder: string
  finder_game: string
  receiver: string
  receiver_game: string
  found: boolean
  entrance?: string
  status?: string
  progression: boolean
  useful: boolean
  trap: boolean
  in_logic: boolean
}

export interface LogicLocation {
  id: number
  name: string
  region?: string | null
  hint: { item: string; receiver: string; progression: boolean } | null
}

export interface SlotDetail extends SlotSummary {
  items_list: ItemEntry[]
  hints_mine_elsewhere: Hint[]
  hints_in_my_world: Hint[]
  in_logic_locations: LogicLocation[]
  players?: Record<string, { name: string; game: string }>
}

export type SseState = 'connecting' | 'open' | 'reconnecting'
