<script setup lang="ts">
import { computed } from 'vue'
import { formatWhen } from '../../lib/history'
import type { SlotSummary } from '../../lib/types'
import { tracker } from '../../stores/tracker'
import { cardState, stateClass, useCardCtx } from '../lib/card'
import { dismissWithUndo } from '../lib/undo'
import BigNumber from './BigNumber.vue'
import DetailTabs from './DetailTabs.vue'
import GoalBlock from './GoalBlock.vue'
import StateChips from './StateChips.vue'

const props = defineProps<{ summary: SlotSummary }>()
const ctx = useCardCtx()
const state = computed(() => cardState(props.summary, ctx.value))
const btn = 'inline-flex min-h-8 items-center rounded-lg border px-3 text-sm hover:bg-accent'
</script>

<template>
  <article :data-focus-panel="summary.name" class="rounded-[14px] border bg-card p-6" :class="stateClass(state)">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <StateChips :state="state" />
      <div class="flex flex-wrap items-center gap-3">
        <span v-if="state.connection.kind === 'ok'" class="font-mono text-xs text-muted-foreground">dernier check {{ formatWhen(summary.last_check_at, tracker.nowMs) }}</span>
        <button v-if="state.activity" type="button" data-dismiss :class="btn" @click="dismissWithUndo(summary.name, summary.game)">✕ Plus actif</button>
      </div>
    </div>
    <div class="mt-4 flex flex-wrap items-center justify-between gap-5">
      <div class="flex min-w-0 items-center gap-5">
        <BigNumber :state="state" size="xl" />
        <div class="min-w-0">
          <h3 class="line-clamp-2 text-2xl font-semibold" :title="summary.game">{{ summary.game }}</h3>
          <p class="font-mono text-xs text-muted-foreground">checks en logique · {{ summary.name }} · {{ summary.checks.done }} / {{ summary.checks.total }} faits · {{ summary.checks.remaining }} restants</p>
        </div>
      </div>
      <GoalBlock :objective="tracker.details[summary.name]?.objective" :goal="summary.goal" compact />
    </div>
    <DetailTabs :key="summary.name" :name="summary.name" initial="logic" class="mt-5" />
  </article>
</template>
