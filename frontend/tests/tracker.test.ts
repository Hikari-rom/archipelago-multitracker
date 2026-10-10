import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from '../src/lib/api'
import { connect, loadDetail, markSeen, stop, tracker } from '../src/stores/tracker'
import { mk } from './helpers'

class FakeES {
  static CLOSED = 2
  static instances: FakeES[] = []
  readyState = 0
  onopen: (() => void) | null = null
  onerror: (() => void) | null = null
  closed = false
  constructor(public url: string) {
    FakeES.instances.push(this)
  }
  addEventListener() {}
  close() {
    this.closed = true
    this.readyState = 2
  }
}

describe('SSE reconnect', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    FakeES.instances = []
    vi.stubGlobal('EventSource', FakeES)
  })
  afterEach(() => {
    stop()
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })
  it('reconnects with doubling backoff after CLOSED, resets on open', () => {
    connect()
    const first = FakeES.instances[0]
    first.readyState = 2
    first.onerror!()
    expect(first.closed).toBe(true)
    expect(tracker.sse).toBe('reconnecting')
    vi.advanceTimersByTime(2999)
    expect(FakeES.instances).toHaveLength(1)
    vi.advanceTimersByTime(1)
    expect(FakeES.instances).toHaveLength(2)
    FakeES.instances[1].readyState = 2
    FakeES.instances[1].onerror!()
    vi.advanceTimersByTime(5999)
    expect(FakeES.instances).toHaveLength(2)
    vi.advanceTimersByTime(1)
    expect(FakeES.instances).toHaveLength(3)
    FakeES.instances[2].onopen!()
    expect(tracker.sse).toBe('open')
    FakeES.instances[2].readyState = 2
    FakeES.instances[2].onerror!()
    vi.advanceTimersByTime(3000)
    expect(FakeES.instances).toHaveLength(4)
  })
  it('does not reconnect manually when the browser is retrying (CONNECTING)', () => {
    connect()
    FakeES.instances[0].readyState = 0
    FakeES.instances[0].onerror!()
    vi.advanceTimersByTime(60000)
    expect(FakeES.instances).toHaveLength(1)
  })
})

describe('detail race', () => {
  afterEach(() => vi.restoreAllMocks())
  it('drops stale responses', async () => {
    tracker.slots = [mk({ name: 'a' })]
    const resolvers: ((v: any) => void)[] = []
    vi.spyOn(api, 'getSlot').mockImplementation(() => new Promise((r) => resolvers.push(r)))
    const p1 = loadDetail('a')
    const p2 = loadDetail('a')
    resolvers[1]({ ...mk({ name: 'a' }), items_list: [], tag: 'new' })
    await p2
    resolvers[0]({ ...mk({ name: 'a' }), items_list: [], tag: 'old' })
    await p1
    expect((tracker.details.a as any).tag).toBe('new')
  })
  it('ignores a detail request started before markSeen resolved', async () => {
    tracker.slots = [mk({ name: 'b', items: { received: 1, new: 1 } })]
    tracker.open.b = true
    let resolveOld!: (v: any) => void
    const spy = vi.spyOn(api, 'getSlot').mockImplementationOnce(() => new Promise((r) => (resolveOld = r)))
    vi.spyOn(api, 'markSeen').mockResolvedValue({ seen: 1 })
    const old = loadDetail('b')
    spy.mockResolvedValueOnce({ ...mk({ name: 'b' }), items_list: [], tag: 'fresh' } as any)
    await markSeen('b')
    await vi.waitFor(() => expect((tracker.details.b as any)?.tag).toBe('fresh'))
    resolveOld({ ...mk({ name: 'b' }), items_list: [], tag: 'stale' })
    await old
    expect((tracker.details.b as any).tag).toBe('fresh')
  })
})
