<script setup lang="ts">
import { computed, ref } from 'vue'
import type { RoomFeedPlayer } from '../../../lib/types'
import { PRESENCE_LABEL, pct, sortPlayers, type BoardSort } from '../../lib/room'

const props = defineProps<{ players: RoomFeedPlayer[] }>()

const sort = ref<BoardSort>('pct')
const sorts: { key: BoardSort; label: string }[] = [
  { key: 'pct', label: '%' },
  { key: 'checks', label: 'Checks' },
]
const ranked = computed(() => sortPlayers(props.players, sort.value))

const open = ref<Set<string>>(new Set())
function toggle(name: string): void {
  const next = new Set(open.value)
  if (!next.delete(name)) next.add(name)
  open.value = next
}
const id = (name: string) => `room-slots-${name.replace(/\W+/g, '_')}`
const seg = 'inline-flex rounded-lg border p-0.5'
const segBtn = (on: boolean) => ['min-h-8 rounded-md px-3 text-sm max-[699px]:min-h-11', on ? 'bg-accent font-semibold text-foreground' : 'text-muted-foreground hover:text-foreground']
// Row grid: rank | player | checks | % | bar | goals | dot (phone: rank | player | % on the first line, the rest below).
const grid = 'grid grid-cols-[1.5rem_minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1 min-[700px]:grid-cols-[2rem_minmax(0,1.4fr)_6.5rem_3rem_minmax(4rem,1fr)_4rem_1rem]'
</script>

<template>
  <section class="flex min-w-0 flex-col gap-2" aria-labelledby="room-board-title">
    <div class="flex flex-wrap items-center gap-x-4 gap-y-2">
      <h3 id="room-board-title" class="text-base font-semibold">Classement</h3>
      <div class="flex items-center gap-2 text-sm text-muted-foreground">
        Tri
        <div :class="seg" role="group" aria-label="Tri du classement">
          <button v-for="s in sorts" :key="s.key" type="button" :aria-pressed="sort === s.key" :class="segBtn(sort === s.key)" @click="sort = s.key">{{ s.label }}</button>
        </div>
      </div>
    </div>

    <ol class="divide-y rounded-xl border bg-card text-sm">
      <li v-for="(p, i) in ranked" :key="p.player" data-row class="min-w-0">
        <button
          type="button" :aria-expanded="open.has(p.player)" :aria-controls="id(p.player)"
          class="w-full px-3 py-2 text-left hover:bg-accent max-[699px]:min-h-11" :class="grid"
          @click="toggle(p.player)"
        >
          <span data-rank class="font-mono text-muted-foreground tabular-nums">{{ i + 1 }}</span>
          <span class="flex min-w-0 items-center gap-2">
            <span data-player-name class="truncate font-medium" :title="p.player">{{ p.player }}</span>
            <span v-if="p.playing > 0" data-playing-dot class="size-2 shrink-0 rounded-full bg-done min-[700px]:hidden" title="Au moins un slot en jeu" role="img" aria-label="Au moins un slot en jeu" />
            <span v-if="p.me" data-me class="shrink-0 rounded-full bg-logic/15 px-2 text-xs text-logic">toi</span>
          </span>
          <span class="whitespace-nowrap text-right font-mono tabular-nums min-[700px]:order-4 min-[700px]:text-left">{{ pct(p.done, p.total) }} %</span>
          <span class="col-start-2 col-end-4 whitespace-nowrap font-mono text-xs text-muted-foreground tabular-nums min-[700px]:order-3 min-[700px]:col-auto min-[700px]:text-sm min-[700px]:text-foreground">{{ p.done }} / {{ p.total }}</span>
          <span class="col-start-2 col-end-4 h-1.5 overflow-hidden rounded-full bg-muted min-[700px]:order-5 min-[700px]:col-auto" aria-hidden="true">
            <span class="block h-full bg-done" :style="{ width: pct(p.done, p.total) + '%' }" />
          </span>
          <span class="col-start-2 col-end-4 whitespace-nowrap font-mono text-xs text-muted-foreground tabular-nums min-[700px]:order-6 min-[700px]:col-auto min-[700px]:text-sm min-[700px]:text-foreground">{{ p.goals }}/{{ p.slots.length }} <span class="min-[700px]:sr-only">buts</span></span>
          <span class="hidden min-[700px]:order-7 min-[700px]:block">
            <span v-if="p.playing > 0" data-playing-dot class="block size-2 rounded-full bg-done" title="Au moins un slot en jeu" role="img" aria-label="Au moins un slot en jeu" />
          </span>
        </button>
        <ul v-if="open.has(p.player)" :id="id(p.player)" data-slots class="divide-y border-t bg-background/40 text-sm">
          <li v-for="(s, k) in p.slots" :key="s.name ?? k" class="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-0.5 px-3 py-1.5 pl-11">
            <span class="min-w-0 max-w-full flex-1 basis-40 truncate" :title="`${s.game ?? '?'} · ${s.name ?? '?'}`">{{ s.game ?? '?' }} <span class="text-muted-foreground">· {{ s.name ?? '?' }}</span></span>
            <span class="whitespace-nowrap font-mono text-xs tabular-nums">{{ s.done }} / {{ s.total }}</span>
            <span v-if="s.goal" class="text-done" title="But atteint" aria-label="But atteint">✓</span>
            <span v-if="s.bk === true" data-bk class="rounded bg-warn px-1 font-mono text-[11px] font-semibold leading-tight text-warn-foreground" title="BK : aucun check en logique, en attente d'items des autres joueurs">BK</span>
            <span class="whitespace-nowrap text-xs text-muted-foreground" :class="s.presence === 'playing' && 'text-done'">{{ PRESENCE_LABEL[s.presence] }}</span>
          </li>
        </ul>
      </li>
    </ol>
  </section>
</template>
