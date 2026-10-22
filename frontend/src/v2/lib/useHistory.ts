// Logic of the History page (copied from the v1 HistoryView so that the v1 file stays untouched).
import { computed, onBeforeUnmount, ref, watch, type Ref } from 'vue'
import * as api from '../../lib/api'
import type { HistoryPage, HistorySlot, ReceivedEntry, SentCheck, SlotSummary } from '../../lib/types'

export const PAGE = 50

export function useHistory(slots: () => SlotSummary[], kind: Ref<'sent' | 'received'>, slotFilter: Ref<string>) {
  const sent = ref<HistoryPage<SentCheck> | null>(null)
  const received = ref<HistoryPage<ReceivedEntry> | null>(null)
  const limit = ref(PAGE)
  const error = ref('')
  const loading = ref(false)

  const names = computed(() => slots().map((s) => s.name))
  const wanted = computed(() => (slotFilter.value && names.value.includes(slotFilter.value) ? [slotFilter.value] : names.value))
  const page = computed(() => (kind.value === 'sent' ? sent.value : received.value))
  const perSlot = computed<HistorySlot[]>(() => {
    const keep = new Set(names.value)
    return (page.value?.slots ?? []).filter((s) => keep.has(s.name))
  })
  const totals = computed(() =>
    perSlot.value.reduce(
      (t, s) => ({ done: t.done + s.checks.done, toOthers: t.toOthers + s.sent.to_others, received: t.received + s.received }),
      { done: 0, toOthers: 0, received: 0 },
    ),
  )

  let seq = 0
  async function load(): Promise<void> {
    const mine = ++seq
    loading.value = true
    try {
      const k = kind.value
      const r = await (k === 'sent'
        ? api.getHistory('sent', wanted.value, limit.value, 0)
        : api.getHistory('received', wanted.value, limit.value, 0))
      if (mine !== seq) return
      if (k === 'sent') sent.value = r as HistoryPage<SentCheck>
      else received.value = r as HistoryPage<ReceivedEntry>
      error.value = ''
    } catch (e) {
      if (mine === seq) error.value = e instanceof Error ? e.message : String(e)
    } finally {
      if (mine === seq) loading.value = false
    }
  }

  function more(): void {
    limit.value += PAGE
    void load()
  }

  watch([kind, () => wanted.value.join('\n')], () => {
    limit.value = PAGE
    void load()
  }, { immediate: true })

  const signature = computed(() => slots().map((s) => `${s.checks.done}/${s.items.received}/${s.sent?.known ?? 0}`).join(','))
  let timer: ReturnType<typeof setTimeout> | undefined
  watch(signature, () => {
    clearTimeout(timer)
    timer = setTimeout(() => void load(), 1500)
  })
  onBeforeUnmount(() => clearTimeout(timer))

  return { sent, received, perSlot, totals, loading, error, more, PAGE }
}
