<script setup lang="ts">
import { computed, onMounted, ref, watch, type ComponentPublicInstance } from 'vue'
import { useWindowVirtualizer } from '@tanstack/vue-virtual'
import { useResizeObserver } from '@vueuse/core'
import * as api from '../../../lib/api'
import type { RoomFeedCheck, RoomFeedPlayer } from '../../../lib/types'
import { tracker } from '../../../stores/tracker'
import { hhmm } from '../../lib/card'
import { CATEGORY_CLASS, groupByDay } from '../../lib/days'
import { onRoomCheck } from '../../lib/roomfeed'

const props = defineProps<{ players: RoomFeedPlayer[] }>()

const PAGE = 50
/** A catch-up window this narrow (seconds) is shown as an approximate time. */
const NARROW = 2 * 3600
const UNKNOWN_DAY = 'Heure inconnue'

const player = ref('')
const game = ref('')
const items = ref<RoomFeedCheck[]>([])
const total = ref(0)
const loaded = ref(false)
const loading = ref(false)
const error = ref('')

const playerNames = computed(() => [...new Set(props.players.map((p) => p.player))])
const games = computed(() =>
  [...new Set(props.players.flatMap((p) => p.slots.map((s) => s.game).filter((g): g is string => !!g)))].sort((a, b) => a.localeCompare(b)))

let seq = 0
async function load(reset: boolean): Promise<void> {
  const mine = ++seq
  loading.value = true
  try {
    const params: api.RoomFeedChecksParams = { limit: PAGE, offset: reset ? 0 : items.value.length }
    if (player.value) params.player = player.value
    if (game.value) params.game = game.value
    const page = await api.getRoomFeedChecks(params)
    if (mine !== seq) return
    if (reset) items.value = page.items
    else {
      const have = new Set(items.value.map((c) => c.key))
      items.value = [...items.value, ...page.items.filter((c) => !have.has(c.key))]
    }
    total.value = page.total
    loaded.value = true
    error.value = ''
  } catch (e) {
    if (mine === seq) error.value = e instanceof Error ? e.message : String(e)
  } finally {
    if (mine === seq) loading.value = false
  }
}
watch([player, game], () => void load(true), { immediate: true })

// Live checks: prepend those matching the filters, once each.
onRoomCheck((data) => {
  const incoming: RoomFeedCheck[] = Array.isArray(data?.checks) ? data.checks : []
  const have = new Set(items.value.map((c) => c.key))
  const fresh = incoming.filter((c) => {
    if (have.has(c.key)) return false
    have.add(c.key)
    return (!player.value || c.sender_player === player.value) && (!game.value || c.sender_game === game.value)
  })
  if (!fresh.length) return
  items.value = [...fresh, ...items.value]
  total.value += fresh.length
})

// A catch-up entry is dated by the middle of its window when that window is narrow; otherwise it has no time.
const narrow = (c: RoomFeedCheck): boolean => c.after !== null && c.before !== null && c.before - c.after <= NARROW
const when = (c: RoomFeedCheck): number | null => c.at ?? (narrow(c) ? (c.after! + c.before!) / 2 : null)
function time(c: RoomFeedCheck): string {
  if (c.at !== null) return hhmm(c.at)
  const t = when(c)
  return t === null ? '—' : `~${hhmm(t)}`
}
const catchup = (c: RoomFeedCheck): string =>
  c.after !== null && c.before !== null ? `rattrapé · entre ${hhmm(c.after)} et ${hhmm(c.before)}` : 'rattrapé · heure inconnue'
const target = (c: RoomFeedCheck): string => `pour ${c.receiver_player ?? c.receiver ?? '?'} · ${c.receiver_game ?? '?'}`

// One flat list (day headings + checks) so the window virtualizer only mounts the rows on screen.
type Row = { kind: 'day'; key: string; label: string; count: number } | { kind: 'check'; key: string; check: RoomFeedCheck }
const rows = computed<Row[]>(() =>
  groupByDay(items.value, when, (c) => c.sender_game ?? '', tracker.nowMs).flatMap((g) => [
    { kind: 'day' as const, key: `day:${g.key}`, label: g.key === 'before' ? UNKNOWN_DAY : g.label, count: g.rows.length },
    ...g.rows.map((r) => ({ kind: 'check' as const, key: r.entry.key, check: r.entry })),
  ]))

const listEl = ref<HTMLElement | null>(null)
const rootEl = ref<HTMLElement | null>(null)
const scrollMargin = ref(0)
const measureMargin = () => {
  if (listEl.value) scrollMargin.value = listEl.value.getBoundingClientRect().top + window.scrollY
}
// Anything above the list (the activity chart, the filters wrapping) moves it: re-measure on resize.
useResizeObserver(rootEl, measureMargin)
onMounted(measureMargin)

