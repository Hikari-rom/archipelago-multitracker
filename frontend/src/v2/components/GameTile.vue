<script setup lang="ts">
import { computed } from 'vue'
import type { SlotSummary } from '../../lib/types'
import { isOpen, pinActive, toggleOpen } from '../../stores/tracker'
import { cardState, useCardCtx } from '../lib/card'
import BigNumber from './BigNumber.vue'
import DetailTabs from './DetailTabs.vue'
import StateChips from './StateChips.vue'

const props = defineProps<{ summary: SlotSummary }>()
const ctx = useCardCtx()
const state = computed(() => cardState(props.summary, ctx.value))
// The full chips belong to the active cards; a tile only shows what needs attention.
const showChips = computed(() => {
  const s = state.value
  return s.connection.kind === 'error' || s.connection.kind === 'sleeping' || s.logic.kind === 'pending' || (s.logic.kind === 'ok' && s.logic.approx)
})
const btn = 'inline-flex min-h-8 items-center rounded-lg border px-3 text-sm hover:bg-accent max-[699px]:min-h-11'
</script>

<template>
  <article
    :data-tile="summary.name"
    class="flex flex-col gap-2 rounded-[14px] border bg-card p-4 transition motion-reduce:transition-none hover:border-logic/50 focus-within:ring-2 focus-within:ring-logic"
    :class="{ 'min-[700px]:col-span-2': isOpen(summary.name) }"
  >
    <BigNumber :state="state" size="lg" />
    <div class="min-w-0">
      <h3 class="line-clamp-2 font-semibold" :title="summary.game">{{ summary.game }}</h3>
      <p class="font-mono text-xs text-muted-foreground">{{ summary.name }} · {{ summary.checks.remaining }} restants</p>
    </div>
    <div class="flex flex-wrap items-center gap-2 text-sm">
      <span v-if="summary.items.new > 0" class="text-new">★{{ summary.items.new }}</span>
      <span v-if="summary.hints.in_my_world_in_logic > 0" class="text-hint">◆{{ summary.hints.in_my_world_in_logic }}</span>
      <span v-if="state.logic.kind === 'unavailable'" class="text-muted-foreground">Logique indisponible</span>
      <StateChips v-if="showChips" :state="state" />
    </div>
    <div class="mt-auto flex items-center gap-2">
      <button type="button" data-activate :class="btn" @click="pinActive(summary.name)">◎ Activer</button>
      <button type="button" :class="btn" :aria-expanded="isOpen(summary.name)" @click="toggleOpen(summary.name)">Détails</button>
    </div>
    <DetailTabs v-if="isOpen(summary.name)" :name="summary.name" />
  </article>
</template>
