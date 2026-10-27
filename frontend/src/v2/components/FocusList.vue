<script setup lang="ts">
import { useMediaQuery } from '@vueuse/core'
import { barParts } from '../../lib/dashboard'
import type { SlotSummary } from '../../lib/types'
import { pinActive } from '../../stores/tracker'
import { cardState, useCardCtx } from '../lib/card'
import BigNumber from './BigNumber.vue'

const props = defineProps<{ slots: SlotSummary[]; current: string | null }>()
const phone = useMediaQuery('(max-width: 699px)')
const ctx = useCardCtx()
const st = (s: SlotSummary) => cardState(s, ctx.value)
const logicOf = (s: SlotSummary) => (s.logic.state === 'ok' ? s.logic.count : 0)
// BK rows are red and finished games gold, the shown game included: its outline marks it as the current one.
function rowClass(s: SlotSummary): string {
  const now = s.name === props.current
  const tint = st(s).goalReached ? 'bg-gold-tint' : st(s).bk ? 'bg-bk-tint' : now ? 'bg-logic/15' : ''
  const ring = st(s).goalReached ? 'ring-gold-line' : st(s).bk ? 'ring-bk' : 'ring-logic/60'
  return now ? `${tint} ring-2 ring-inset ${ring}` : tint
}
const barClass = (s: SlotSummary): string =>
  st(s).goalReached ? 'bg-gold-line' : st(s).bk ? 'bg-bk' : s.name === props.current ? 'bg-logic' : ''
</script>

<template>
  <div class="rounded-[14px] border bg-card">
    <p class="border-b px-4 py-2 font-mono text-xs text-muted-foreground">{{ slots.length }} jeux · {{ phone ? 'toucher' : 'clic' }} = afficher et rendre actif</p>
    <ul class="overflow-y-auto min-[700px]:max-h-[calc(100vh-220px)]">
      <li v-for="s in slots" :key="s.name" class="border-b last:border-b-0">
        <button
          type="button" :data-focus-row="s.name" :aria-current="s.name === current ? 'true' : undefined"
          class="relative flex min-h-11 w-full items-center gap-3 px-4 py-2 text-left hover:bg-accent"
          :class="rowClass(s)" :data-state="st(s).goalReached ? 'goal' : st(s).bk ? 'bk' : undefined"
          @click="pinActive(s.name)"
        >
          <span class="absolute inset-y-0 left-0 w-[3px]" :class="barClass(s)" aria-hidden="true" />
          <span class="w-12 shrink-0 text-right"><BigNumber :state="st(s)" size="md" /></span>
          <span class="min-w-0 flex-1">
            <span class="flex items-baseline gap-2">
              <span class="truncate text-sm font-medium" :title="s.game">{{ s.game }}</span>
              <span v-if="st(s).activity?.kind === 'chosen'" class="shrink-0 font-mono text-[11px] text-logic">◉ choisi</span>
              <span v-else-if="st(s).activity?.kind === 'auto'" class="shrink-0 font-mono text-[11px] text-logic">◔ auto</span>
            </span>
            <span class="mt-1 flex h-1 overflow-hidden rounded-full bg-muted" aria-hidden="true">
              <span class="bg-done" :style="{ width: barParts(s.checks.done, logicOf(s), s.checks.total).done + '%' }" />
              <span class="bg-logic" :style="{ width: barParts(s.checks.done, logicOf(s), s.checks.total).logic + '%' }" />
            </span>
          </span>
          <span class="shrink-0 font-mono text-xs">
            <span v-if="s.hints.in_my_world_in_logic" class="text-hint">◆{{ s.hints.in_my_world_in_logic }} </span>
            <span v-if="s.items.new" class="text-new">★{{ s.items.new }}</span>
          </span>
          <span class="w-16 shrink-0 text-right font-mono text-xs text-muted-foreground">{{ s.checks.remaining }} rest.</span>
        </button>
      </li>
    </ul>
  </div>
</template>
