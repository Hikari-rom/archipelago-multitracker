import type { RecentItem, SlotDetail, SlotSummary } from '../../src/lib/types'
import type { CardCtx } from '../../src/v2/lib/card'
import { tracker } from '../../src/stores/tracker'
import { mk } from '../helpers'

export const NOW = 1_800_000_000_000

export const ctx: CardCtx = { nowMs: NOW, activeMinutes: 30, activity: { pinned: null, dismissed: {} }, roomSleeping: false }

export const rich = (over: Partial<SlotSummary> = {}): SlotSummary =>
  mk({
    name: 'romain_tww',
    game: 'The Wind Waker',
    checks: { done: 4, total: 10, remaining: 6 },
    items: { received: 5, new: 2 },
    hints: { mine_elsewhere: 0, in_my_world: 1, in_my_world_in_logic: 1 },
    logic: { state: 'ok', count: 3, message: null },
    go_mode: true,
    last_check_at: NOW / 1000 - 300,
    ...over,
  })

const detail = (s: SlotSummary): SlotDetail => ({
  ...s,
  items_list: [],
  hints_mine_elsewhere: [],
  hints_in_my_world: [],
  in_logic_locations: [
    { id: 1, name: 'Windfall chest', region: 'Windfall', hint: null },
    { id: 2, name: 'Great Sea chest', region: 'Great Sea', hint: null },
  ],
})

export const recentItem: RecentItem = {
  index: 1, name: 'Hookshot', sender: 'kuro', own: false, location: 'Somewhere', progression: true, useful: false,
  trap: false, new: true, slot: 'romain_tww', game: 'The Wind Waker', received_at: NOW / 1000 - 60,
}

export function prime(): void {
  tracker.nowMs = NOW
  tracker.activeMinutes = 30
  tracker.activity = { pinned: null, dismissed: {} }
  tracker.ticker = 'off'
  tracker.details = { romain_tww: detail(rich()) }
  tracker.recent = [recentItem]
}

export function reset(): void {
  tracker.details = {}
  tracker.recent = []
  tracker.ticker = 'off'
}
