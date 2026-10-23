<script setup lang="ts">
import { computed, ref, watch, type ComponentPublicInstance } from 'vue'
import { useVirtualizer } from '@tanstack/vue-virtual'
import * as api from '../../../lib/api'
import type { RoomFeedCheck, RoomFeedPlayer } from '../../../lib/types'
import { tracker } from '../../../stores/tracker'
import { hhmm } from '../../lib/card'
import { MONTHS } from '../../../lib/history'
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
// The list scrolls inside a box of fixed height: the page stays short however many checks the room has.
const scrollEl = ref<HTMLElement | null>(null)

const playerNames = computed(() => [...new Set(props.players.map((p) => p.player))])
const games = computed(() =>
  [...new Set(props.players.flatMap((p) => p.slots.map((s) => s.game).filter((g): g is string => !!g)))].sort((a, b) => a.localeCompare(b)))

// Server order (feed.py `checks`): newest first by `at ?? before ?? recorded_at`, ties: the most recently logged first.
// The recording time of a live check is "now".
const sortKey = (c: RoomFeedCheck): number | null => c.at ?? c.before
const matches = (c: RoomFeedCheck): boolean =>
  (!player.value || c.sender_player === player.value) && (!game.value || c.sender_game === game.value)

/**
 * Insert the rows whose key is new at their place in the server order; returns how many were added.
 * Rows of a server page older than everything loaded are appended. A live row older than everything loaded belongs to
 * a page not loaded yet when the server has `unloaded` rows beyond the loaded ones: it is left to that page.
 * Ties (same time, e.g. a history import stamped with its poll time) follow the server: rows of a later page were logged
 * before the loaded ones and go after them; rows of the first page (resync) or live ones were logged after and go before.
 */
function merge(incoming: RoomFeedCheck[], mode: 'live' | 'page' | 'resync', unloaded = 0): number {
  const have = new Set(items.value.map((c) => c.key))
  const next = [...items.value]
  let added = 0
  // A resync page is in server order: walk it backwards so that tied rows inserted "before" keep that order.
  for (const c of mode === 'resync' ? [...incoming].reverse() : incoming) {
    if (have.has(c.key)) continue
    have.add(c.key)
    if (!matches(c)) continue
    const key = sortKey(c) ?? Date.now() / 1000
    // Rows without a known key (undated catch-up) cannot be compared: skip over them.
    let at = next.findIndex((x) => {
      const k = sortKey(x)
      return k !== null && (mode === 'page' ? k < key : k <= key)
    })
    if (at < 0) {
      if (mode === 'live' && unloaded > 0) continue
      at = next.length
    }
    next.splice(at, 0, c)
    added++
  }
  if (added) items.value = next
  return added
}

const filterParams = (offset: number): api.RoomFeedChecksParams => {
  const params: api.RoomFeedChecksParams = { limit: PAGE, offset }
  if (player.value) params.player = player.value
  if (game.value) params.game = game.value
  return params
}

let seq = 0
let generation = 0 // bumped by every filter change: answers of an older generation are dropped
// Server cursor of the paging: how many rows of the server list were requested so far. It only moves forward with what
// the server returned, so rows inserted locally (live) cannot make the next page a list of duplicates.
const nextOffset = ref(0)

/** Fetch a page; returns the number of rows added, or null when the answer is stale or failed. */
async function load(reset: boolean): Promise<number | null> {
  const mine = ++seq
  if (reset) generation++
  loading.value = true
  try {
    const page = await api.getRoomFeedChecks(filterParams(reset ? 0 : nextOffset.value))
    if (mine !== seq) return null
    let added: number
    if (reset) {
      items.value = page.items
      added = page.items.length
      nextOffset.value = page.items.length
    } else {
      added = merge(page.items, 'page')
      // An empty page cannot move the cursor: the server has nothing more at this offset.
      nextOffset.value = page.items.length ? nextOffset.value + page.items.length : Math.max(nextOffset.value, page.total)
    }
    total.value = page.total
    loaded.value = true
    error.value = ''
    return added
  } catch (e) {
    if (mine === seq) {
      error.value = e instanceof Error ? e.message : String(e)
      if (reset) {
        // Do not leave the rows of the previous filters next to the error.
        items.value = []
        total.value = 0
        nextOffset.value = 0
        loaded.value = true
      }
    }
    return null
  } finally {
    if (mine === seq) loading.value = false
  }
}
watch([player, game], () => {
  if (scrollEl.value) scrollEl.value.scrollTop = 0
  void load(true)
}, { immediate: true })

// Live checks (catch-up entries too): insert those matching the filters, once each, at their place in that order.
onRoomCheck((data) => {
  const incoming: RoomFeedCheck[] = Array.isArray(data?.checks) ? data.checks : []
  const have = new Set(items.value.map((c) => c.key))
  let counted = 0
  for (const c of incoming) {
    if (have.has(c.key) || !matches(c)) continue
    have.add(c.key)
    // Server rows not loaded yet, this one aside: the total plus the rows counted earlier in this batch.
    merge([c], 'live', total.value + counted - items.value.length)
    counted++
  }
  total.value += counted
})

// Pushes are best effort (a stream reconnection, a history import, a gap): fetch the first page again and merge what is
// new. Run when the summary was refreshed (after each `roomfeed` event) and when the event stream reopens.
let syncing = 0
async function resync(): Promise<void> {
  if (!loaded.value) return // the first load is still on its way
  const mine = ++syncing
  const gen = generation
  try {
    const page = await api.getRoomFeedChecks(filterParams(0))
    if (mine !== syncing || gen !== generation) return
    merge(page.items, 'resync')
    nextOffset.value = Math.max(nextOffset.value, page.items.length)
    total.value = Math.max(page.total, items.value.length)
    error.value = ''
  } catch {
    // Silent: the rows on screen are still right, and the header shows the connection state.
  }
}
watch(() => props.players, () => void resync())
watch(() => tracker.sse, (now, prev) => {
  if (now === 'open' && prev !== 'open') void resync()
})

