import { installMock } from '../lib/api'
import type { TrackerEvent } from '../lib/state'
import { tracker } from '../stores/tracker'
import { mockConfig, mockDetail, mockDiscover, mockSlots } from './fixtures'

export function installMockMode(dispatch: (e: TrackerEvent) => void): void {
  installMock({
    getSlot: async (n) => mockDetail(n),
    markSeen: async () => ({ seen: 1 }),
    getConfig: async () => mockConfig,
    discover: async () => mockDiscover,
    putConfig: async () => ({ ok: true }),
  })
  tracker.sse = 'open'
  dispatch({ type: 'snapshot', slots: structuredClone(mockSlots), server: 'archipelago.gg:38281 (mock)' })
}
