export type SlotStatus = 'idle' | 'connecting' | 'connected' | 'disconnected' | 'error'
export type LogicState = 'ok' | 'unavailable' | 'pending' | 'error'

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
  logic: {
    state: LogicState
    count: number
    message: string | null
    computed_at?: number | null
    seconds?: number | null
  }
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
