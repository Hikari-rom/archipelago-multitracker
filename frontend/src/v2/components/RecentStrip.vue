<script setup lang="ts">
import { computed } from 'vue'
import { useMediaQuery } from '@vueuse/core'
import { FEED_SHORT, feedItems } from '../../lib/dashboard'
import { formatWhen } from '../../lib/history'
import type { SlotSummary } from '../../lib/types'
import { tracker } from '../../stores/tracker'
import { openHistory } from '../lib/nav'
import NewsTicker from './NewsTicker.vue'

/** How many items the ticker carries: more than the static strip, it has the room to show them in turn. */
const TICKER_COUNT = 15

const props = defineProps<{ slots: SlotSummary[] }>()
const phone = useMediaQuery('(max-width: 699px)')
const ticker = computed(() => (tracker.ticker === 'off' ? null : tracker.ticker))
const items = computed(() =>
  feedItems(tracker.recent, new Set(props.slots.map((s) => s.name)), ticker.value ? TICKER_COUNT : phone.value ? 1 : FEED_SHORT))
</script>

<template>
  <NewsTicker v-if="ticker && items.length" :items="items" :variant="ticker" />
  <div v-else-if="items.length" class="mt-3 rounded-[14px] border bg-card px-5 py-3">
    <button v-if="phone" type="button" class="flex min-h-11 w-full items-center gap-2 text-left text-sm" @click="openHistory('received')">
      <span :class="items[0].progression ? 'text-new' : 'text-muted-foreground'">★</span>
      <span class="min-w-0 flex-1 truncate">{{ items[0].name }} → {{ items[0].game }} · {{ formatWhen(items[0].received_at, tracker.nowMs) }}</span>
      <span aria-label="Voir l'historique">›</span>
    </button>
    <div v-else class="flex flex-wrap items-center gap-x-5 gap-y-1 text-sm">
      <span class="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">Derniers reçus</span>
      <span v-for="i in items" :key="i.slot + i.index" class="whitespace-nowrap">
        <span :class="i.progression ? 'text-new' : 'text-muted-foreground'">★</span>
        {{ i.name }} → {{ i.game }} · <span class="text-muted-foreground">{{ formatWhen(i.received_at, tracker.nowMs) }}</span>
      </span>
      <button type="button" class="ml-auto text-sm text-logic hover:underline" @click="openHistory('received')">Tout voir →</button>
    </div>
  </div>
</template>
