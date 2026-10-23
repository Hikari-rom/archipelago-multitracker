<script setup lang="ts">
import { cn } from '@/lib/utils'
import { percent } from '../lib/dashboard'
import { isBK } from '../lib/logic'
import type { SlotSummary } from '../lib/types'
import { pinActive } from '../stores/tracker'
import ProgressSplit from './ProgressSplit.vue'

/** Compact layout, right column: every game in one line; a click makes it the active game (shown on the left). */
defineProps<{ slots: SlotSummary[]; current: string | null }>()
const inLogic = (s: SlotSummary) => (s.logic.state === 'ok' && !s.goal ? s.logic.count : 0)
const logicText = (s: SlotSummary) =>
  s.goal ? 'but atteint' : s.logic.state === 'ok' ? `${s.logic.count} en logique` : s.logic.state === 'pending' ? '…' : '—'
</script>

<template>
  <nav class="bg-card rounded-xl border" aria-label="Jeux">
    <ul class="divide-y">
      <li v-for="s in slots" :key="s.name">
        <button
          type="button"
          :class="cn('compact-row hover:bg-accent/60 flex w-full flex-col gap-1 px-3 py-2 text-left', s.name === current && 'bg-accent')"
          :aria-current="s.name === current ? 'true' : undefined"
          :data-slot-name="s.name"
          @click="pinActive(s.name)"
        >
          <span class="flex items-baseline justify-between gap-2">
            <span class="min-w-0 truncate text-sm font-medium" :title="s.game">{{ s.game }}</span>
            <span
              :class="cn('shrink-0 text-sm tabular-nums whitespace-nowrap', inLogic(s) > 0 ? 'text-bar-logic font-semibold' : 'text-muted-foreground')"
            >
              <span v-if="isBK(s)" data-bk class="bg-warn text-warn-foreground mr-1.5 rounded px-1 font-mono text-[11px] font-semibold" title="BK : aucun check en logique, en attente d'items des autres joueurs">BK</span>{{ logicText(s) }}
            </span>
          </span>
          <ProgressSplit
            :done="s.checks.done"
            :logic="inLogic(s)"
            :total="s.checks.total"
            :label="`${s.game} : ${s.checks.done} checks faits sur ${s.checks.total} (${percent(s.checks.done, s.checks.total)} %), ${inLogic(s)} en logique`"
          />
          <span class="text-muted-foreground flex justify-between gap-2 text-xs">
            <span class="min-w-0 truncate">{{ s.name }}</span>
            <span class="shrink-0 tabular-nums">
              <template v-if="s.items.new">{{ s.items.new }} {{ s.items.new === 1 ? 'nouvel item' : 'nouveaux' }} · </template>{{ s.checks.remaining }} restants
            </span>
          </span>
        </button>
      </li>
    </ul>
  </nav>
</template>