const virtualizer = useWindowVirtualizer<HTMLElement>(computed(() => ({
  count: rows.value.length,
  estimateSize: (i: number) => (rows.value[i]?.kind === 'day' ? 37 : 56),
  getItemKey: (i: number) => rows.value[i]?.key ?? i,
  overscan: 12,
  scrollMargin: scrollMargin.value,
})))
const visible = computed(() => virtualizer.value.getVirtualItems().map((v) => ({ v, r: rows.value[v.index] })).filter((x) => x.r))
const measure = (el: Element | ComponentPublicInstance | null) => {
  if (el instanceof HTMLElement) virtualizer.value.measureElement(el)
}

// Load the next page once the end of the loaded rows comes into view.
const hasMore = computed(() => items.value.length < total.value)
function more(): void {
  void load(false)
}
watch(() => visible.value.at(-1)?.v.index ?? -1, (last) => {
  if (last >= rows.value.length - 5 && hasMore.value && !loading.value && !error.value) more()
})

const select = 'h-9 min-w-0 max-w-full rounded-lg border bg-card px-2 text-sm text-foreground max-[699px]:h-11'
</script>

<template>
  <section ref="rootEl" class="flex min-w-0 flex-col gap-2" aria-labelledby="room-feed-title">
    <div class="flex flex-wrap items-center gap-x-4 gap-y-2">
      <h3 id="room-feed-title" class="text-base font-semibold">Fil des checks</h3>
      <label class="flex min-w-0 items-center gap-2 text-sm text-muted-foreground">
        Joueur
        <select v-model="player" :class="select">
          <option value="">tous</option>
          <option v-for="n in playerNames" :key="n" :value="n">{{ n }}</option>
        </select>
      </label>
      <label class="flex min-w-0 items-center gap-2 text-sm text-muted-foreground">
        Jeu
        <select v-model="game" :class="select">
          <option value="">tous</option>
          <option v-for="g in games" :key="g" :value="g">{{ g }}</option>
        </select>
      </label>
      <span v-if="loaded" class="font-mono text-xs text-muted-foreground">{{ total }} check{{ total > 1 ? 's' : '' }}</span>
    </div>

    <p v-if="error" role="alert" class="break-words rounded-xl bg-warn p-3 text-sm text-warn-foreground"><span class="text-error">! </span>{{ error }}</p>

    <div class="min-w-0 rounded-xl border bg-card px-4 py-3">
      <p v-if="!loaded && loading" class="text-sm text-muted-foreground">Chargement…</p>
      <p v-else-if="loaded && !total" class="text-sm text-muted-foreground">Aucun check pour ces filtres.</p>

      <ul ref="listEl" class="relative" :style="{ height: `${virtualizer.getTotalSize()}px` }">
        <li
          v-for="{ v, r } in visible" :key="r.key" :ref="measure" :data-index="v.index"
          class="absolute inset-x-0 top-0 min-w-0" :style="{ transform: `translateY(${v.start - scrollMargin}px)` }"
        >
          <h4 v-if="r.kind === 'day'" :data-day="r.label" class="border-b py-1 text-sm font-semibold" :class="v.index > 0 && 'mt-3'">
            {{ r.label }} · {{ r.count }} check{{ r.count > 1 ? 's' : '' }}
          </h4>
          <div v-else class="flex min-w-0 gap-2.5 border-b py-1.5 text-sm">
            <span class="w-12 shrink-0 font-mono text-xs text-muted-foreground tabular-nums" :data-time-none="when(r.check) === null ? '' : undefined">{{ time(r.check) }}</span>
            <div class="min-w-0 flex-1">
              <div class="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
                <span class="min-w-0 break-words font-semibold">{{ r.check.sender_player ?? r.check.sender ?? '?' }} · {{ r.check.sender_game ?? '?' }}</span>
                <span class="min-w-0 break-words font-mono text-xs">{{ r.check.location ?? '?' }}</span>
              </div>
              <div class="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
                <span v-if="r.check.category" class="rounded px-1 font-mono text-[11px]" :class="CATEGORY_CLASS[r.check.category]">{{ r.check.category }}</span>
                <span v-if="r.check.item === null" class="italic text-muted-foreground">contenu inconnu</span>
                <span v-else class="min-w-0 break-words">{{ r.check.item }}</span>
                <span v-if="r.check.mine" data-for="me" class="font-semibold text-logic">pour toi</span>
                <span v-else-if="r.check.self" class="text-muted-foreground">pour lui-même</span>
                <span v-else class="min-w-0 break-words text-muted-foreground">{{ target(r.check) }}</span>
              </div>
              <p v-if="r.check.src === 'catchup'" class="text-xs text-muted-foreground">{{ catchup(r.check) }}</p>
            </div>
          </div>
        </li>
      </ul>

      <button v-if="hasMore" type="button" class="mt-3 rounded-lg border px-3 py-1.5 text-sm hover:bg-accent disabled:opacity-50 max-[699px]:min-h-11" :disabled="loading" @click="more">{{ loading ? 'Chargement…' : 'Afficher plus' }}</button>
    </div>
  </section>
</template>
