<script setup lang="ts">
import { computed, ref, type ComponentPublicInstance } from 'vue'
import { useElementSize, useMediaQuery } from '@vueuse/core'
import { formatWhen } from '../../lib/history'
import type { RecentItem } from '../../lib/types'
import { tracker } from '../../stores/tracker'
import { hhmm } from '../lib/card'
import { CATEGORY_CLASS, category } from '../lib/days'
import { openHistory } from '../lib/nav'
import type { TickerStyle } from '../lib/prefs'

// « Derniers reçus » as a news ticker: the items slide from right to left in a loop, paused on hover or focus.
const props = defineProps<{ items: RecentItem[]; variant: Exclude<TickerStyle, 'off'> }>()

/** Scroll speed in px per second: slow enough to read an item while it crosses the screen. */
const SPEED = 45

const viewport = ref<HTMLElement | null>(null)
const lap = ref<HTMLElement | null>(null)
const setLap = (el: Element | ComponentPublicInstance | null) => {
  lap.value = el instanceof HTMLElement ? el : null
}
const { width: viewWidth } = useElementSize(viewport)
const { width: lapWidth } = useElementSize(lap)
const reduced = useMediaQuery('(prefers-reduced-motion: reduce)')
// Slide only when the items do not fit. The list is then drawn twice and the track moves by one copy per lap, so the
// loop has no seam. With reduced motion the list stays still and scrolls by hand.
const moving = computed(() => !reduced.value && lapWidth.value > viewWidth.value)
const copies = computed(() => (moving.value ? [0, 1] : [0]))
const duration = computed(() => `${Math.max(12, Math.round(lapWidth.value / SPEED))}s`)

const newCount = computed(() => props.items.filter((i) => i.new).length)
const when = (i: RecentItem) => formatWhen(i.received_at, tracker.nowMs).replace(/^il y a /, '')
const from = (i: RecentItem) =>
  i.origin === 'start' ? 'départ' : i.origin === 'server' ? 'serveur' : i.own ? 'toi' : `de ${i.sender}`
const open = () => openHistory('received')
</script>

