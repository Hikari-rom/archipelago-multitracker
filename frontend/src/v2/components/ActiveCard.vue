<script setup lang="ts">
import { computed, ref } from 'vue'
import type { SlotSummary } from '../../lib/types'
import { markSeen, tracker } from '../../stores/tracker'
import { cardState, useCardCtx } from '../lib/card'
import { regionsOf } from '../lib/regions'
import { dismissWithUndo } from '../lib/undo'
import BigNumber from './BigNumber.vue'
import DetailTabs from './DetailTabs.vue'
import GoalBlock from './GoalBlock.vue'
import StateChips from './StateChips.vue'

const props = defineProps<{ summary: SlotSummary }>()
const ctx = useCardCtx()
const state = computed(() => cardState(props.summary, ctx.value))
const expanded = ref(false)
const regions = computed(() => regionsOf(tracker.details[props.summary.name]?.in_logic_locations ?? []))
const btn = 'inline-flex min-h-8 items-center rounded-lg border px-3 text-sm hover:bg-accent max-[699px]:min-h-11'
</script>

<template>
  <article :data-active-card="summary.name" class="rounded-[14px] border bg-card p-5">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <StateChips :state="state" />
      <div class="flex items-center gap-2">
        <button type="button" data-dismiss :class="btn" @click="dismissWithUndo(summary.name, summary.game)">✕ Plus actif</button>
        <button type="button" :class="btn" :aria-expanded="expanded" @click="expanded = !expanded">Détails {{ expanded ? '▴' : '▾' }}</button>
      </div>
    </div>
    <div class="mt-4 flex items-center gap-5">
      <BigNumber :state="state" size="xl" />
      <div class="min-w-0">
        <h3 class="line-clamp-2 text-2xl font-semibold" :title="summary.game">{{ summary.game }}</h3>
        <p class="font-mono text-xs text-muted-foreground">checks en logique · {{ summary.name }} · {{ summary.checks.done }} / {{ summary.checks.total }} faits</p>
        <p v-if="summary.items.new" class="mt-1 text-sm">
          <span class="text-new">★ {{ summary.items.new }} {{ summary.items.new > 1 ? 'nouveaux' : 'nouveau' }}</span> ·
          <button type="button" class="text-logic hover:underline" @click="markSeen(summary.name)">Marquer comme vu</button>
        </p>
      </div>
    </div>
    <div class="mt-4 flex flex-wrap items-center gap-x-3 gap-y-2">
      <span v-for="r in regions.slice(0, 3)" :key="r.name" class="rounded-full border px-2.5 py-0.5 font-mono text-xs">{{ r.name }} {{ r.count }}</span>
      <span v-if="regions.length > 3" class="font-mono text-xs text-muted-foreground">+ {{ regions.length - 3 }} régions</span>
      <GoalBlock :objective="tracker.details[summary.name]?.objective" :goal="summary.goal" compact class="ml-auto" />
    </div>
    <DetailTabs v-if="expanded" :name="summary.name" class="mt-4" />
  </article>
</template>
