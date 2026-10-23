<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import * as api from '../../../lib/api'
import { MONTHS } from '../../../lib/history'
import type { RoomFeedActivity, RoomFeedPlayer } from '../../../lib/types'
import { hhmm } from '../../lib/card'

const props = defineProps<{ players: RoomFeedPlayer[] }>()

type Bucket = 'hour' | 'day'
const ranges: { key: Bucket; label: string }[] = [
  { key: 'hour', label: '48 h' },
  { key: 'day', label: '30 jours' },
]
const bucket = ref<Bucket>('hour')
const player = ref('')
const data = ref<RoomFeedActivity | null>(null)
const error = ref('')

const playerNames = computed(() => [...new Set(props.players.map((p) => p.player))])

let seq = 0
async function load(): Promise<void> {
  const mine = ++seq
  try {
    const r = await api.getRoomFeedActivity(bucket.value, player.value || undefined)
    if (mine !== seq) return
    data.value = r
    error.value = ''
  } catch (e) {
    if (mine === seq) error.value = e instanceof Error ? e.message : String(e)
  }
}
onMounted(() => void load())
// Toggles, and every refresh of the summary (which follows the debounced `roomfeed` events).
watch([bucket, player, () => props.players], () => void load())

const W = 10
const H = 100
const buckets = computed(() => data.value?.buckets ?? [])
const max = computed(() => buckets.value.reduce((m, b) => Math.max(m, b.count), 0))
const plural = (n: number) => `${n} check${n > 1 ? 's' : ''}`
const stamp = (start: number): string => {
  if (bucket.value === 'hour') return hhmm(start)
  const d = new Date(start * 1000)
  return `${d.getDate()} ${MONTHS[d.getMonth()]}`
}
const bars = computed(() =>
  buckets.value.map((b, i) => {
    const height = b.count === 0 ? 0 : Math.max(2, (b.count / max.value) * H)
    return { key: b.start, x: i * W + 1, y: H - height, height, title: `${stamp(b.start)} · ${plural(b.count)}` }
  }))
// x labels: every 6 h (on the hours 00, 06, 12, 18) or every 5 days (counted back from the last day).
const labels = computed(() => {
  const n = buckets.value.length
  return buckets.value
    .map((b, i) => ({ start: b.start, left: ((i + 0.5) / n) * 100, show: bucket.value === 'hour' ? new Date(b.start * 1000).getHours() % 6 === 0 : (n - 1 - i) % 5 === 0 }))
    .filter((l) => l.show)
    .map((l) => ({ ...l, text: stamp(l.start) }))
})
const seg = 'inline-flex rounded-lg border p-0.5'
const segBtn = (on: boolean) => ['min-h-8 rounded-md px-3 text-sm max-[699px]:min-h-11', on ? 'bg-accent font-semibold text-foreground' : 'text-muted-foreground hover:text-foreground']
</script>

<template>
  <section class="flex min-w-0 flex-col gap-2" aria-labelledby="room-activity-title">
    <div class="flex flex-wrap items-center gap-x-4 gap-y-2">
      <h3 id="room-activity-title" class="text-base font-semibold">Activité</h3>
      <div :class="seg" role="group" aria-label="Période">
        <button v-for="r in ranges" :key="r.key" type="button" :aria-pressed="bucket === r.key" :class="segBtn(bucket === r.key)" @click="bucket = r.key">{{ r.label }}</button>
      </div>
      <label class="flex min-w-0 items-center gap-2 text-sm text-muted-foreground">
        Joueur
        <select v-model="player" class="h-9 min-w-0 max-w-full rounded-lg border bg-card px-2 text-sm text-foreground max-[699px]:h-11">
          <option value="">toute la room</option>
          <option v-for="n in playerNames" :key="n" :value="n">{{ n }}</option>
        </select>
      </label>
    </div>

    <p v-if="error" role="alert" class="break-words rounded-xl bg-warn p-3 text-sm text-warn-foreground"><span class="text-error">! </span>{{ error }}</p>

    <div class="min-w-0 rounded-xl border bg-card px-4 py-3">
      <p v-if="!data && !error" class="text-sm text-muted-foreground">Chargement…</p>
      <template v-if="data">
        <p data-max class="mb-1 font-mono text-[10px] text-muted-foreground">max {{ max }} par {{ bucket === 'hour' ? 'heure' : 'jour' }}</p>
        <svg
          class="block h-28 w-full" :viewBox="`0 0 ${buckets.length * W} ${H}`" preserveAspectRatio="none" role="img"
          :aria-label="`Checks de la room par ${bucket === 'hour' ? 'heure' : 'jour'}`"
        >
          <g fill="currentColor" class="text-logic">
            <rect v-for="b in bars" :key="b.key" :x="b.x" :y="b.y" :width="W - 2" :height="b.height"><title>{{ b.title }}</title></rect>
          </g>
        </svg>
        <div class="relative mt-1 h-4 overflow-hidden" aria-hidden="true">
          <span
            v-for="l in labels" :key="l.start" data-xlabel
            class="absolute top-0 -translate-x-1/2 whitespace-nowrap text-[10px] text-muted-foreground" :style="{ left: `${l.left}%` }"
          >{{ l.text }}</span>
        </div>
        <p v-if="data.undated > 0" class="mt-1 text-xs text-muted-foreground">{{ plural(data.undated) }} sans heure</p>
      </template>
    </div>
  </section>
</template>