<template>
  <div
    data-ticker :data-variant="variant"
    class="mt-3 flex min-w-0 items-stretch"
    :class="variant === 'ruban' ? 'flex-col gap-1.5' : ['h-12 overflow-hidden rounded-[14px] border', variant === 'arrivees' ? 'bg-popover font-mono' : 'bg-card']"
  >
    <!-- Label -->
    <div v-if="variant === 'agence'" class="flex shrink-0 items-center gap-2 border-r bg-accent px-4">
      <span aria-hidden="true" class="size-[7px] rounded-full bg-live shadow-[0_0_8px_var(--live)]" />
      <span class="font-mono text-[11px] font-semibold tracking-wider uppercase max-[699px]:sr-only">Derniers reçus</span>
    </div>
    <div v-else-if="variant === 'arrivees'" class="flex shrink-0 flex-col justify-center border-r border-dashed px-4 max-[699px]:px-3">
      <span class="text-[10px] tracking-widest text-muted-foreground uppercase">Arrivées</span>
      <span v-if="newCount" class="text-[13px] font-semibold text-new">★ {{ newCount }}<span class="max-[699px]:hidden"> nouveau{{ newCount > 1 ? 'x' : '' }}</span></span>
    </div>
    <div v-else class="flex items-baseline gap-3">
      <span class="font-mono text-[11px] tracking-wider text-muted-foreground uppercase">Derniers reçus</span>
      <button type="button" class="ml-auto text-sm text-logic hover:underline" @click="open">Tout voir →</button>
    </div>

    <!-- Scrolling items -->
    <div
      ref="viewport" class="v2-ticker-view flex min-w-0 flex-1 items-center"
      :class="[moving ? 'overflow-hidden' : 'overflow-x-auto', moving && (variant === 'ruban' ? 'v2-ticker-fade-wide' : 'v2-ticker-fade'), variant === 'ruban' && 'py-1.5']"
    >
      <div class="flex w-max" :class="moving && 'v2-ticker-move'" :style="{ animationDuration: duration }">
        <div
          v-for="c in copies" :key="c" :ref="c === 0 ? setLap : undefined" class="flex shrink-0 items-center"
          :class="variant === 'ruban' && 'gap-2.5 pr-2.5'" :aria-hidden="c === 1 ? 'true' : undefined" :inert="c === 1"
        >
          <template v-for="i in items" :key="i.slot + i.index">
            <button
              v-if="variant === 'agence'" type="button"
              class="group inline-flex items-baseline gap-1.5 pl-4 text-sm whitespace-nowrap" @click="open"
            >
              <span :class="i.progression ? 'text-new' : 'text-muted-foreground'">★</span>
              <span class="font-semibold group-hover:underline group-hover:underline-offset-3">{{ i.name }}</span>
              <span class="text-muted-foreground">→ {{ i.game }}</span>
              <span class="font-mono text-xs text-muted-foreground">· {{ when(i) }}</span>
              <span aria-hidden="true" class="pl-2.5 text-muted-foreground/40">◆</span>
            </button>
            <button
              v-else-if="variant === 'arrivees'" type="button"
              class="group inline-flex h-12 items-center gap-2.5 border-r border-border/60 px-5 text-[13px] whitespace-nowrap" @click="open"
            >
              <span class="text-muted-foreground tabular-nums">{{ i.received_at != null ? hhmm(i.received_at) : '—' }}</span>
              <span
                class="rounded px-1.5 text-[10px] font-semibold tracking-wide"
                :class="category(i) ? CATEGORY_CLASS[category(i)!] : 'bg-muted text-muted-foreground'"
              >{{ category(i) ?? 'ITEM' }}</span>
              <span class="font-sans text-sm font-semibold group-hover:underline group-hover:underline-offset-3">{{ i.name }}</span>
              <span class="text-muted-foreground">→ {{ i.slot }}</span>
              <span class="text-muted-foreground">{{ from(i) }}</span>
            </button>
            <button
              v-else type="button"
              class="inline-flex h-9 items-center gap-2 rounded-full border px-3.5 text-sm whitespace-nowrap transition-transform hover:-translate-y-px motion-reduce:transition-none"
              :class="i.progression ? 'border-gold-line bg-gold-tint shadow-[0_0_14px_-4px_var(--gold-glow)]' : 'bg-card'"
              @click="open"
            >
              <span :class="i.progression ? 'text-new' : 'text-muted-foreground'">★</span>
              <span class="font-semibold">{{ i.name }}</span>
              <span class="text-[13px] text-muted-foreground">{{ i.game }}</span>
              <span class="font-mono text-[11px] text-muted-foreground">{{ when(i) }}</span>
            </button>
          </template>
        </div>
      </div>
    </div>

    <button
      v-if="variant !== 'ruban'" type="button" aria-label="Voir l'historique des items reçus"
      class="shrink-0 border-l px-4 text-sm text-logic hover:underline max-[699px]:px-3"
      :class="variant === 'arrivees' && 'border-dashed'" @click="open"
    >
      <span class="max-[699px]:hidden">{{ variant === 'arrivees' ? 'Historique →' : 'Tout voir →' }}</span>
      <span class="min-[700px]:hidden" aria-hidden="true">›</span>
    </button>
  </div>
</template>

<style scoped>
@keyframes v2-ticker {
  from { transform: translate3d(0, 0, 0); }
  to { transform: translate3d(-50%, 0, 0); }
}
.v2-ticker-move {
  animation: v2-ticker linear infinite;
}
.v2-ticker-view:hover .v2-ticker-move,
.v2-ticker-view:focus-within .v2-ticker-move {
  animation-play-state: paused;
}
.v2-ticker-fade {
  mask-image: linear-gradient(90deg, transparent, #000 24px, #000 calc(100% - 40px), transparent);
}
.v2-ticker-fade-wide {
  mask-image: linear-gradient(90deg, transparent, #000 64px, #000 calc(100% - 64px), transparent);
}
</style>
