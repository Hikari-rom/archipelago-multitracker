<script setup lang="ts">
import { ref } from 'vue'
import type { SlotSummary } from '../../lib/types'
import { tracker } from '../../stores/tracker'
import { cardState, useCardCtx } from '../lib/card'
import { dismissWithUndo } from '../lib/undo'
import BigNumber from './BigNumber.vue'
import GoalBlock from './GoalBlock.vue'
import StateChips from './StateChips.vue'

defineProps<{ slots: SlotSummary[] }>()
const emit = defineEmits<{ details: [string] }>()
const ctx = useCardCtx()
const index = ref(0)
function onScroll(e: Event) {
  const el = e.target as HTMLElement
  if (el.clientWidth > 0) index.value = Math.round(el.scrollLeft / el.clientWidth)
}
const btn = 'inline-flex min-h-11 items-center rounded-lg border px-3 text-sm hover:bg-accent'
</script>

<template>
  <div data-carousel class="flex snap-x snap-mandatory overflow-x-auto rounded-[14px] border bg-card" @scroll="onScroll">
    <article v-for="s in slots" :key="s.name" :data-carousel-card="s.name" class="min-w-full snap-start p-4">
      <div class="flex items-start justify-between gap-2">
        <StateChips :state="cardState(s, ctx)" />
        <span v-if="slots.length > 1" class="shrink-0 font-mono text-xs text-muted-foreground" data-counter>{{ Math.min(index, slots.length - 1) + 1 }} / {{ slots.length }}</span>
      </div>
      <div class="mt-3 flex items-center gap-3">
        <BigNumber :state="cardState(s, ctx)" size="lg" />
        <div class="min-w-0 flex-1">
          <h3 class="line-clamp-2 text-base font-semibold" :title="s.game">{{ s.game }}</h3>
          <p class="font-mono text-xs text-muted-foreground">en logique · {{ s.checks.done }} / {{ s.checks.total }}</p>
        </div>
      </div>
      <GoalBlock :objective="tracker.details[s.name]?.objective" :goal="s.goal" compact class="mt-2" />
      <div class="mt-2 flex items-center justify-between gap-2">
        <button v-if="cardState(s, ctx).activity" type="button" data-dismiss :class="btn" @click="dismissWithUndo(s.name, s.game)">✕ Plus actif</button>
        <span v-else />
        <button type="button" data-details :class="btn" @click="emit('details', s.name)">Détails ↑</button>
      </div>
    </article>
  </div>
</template>