// A catch-up entry is dated by the middle of its window when that window is narrow; otherwise it has no time.
const narrow = (c: RoomFeedCheck): boolean => c.after !== null && c.before !== null && c.before - c.after <= NARROW
const when = (c: RoomFeedCheck): number | null => c.at ?? (narrow(c) ? (c.after! + c.before!) / 2 : null)
function time(c: RoomFeedCheck): string {
  if (c.at !== null) return hhmm(c.at)
  const t = when(c)
  return t === null ? '—' : `~${hhmm(t)}`
}
const sameDay = (a: number, b: number): boolean => new Date(a * 1000).toDateString() === new Date(b * 1000).toDateString()
const dayAndTime = (t: number): string => `${new Date(t * 1000).getDate()} ${MONTHS[new Date(t * 1000).getMonth()]} ${hhmm(t)}`
function catchup(c: RoomFeedCheck): string {
  if (c.after === null || c.before === null) return 'rattrapé · heure inconnue'
  if (sameDay(c.after, c.before)) return `rattrapé · entre ${hhmm(c.after)} et ${hhmm(c.before)}`
  // Over midnight: the start gets its date; the end too unless it is the next day.
  const nextDay = new Date(c.after * 1000)
  nextDay.setDate(nextDay.getDate() + 1)
  const end = sameDay(nextDay.getTime() / 1000, c.before) ? hhmm(c.before) : dayAndTime(c.before)
  return `rattrapé · entre ${dayAndTime(c.after)} et ${end}`
}
const target = (c: RoomFeedCheck): string => `pour ${c.receiver_player ?? c.receiver ?? '?'} · ${c.receiver_game ?? '?'}`

// One flat list (day headings + checks) so the window virtualizer only mounts the rows on screen.
type Row = { kind: 'day'; key: string; label: string; count: number } | { kind: 'check'; key: string; check: RoomFeedCheck }
const rows = computed<Row[]>(() =>
  groupByDay(items.value, when, (c) => c.sender_game ?? '', tracker.nowMs).flatMap((g, gi) => [
    // The group index keeps heading keys unique when the server order interleaves two days around midnight.
    { kind: 'day' as const, key: `day:${gi}:${g.key}`, label: g.key === 'before' ? UNKNOWN_DAY : g.label, count: g.rows.length },
    ...g.rows.map((r) => ({ kind: 'check' as const, key: r.entry.key, check: r.entry })),
  ]))

const virtualizer = useVirtualizer<HTMLElement, HTMLElement>(computed(() => ({
  count: rows.value.length,
  getScrollElement: () => scrollEl.value,
  estimateSize: (i: number) => (rows.value[i]?.kind === 'day' ? 37 : 56),
  getItemKey: (i: number) => rows.value[i]?.key ?? i,
  overscan: 12,
})))
const visible = computed(() => virtualizer.value.getVirtualItems().map((v) => ({ v, r: rows.value[v.index] })).filter((x) => x.r))
const measure = (el: Element | ComponentPublicInstance | null) => {
  if (el instanceof HTMLElement) virtualizer.value.measureElement(el)
}

// Load the next page once the end of the loaded rows comes into view.
// The cursor ends the paging even when the loaded rows and the total disagree (no stuck button).
const hasMore = computed(() => items.value.length < total.value && nextOffset.value < total.value)
async function more(): Promise<void> {
  // A page of rows we already have (live inserts shift the server offsets) does not end the paging: go on.
  while ((await load(false)) === 0 && hasMore.value && !loading.value) { /* next page */ }
}
watch(() => visible.value.at(-1)?.v.index ?? -1, (last) => {
  if (last >= rows.value.length - 5 && hasMore.value && !loading.value && !error.value) void more()
})

const select = 'h-9 min-w-0 max-w-full rounded-lg border bg-card px-2 text-sm text-foreground max-[699px]:h-11'
</script>

<template>
  <section class="flex min-w-0 flex-col gap-2" aria-labelledby="room-feed-title">
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

    <div class="min-w-0 rounded-xl border bg-card py-3">
      <p v-if="!loaded && loading" class="px-4 text-sm text-muted-foreground">Chargement…</p>
      <p v-else-if="loaded && !total" class="px-4 text-sm text-muted-foreground">Aucun check pour ces filtres.</p>

      <div
        v-show="rows.length" ref="scrollEl" data-feed-scroll tabindex="0" aria-label="Fil des checks"
        class="max-h-[min(65vh,40rem)] overflow-y-auto overscroll-contain px-4"
      >
        <ul class="relative" :style="{ height: `${virtualizer.getTotalSize()}px` }">
          <li
            v-for="{ v, r } in visible" :key="r.key" :ref="measure" :data-index="v.index"
            class="absolute inset-x-0 top-0 min-w-0" :style="{ transform: `translateY(${v.start}px)` }"
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
      </div>

      <button v-if="hasMore" type="button" class="mx-4 mt-3 rounded-lg border px-3 py-1.5 text-sm hover:bg-accent disabled:opacity-50 max-[699px]:min-h-11" :disabled="loading" @click="void more()">{{ loading ? 'Chargement…' : 'Afficher plus' }}</button>
    </div>
  </section>
</template>
