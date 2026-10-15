import { afterEach, describe, expect, it, vi } from 'vitest'
import { restoreActivity, tracker } from '../../src/stores/tracker'
import { clearUndo, dismissWithUndo, undo, undoLast, UNDO_MS } from '../../src/v2/lib/undo'
import { mk } from '../helpers'

afterEach(() => {
  clearUndo()
  vi.useRealTimers()
  tracker.activity = { pinned: null, dismissed: {} }
  tracker.slots = []
  localStorage.clear()
})

describe('Plus actif + Annuler', () => {
  it('restores the previous activity exactly and saves it', () => {
    vi.useFakeTimers()
    tracker.slots = [mk({ name: 'celeste', last_check_at: 100 })]
    tracker.activity = { pinned: { name: 'celeste', at: 50 }, dismissed: { other: 3 } }
    dismissWithUndo('celeste', 'Celeste (Open World)')
    expect(tracker.activity.pinned).toBeNull()
    expect(tracker.activity.dismissed.celeste).toBe(100)
    expect(undo.message).toBe("Celeste (Open World) n'est plus actif jusqu'à son prochain check.")
    undoLast()
    expect(tracker.activity).toEqual({ pinned: { name: 'celeste', at: 50 }, dismissed: { other: 3 } })
    expect(JSON.parse(localStorage.getItem('amt-activity')!)).toEqual(tracker.activity)
    expect(undo.message).toBe('')
  })
  it('the message disappears after 6 s', () => {
    vi.useFakeTimers()
    tracker.slots = [mk({ name: 'a', last_check_at: 1 })]
    dismissWithUndo('a', 'A')
    vi.advanceTimersByTime(UNDO_MS - 1)
    expect(undo.message).not.toBe('')
    vi.advanceTimersByTime(1)
    expect(undo.message).toBe('')
    expect(undo.prev).toBeNull()
  })
  it('restoreActivity copies its argument', () => {
    const prev = { pinned: null, dismissed: { a: 1 } }
    restoreActivity(prev)
    prev.dismissed.a = 9
    expect(tracker.activity.dismissed.a).toBe(1)
  })
})
