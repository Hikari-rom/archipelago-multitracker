// Helpers shared by the room page components.
import type { RoomFeedPlayer, RoomPresence } from '../../lib/types'

export type BoardSort = 'pct' | 'checks'

/** Completion ratio in [0, 1]; 0 when there is nothing to do. */
export const ratio = (done: number, total: number): number => (total > 0 ? done / total : 0)
/** Whole percent, for display. */
export const pct = (done: number, total: number): number => Math.round(ratio(done, total) * 100)

export const PRESENCE_LABEL: Record<RoomPresence, string> = {
  playing: 'En jeu',
  connected: 'Connecté',
  offline: 'Hors ligne',
  unknown: 'Inconnu',
}

/** Leaderboard order: by % (ties: more checks) or by number of checks (ties: higher %); then by name. */
export function sortPlayers(players: RoomFeedPlayer[], by: BoardSort): RoomFeedPlayer[] {
  const key = (p: RoomFeedPlayer) => (by === 'pct' ? [ratio(p.done, p.total), p.done] : [p.done, ratio(p.done, p.total)])
  return [...players].sort((a, b) => {
    const [a1, a2] = key(a)
    const [b1, b2] = key(b)
    return b1 - a1 || b2 - a2 || a.player.localeCompare(b.player)
  })
}
