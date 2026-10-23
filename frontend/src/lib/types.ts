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
  /** checks whose content is known (scouted, or received by a tracked slot), and those sent to another player */
  sent?: { known: number; to_others: number }
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

/** A check made by a slot (History page, "Envoyés"). */
export interface SentCheck {
  slot: string
  game: string
  owner?: string | null
  location_id: number
  location: string
  /** epoch seconds when the app saw it checked; null = before the app recorded check times */
  checked_at: number | null
  /** set when only a range is known: checked between checked_after and checked_at */
  checked_after: number | null
  /** null: what it held is not known (not scouted, and not received by a tracked slot) */
  item: string | null
  receiver: string | null
  receiver_game: string | null
  to_self: boolean | null
  progression: boolean
  useful: boolean
  trap: boolean
}

/** An item received by a slot (History page, "Reçus"). */
export interface ReceivedEntry extends ItemEntry {
  slot: string
  game: string
  owner?: string | null
}

export interface HistorySlot {
  name: string
  game: string
  owner?: string | null
  checks: { done: number; total: number }
  sent: { known: number; to_others: number }
  received: number
}

export interface HistoryPage<T> {
  kind: 'sent' | 'received'
  total: number
  offset: number
  items: T[]
  slots: HistorySlot[]
  scout_checked: boolean
}

/** GET /api/roomfeed: state of the room-wide listener (docs/API.md, « Tableau de bord de la room complète »). */
export type RoomFeedState = 'starting' | 'listening' | 'disconnected' | 'error'
export interface RoomFeedStatus {
  /** false: the dashboard is disabled, nothing else is sent */
  enabled: boolean
  state?: RoomFeedState
  error?: string | null
  seed?: string | null
  /** epoch seconds */
  listening_since?: number | null
  last_poll_at?: number | null
  poll_error?: string | null
  /** the room publishes a tracker id: catch-up is possible */
  catchup_available?: boolean
  unreadable_lines?: number
  dir?: string | null
  write_error?: string | null
}

export type RoomPresence = 'playing' | 'connected' | 'offline' | 'unknown'

export interface RoomFeedSlot {
  name: string | null
  game: string | null
  done: number
  total: number
  goal: boolean
  presence: RoomPresence
  last_check_at: number | null
  /** last check seen live for this slot (epoch seconds); catch-up entries do not count */
  active_at: number | null
  /** BK slot; null for the slots the app does not track */
  bk: boolean | null
}

export interface RoomFeedPlayer {
  player: string
  /** a slot of this player is tracked by the app */
  me: boolean
  done: number
  total: number
  goals: number
  playing: number
  last_check_at: number | null
  slots: RoomFeedSlot[]
}

/** GET /api/roomfeed/summary */
export interface RoomFeedSummary {
  room: { done: number; total: number; slots: number; goals: number; playing: number }
  players: RoomFeedPlayer[]
}

/** A check done in the room (GET /api/roomfeed/checks items, SSE `roomfeed_check` payload). Names, never ids. */
export interface RoomFeedCheck {
  /** `<sender slot>:<location>`, unique */
  key: string
  /** exact time (live checks); null for catch-up entries */
  at: number | null
  /** catch-up entries: done between `after` and `before` */
  after: number | null
  before: number | null
  src: 'live' | 'catchup'
  sender: string | null
  sender_game: string | null
  sender_player: string | null
  receiver: string | null
  receiver_game: string | null
  receiver_player: string | null
  item: string | null
  location: string | null
  category: 'PROG' | 'UTILE' | 'PIÈGE' | null
  /** the item is for a slot tracked by the app */
  mine: boolean
  /** the slot sent the item to itself */
  self: boolean
}

export interface RoomFeedChecksPage {
  total: number
  offset: number
  items: RoomFeedCheck[]
}

export interface RoomFeedBucket {
  /** epoch seconds, local-time boundary */
  start: number
  count: number
  by_player: Record<string, number>
}

/** GET /api/roomfeed/activity */
export interface RoomFeedActivity {
  bucket: 'hour' | 'day'
  buckets: RoomFeedBucket[]
  /** catch-up checks whose interval is too wide to be dated */
  undated: number
}
