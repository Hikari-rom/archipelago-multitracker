import type { SlotSummary } from '../src/lib/types'

export function mk(p: Partial<SlotSummary> & { name: string }): SlotSummary {
  return {
    game: 'Game ' + p.name,
    status: 'connected',
    error: null,
    checks: { done: 1, total: 10, remaining: 9 },
    items: { received: 0, new: 0 },
    hints: { mine_elsewhere: 0, in_my_world: 0, in_my_world_in_logic: 0 },
    goal: false,
    logic: { state: 'ok', count: 0, message: null },
    ...p,
  }
}

/**
 * happy-dom lays nothing out: give the scroll boxes of virtualized lists (`data-scroll-box`) the height they have in a
 * browser, so that the virtualizer mounts rows. Call once per test file (beforeAll).
 */
export function stubScrollBoxes(height = 640): void {
  const base = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetHeight')!
  Object.defineProperty(HTMLElement.prototype, 'offsetHeight', {
    configurable: true,
    get(this: HTMLElement) { return this.hasAttribute('data-scroll-box') ? height : base.get!.call(this) },
  })
}
