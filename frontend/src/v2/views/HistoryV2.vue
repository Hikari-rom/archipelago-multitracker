<script setup lang="ts">
import { computed, onMounted, ref, watch, type ComponentPublicInstance } from 'vue'
import { useWindowVirtualizer } from '@tanstack/vue-virtual'
import { useResizeObserver } from '@vueuse/core'
import { tracker } from '../../stores/tracker'
import type { ReceivedEntry, SentCheck, SlotSummary } from '../../lib/types'
import { sentText } from '../../lib/history'
import OwnerSelect from '../components/OwnerSelect.vue'
import { hhmm } from '../lib/card'
import { CATEGORY_CLASS as badgeClass, category, groupByDay, itemOrigin, type DayGroup, type DayRow } from '../lib/days'
import { historyTab } from '../lib/nav'
import { PAGE, useHistory } from '../lib/useHistory'

const props = defineProps<{ slots: SlotSummary[]; owner: string; chips: { key: string; label: string }[] }>()
defineEmits<{ 'update:owner': [key: string] }>()

const slotFilter = ref('')
const { sent, received, perSlot, totals, loading, error, more } = useHistory(() => props.slots, historyTab, slotFilter)
const page = computed(() => (historyTab.value === 'sent' ? sent.value : received.value))

// groupByDay expects newest first: sort copies, entries without a time go last (stable).
const newestFirst = <T,>(items: T[], at: (e: T) => number | null): T[] =>
  [...items].sort((a, b) => (at(b) ?? -Infinity) - (at(a) ?? -Infinity))
const sentAt = (c: { checked_at: number | null }) => c.checked_at
const receivedAt = (i: { received_at?: number | null }) => i.received_at ?? null
const sentGroups = computed(() =>
  groupByDay(newestFirst(sent.value?.items ?? [], sentAt), sentAt, (c) => c.game, tracker.nowMs))
const receivedGroups = computed(() =>
  groupByDay(newestFirst(received.value?.items ?? [], receivedAt), receivedAt, (i) => i.game, tracker.nowMs))

const time = (t: number | null | undefined) => (t == null ? '—' : hhmm(t))

// One flat list (day headings + entries) so the window virtualizer only mounts the rows on screen.
type Row =
  | { kind: 'day'; key: string; label: string; count: number }
  | { kind: 'sent'; key: string; row: DayRow<SentCheck> }
  | { kind: 'received'; key: string; row: DayRow<ReceivedEntry> }
function flatten<T>(groups: DayGroup<T>[], wrap: (r: DayRow<T>) => Row): Row[] {
  return groups.flatMap((g) => [{ kind: 'day' as const, key: `day:${g.key}`, label: g.label, count: g.rows.length }, ...g.rows.map(wrap)])
}
const rows = computed<Row[]>(() =>
  historyTab.value === 'sent'
    ? flatten(sentGroups.value, (row) => ({ kind: 'sent', key: `${row.entry.slot}:${row.entry.location_id}`, row }))
    : flatten(receivedGroups.value, (row) => ({ kind: 'received', key: `${row.entry.slot}:${row.entry.index}`, row })))

const listEl = ref<HTMLElement | null>(null)
const rootEl = ref<HTMLElement | null>(null)
const scrollMargin = ref(0)
const measureMargin = () => {
  if (listEl.value) scrollMargin.value = listEl.value.getBoundingClientRect().top + window.scrollY
}
// Anything above the list (per-game table on narrow screens, notices) moves it: re-measure on resize.
useResizeObserver(rootEl, measureMargin)
onMounted(measureMargin)

const virtualizer = useWindowVirtualizer<HTMLElement>(computed(() => ({
  count: rows.value.length,
  estimateSize: (i: number) => (rows.value[i]?.kind === 'day' ? 37 : 33),
  getItemKey: (i: number) => rows.value[i]?.key ?? i,
  overscan: 12,
  scrollMargin: scrollMargin.value,
})))
const visible = computed(() => virtualizer.value.getVirtualItems().map((v) => ({ v, r: rows.value[v.index] })).filter((x) => x.r))
const measure = (el: Element | ComponentPublicInstance | null) => {
  if (el instanceof HTMLElement) virtualizer.value.measureElement(el)
}

// Load the next page once the end of the loaded rows comes into view.
const hasMore = computed(() => !!page.value && page.value.items.length < page.value.total)
watch(() => visible.value.at(-1)?.v.index ?? -1, (last) => {
  if (last >= rows.value.length - 5 && hasMore.value && !loading.value && !error.value) more()
})

