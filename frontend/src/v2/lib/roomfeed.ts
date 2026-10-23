// Room-wide dashboard: status + summary kept fresh from the `roomfeed` SSE events, and a hook on `roomfeed_check`.
// The SSE listeners live in stores/tracker.ts (v1 code must not import v2): this file registers into them.
import { onBeforeUnmount, onMounted, ref } from 'vue'
import * as api from '../../lib/api'
import type { RoomFeedStatus, RoomFeedSummary } from '../../lib/types'
import { roomfeedListeners } from '../../stores/tracker'

export const REFRESH_DEBOUNCE_MS = 1000

/** Status and summary of the room feed: fetched on mount and (debounced) after every `roomfeed` event. */
export function useRoomFeed() {
  const status = ref<RoomFeedStatus | null>(null)
  const summary = ref<RoomFeedSummary | null>(null)
  const loading = ref(false)
  const error = ref('')

  let seq = 0
  async function refresh(): Promise<void> {
    const mine = ++seq
    loading.value = true
    try {
      const st = await api.getRoomFeed()
      const sm = st.enabled ? await api.getRoomFeedSummary() : null
      if (mine !== seq) return
      status.value = st
      summary.value = sm
      error.value = ''
    } catch (e) {
      if (mine === seq) error.value = e instanceof Error ? e.message : String(e)
    } finally {
      if (mine === seq) loading.value = false
    }
  }

  let timer: ReturnType<typeof setTimeout> | undefined
  const onState = (): void => {
    clearTimeout(timer)
    timer = setTimeout(() => void refresh(), REFRESH_DEBOUNCE_MS)
  }
  onMounted(() => {
    roomfeedListeners.state.add(onState)
    void refresh()
  })
  onBeforeUnmount(() => {
    roomfeedListeners.state.delete(onState)
    clearTimeout(timer)
    seq++ // drop in-flight answers
  })

  return { status, summary, loading, error, refresh }
}

/** Call `fn` with each `roomfeed_check` SSE payload (`{type, checks}`) while the component is mounted. */
export function onRoomCheck(fn: (data: any) => void): void {
  onMounted(() => roomfeedListeners.check.add(fn))
  onBeforeUnmount(() => roomfeedListeners.check.delete(fn))
}
