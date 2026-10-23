import { installMock } from '../lib/api'
import type { TrackerEvent } from '../lib/state'
import { tracker } from '../stores/tracker'
import {
  mockConfig, mockDetail, mockDiscover, mockHistory, mockRecent, mockRoomFeedActivity, mockRoomFeedChecks, mockRoomFeedStatus,
  mockRoomFeedSummary, mockSlots,
} from './fixtures'

export function installMockMode(dispatch: (e: TrackerEvent) => void): void {
  installMock({
    getSlot: async (n) => mockDetail(n),
    markSeen: async () => ({ seen: 1 }),
    recentItems: async () => ({ items: mockRecent() }),
    getConfig: async () => mockConfig,
    discover: async () => mockDiscover,
    history: async (k, s, limit, offset) => mockHistory(k, s, limit, offset),
    putConfig: async () => ({ ok: true }),
    getRoomFeed: async () => mockRoomFeedStatus(),
    getRoomFeedSummary: async () => mockRoomFeedSummary(),
    getRoomFeedChecks: async (p) => mockRoomFeedChecks(p),
    getRoomFeedActivity: async (bucket, player) => mockRoomFeedActivity(bucket, player),
  })
  tracker.sse = 'open'
  tracker.roomDashboard = true // what /api/slots would say with `room_dashboard: true`
  dispatch({ type: 'snapshot', slots: structuredClone(mockSlots), server: 'archipelago.gg:38281 (mock)' })
}