const tabs = computed(() => [
  { key: 'sent' as const, label: `Checks envoyés${sent.value ? ` · ${sent.value.total}` : ''}` },
  { key: 'received' as const, label: `Items reçus${received.value ? ` · ${received.value.total}` : ''}` },
])
</script>

<template>
  <section ref="rootEl" class="flex flex-col gap-4" aria-labelledby="history-title">
    <div class="flex flex-wrap items-center gap-x-4 gap-y-2">
      <h2 id="history-title" class="text-lg font-semibold">Historique</h2>
      <div role="tablist" aria-label="Type d'historique" class="flex gap-1 border-b">
        <button
          v-for="t in tabs" :key="t.key" type="button" role="tab" :aria-selected="historyTab === t.key"
          class="border-b-2 px-3 py-1.5 text-sm max-[699px]:min-h-11"
          :class="historyTab === t.key ? 'border-logic font-semibold' : 'border-transparent text-muted-foreground hover:text-foreground'"
          @click="historyTab = t.key"
        >{{ t.label }}</button>
      </div>
      <label class="flex items-center gap-2 text-sm text-muted-foreground">
        Jeu
        <select v-model="slotFilter" class="h-9 rounded-lg border bg-card px-2 text-sm text-foreground max-[699px]:h-11">
          <option value="">tous ({{ slots.length }})</option>
          <option v-for="s in slots" :key="s.name" :value="s.name">{{ s.game }}</option>
        </select>
      </label>
      <OwnerSelect :model-value="owner" :chips="chips" @update:model-value="(k: string) => $emit('update:owner', k)" />
      <span class="font-mono text-xs text-muted-foreground">du plus récent au plus ancien · pages de {{ PAGE }}</span>
    </div>

    <p v-if="error" role="alert" class="rounded-xl bg-warn p-3 text-sm text-warn-foreground"><span class="text-error">! </span>{{ error }}</p>
    <p v-if="historyTab === 'sent' && page && page.scout_checked === false" class="text-sm text-muted-foreground">
      Le contenu des checks faits n'est pas demandé au serveur (Configuration).
    </p>

    <div class="grid gap-4 min-[1100px]:grid-cols-[400px_1fr]">
      <div>
        <table data-history-table class="hidden w-full rounded-xl border bg-card text-sm min-[700px]:table">
          <thead class="text-left text-xs text-muted-foreground">
            <tr class="border-b">
              <th scope="col" class="px-3 py-2 font-medium">Jeu · clic = filtrer</th>
              <th scope="col" class="px-2 py-2 text-right font-medium">Faits</th>
              <th scope="col" class="px-2 py-2 text-right font-medium">Envoyés</th>
              <th scope="col" class="px-2 py-2 text-right font-medium">Reçus</th>
            </tr>
          </thead>
          <tbody class="divide-y">
            <tr v-for="s in perSlot" :key="s.name" :class="slotFilter === s.name && 'bg-accent'">
              <th scope="row" class="px-3 py-1.5 text-left font-normal">
                <button type="button" class="text-left hover:underline" :aria-pressed="slotFilter === s.name" @click="slotFilter = slotFilter === s.name ? '' : s.name">{{ s.game }}</button>
              </th>
              <td class="whitespace-nowrap px-2 py-1.5 text-right font-mono tabular-nums">{{ s.checks.done }} / {{ s.checks.total }}</td>
              <td class="whitespace-nowrap px-2 py-1.5 text-right font-mono tabular-nums">
                {{ s.sent.to_others }}<span v-if="s.checks.done - s.sent.known > 0" class="text-muted-foreground" :title="sentText(s)"> +{{ s.checks.done - s.sent.known }} ?</span>
              </td>
              <td class="whitespace-nowrap px-2 py-1.5 text-right font-mono tabular-nums">{{ s.received }}</td>
            </tr>
          </tbody>
          <tfoot class="border-t font-semibold">
            <tr>
              <th scope="row" class="px-3 py-1.5 text-left">Total</th>
              <td class="whitespace-nowrap px-2 py-1.5 text-right font-mono tabular-nums">{{ totals.done }}</td>
              <td class="whitespace-nowrap px-2 py-1.5 text-right font-mono tabular-nums">{{ totals.toOthers }}</td>
              <td class="whitespace-nowrap px-2 py-1.5 text-right font-mono tabular-nums">{{ totals.received }}</td>
            </tr>
          </tfoot>
        </table>
        <p class="hidden px-3 py-2 text-xs text-muted-foreground min-[700px]:block">« +N ? » : checks au contenu inconnu</p>
        <details class="rounded-xl border bg-card p-3 text-sm min-[700px]:hidden">
          <summary class="flex min-h-11 cursor-pointer items-center">Par jeu ▾</summary>
          <ul class="mt-2 divide-y">
            <li v-for="s in perSlot" :key="s.name" class="flex flex-wrap justify-between gap-x-3 py-1.5">
              <span>{{ s.game }}</span>
              <span class="font-mono text-xs text-muted-foreground">{{ s.checks.done }} / {{ s.checks.total }} · {{ sentText(s) }} · {{ s.received }}</span>
            </li>
          </ul>
        </details>
      </div>

      <div class="rounded-xl border bg-card px-4 py-3">
        <p class="mb-2 flex flex-wrap gap-x-4 font-mono text-xs text-muted-foreground">
          <span><span class="rounded px-1" :class="badgeClass.PROG">PROG</span> progression</span>
          <span><span class="rounded px-1" :class="badgeClass.UTILE">UTILE</span> utile</span>
          <span><span class="rounded px-1" :class="badgeClass.PIÈGE">PIÈGE</span> piège</span>
          <span>sans étiquette = normal</span>
        </p>
        <p v-if="!page && loading" class="text-sm text-muted-foreground">Chargement…</p>
        <p v-else-if="page && !page.total" class="text-sm text-muted-foreground">{{ historyTab === 'sent' ? 'Aucun check fait.' : 'Aucun item reçu.' }}</p>

        <ul ref="listEl" class="relative" :style="{ height: `${virtualizer.getTotalSize()}px` }">
          <li
            v-for="{ v, r } in visible" :key="r.key" :ref="measure" :data-index="v.index"
            class="absolute inset-x-0 top-0" :style="{ transform: `translateY(${v.start - scrollMargin}px)` }"
          >
            <h3 v-if="r.kind === 'day'" :data-day="r.label" class="border-b py-1 text-sm font-semibold" :class="v.index > 0 && 'mt-3'">
              {{ r.label }} · {{ r.count }} {{ historyTab === 'sent' ? 'check' : 'item' }}{{ r.count > 1 ? 's' : '' }}
            </h3>
            <div v-else-if="r.kind === 'sent'" class="flex flex-wrap items-baseline gap-x-2.5 gap-y-0.5 border-b py-1.5 text-sm">
              <span class="w-12 font-mono text-xs text-muted-foreground tabular-nums">{{ time(r.row.entry.checked_at) }}</span>
              <span v-if="r.row.showSource" class="font-semibold">{{ r.row.entry.game }}</span>
              <span class="font-mono text-xs">{{ r.row.entry.location }}</span>
              <span v-if="r.row.entry.item == null" class="italic text-muted-foreground">contenu inconnu</span>
              <template v-else>
                <span v-if="category(r.row.entry)" class="rounded px-1 font-mono text-[11px]" :class="badgeClass[category(r.row.entry)!]">{{ category(r.row.entry) }}</span>
                <span>{{ r.row.entry.item }}</span>
                <span class="text-muted-foreground">{{ r.row.entry.to_self ? 'pour moi' : `pour ${r.row.entry.receiver} · ${r.row.entry.receiver_game}` }}</span>
              </template>
            </div>
            <div v-else class="flex flex-wrap items-baseline gap-x-2.5 gap-y-0.5 border-b py-1.5 text-sm">
              <span class="w-12 font-mono text-xs text-muted-foreground tabular-nums">{{ time(r.row.entry.received_at) }}</span>
              <span v-if="category(r.row.entry)" class="rounded px-1 font-mono text-[11px]" :class="badgeClass[category(r.row.entry)!]">{{ category(r.row.entry) }}</span>
              <span>{{ r.row.entry.name }}</span>
              <span v-if="r.row.showSource" class="text-muted-foreground">pour <span class="font-semibold text-foreground">{{ r.row.entry.game }}</span></span>
              <span class="text-muted-foreground">{{ itemOrigin(r.row.entry) }}</span>
            </div>
          </li>
        </ul>

        <button v-if="hasMore" type="button" class="mt-3 rounded-lg border px-3 py-1.5 text-sm hover:bg-accent disabled:opacity-50 max-[699px]:min-h-11" :disabled="loading" @click="more">{{ loading ? 'Chargement…' : 'Afficher plus' }}</button>
      </div>
    </div>
  </section>
</template>
