<script setup lang="ts">
import { computed, ref } from 'vue'
import type { SlotSummary } from '../../lib/types'
import { markSeen, pinsOf, tracker } from '../../stores/tracker'
import { cardState, stateClass, useCardCtx } from '../lib/card'
import { regionsOf } from '../lib/regions'
import { dismissWithUndo } from '../lib/undo'
import BigNumber from './BigNumber.vue'
import DetailTabs from './DetailTabs.vue'
import GoalBlock from './GoalBlock.vue'
import PinButton from './PinButton.vue'
import StateChips from './StateChips.vue'

const props = defineProps<{ summary: SlotSummary }>()
const ctx = useCardCtx()
const state = computed(() => cardState(props.summary, ctx.value))
const expanded = ref(false)
const regions = computed(() => regionsOf(tracker.details[props.summary.name]?.in_logic_locations ?? []))
const pinned = computed(() => pinsOf(props.summary.name))
const PINS_SHOWN = 5
const btn = 'inline-flex min-h-8 items-center rounded-lg border px-3 text-sm hover:bg-accent max-[699px]:min-h-11'
</script>

<template>
  <article :data-active-card="summary.name" class="rounded-[14px] border bg-card p-5" :class="stateClass(state)">
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
    <div v-if="pinned.length && !expanded" data-card-pins class="mt-3 rounded-md border border-new/40 bg-new/5 p-2">
      <p class="px-1 text-xs font-semibold"><span aria-hidden="true">📌 </span>Épinglés · {{ pinned.length }}</p>
      <ul class="mt-1 grid gap-x-3 min-[900px]:grid-cols-2">
        <li v-for="p in pinned.slice(0, PINS_SHOWN)" :key="p.location" class="flex min-w-0 items-center gap-1 text-sm">
          <PinButton :slot="p.slot" :location="p.location" :name="p.name" :game="p.game" />
          <span class="min-w-0 truncate" :title="p.name">{{ p.name }}</span>
        </li>
      </ul>
      <button v-if="pinned.length > PINS_SHOWN" type="button" class="px-1 text-xs text-logic hover:underline" @click="expanded = true">
        + {{ pinned.length - PINS_SHOWN }} autres
      </button>
    </div>
    <DetailTabs v-if="expanded" :name="summary.name" class="mt-4" />
  </article>
</template>
