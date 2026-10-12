<script setup lang="ts">
import { computed } from 'vue'
import { CircleCheck, Circle, CircleHelp, Flag, Trophy } from '@lucide/vue'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { SOURCE_LABELS, counterText, goalProgress, sortByGoal } from '../lib/goals'
import type { SlotSummary } from '../lib/types'
import ProgressSplit from './ProgressSplit.vue'

/** Goal of every selected slot (owner filter of the header) and how far it is. */
const props = defineProps<{ slots: SlotSummary[] }>()
const sorted = computed(() => sortByGoal(props.slots))
const reached = computed(() => props.slots.filter((s) => s.goal).length)
const pct = (s: SlotSummary) => Math.round(goalProgress(s) * 100)
</script>

<template>
  <section class="flex flex-col gap-3" aria-labelledby="goals-title">
    <div class="flex flex-wrap items-baseline gap-x-3 gap-y-1">
      <h2 id="goals-title" class="flex items-center gap-2 text-base font-semibold"><Flag class="size-4" aria-hidden="true" /> Objectifs</h2>
      <span class="text-muted-foreground text-sm">{{ reached }} / {{ slots.length }} {{ slots.length > 1 ? 'buts atteints' : 'but atteint' }}</span>
    </div>
    <p class="text-muted-foreground text-sm">
      Calculé sans spoiler : options du slot (slot_data ou yaml), items reçus et checks faits. Les étapes marquées
      <CircleHelp class="inline size-3.5 align-[-2px]" aria-label="?" /> sont des événements du jeu qu’un tracker ne voit pas.
    </p>
    <p v-if="!slots.length" class="text-muted-foreground">Aucun slot.</p>
    <div class="grid grid-cols-1 items-start gap-3 min-[900px]:grid-cols-2">
      <Card v-for="s in sorted" :key="s.name" as="article" :class="cn('min-w-0 gap-3 px-4 py-4', s.goal && 'opacity-80')" :data-goal-slot="s.name">
        <header class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <h3 class="text-lg leading-tight font-semibold break-words">{{ s.game }}</h3>
            <p class="text-muted-foreground text-sm break-words">
              {{ s.name }}<span v-if="s.owner" class="italic"> · {{ s.owner }}</span>
            </p>
          </div>
          <Badge v-if="s.goal" variant="good" class="shrink-0"><Trophy aria-hidden="true" /> But atteint</Badge>
          <Badge v-else-if="s.objective" variant="secondary" class="shrink-0 tabular-nums" :title="'Avancement estimé à partir des compteurs et des étapes visibles'">{{ pct(s) }} %</Badge>
        </header>

        <template v-if="s.objective">
          <p class="font-semibold">But : {{ s.objective.summary }}</p>
          <p v-if="s.objective.note" class="text-muted-foreground -mt-2 text-sm">{{ s.objective.note }}</p>
          <ul v-if="s.objective.counters.length" class="flex flex-col gap-2.5">
            <li v-for="c in s.objective.counters" :key="c.label" class="text-sm">
              <div class="mb-1 flex justify-between gap-2">
                <span class="min-w-0 break-words">{{ c.label }}</span>
                <strong :class="cn('tabular-nums whitespace-nowrap', c.current >= c.target && 'text-good-foreground')">{{ counterText(c) }}</strong>
              </div>
              <ProgressSplit :done="Math.min(c.current, c.target)" :logic="0" :total="c.target" :label="`${c.label} : ${counterText(c)}`" />
              <p v-if="c.detail" class="text-muted-foreground mt-0.5 text-xs">{{ c.detail }}</p>
            </li>
          </ul>
          <ul v-if="s.objective.steps.length" class="flex flex-col gap-1 text-sm" aria-label="Étapes">
            <li v-for="st in s.objective.steps" :key="st.label" class="flex items-start gap-2">
              <CircleCheck v-if="st.done" class="text-bar-done mt-0.5 size-4 shrink-0" aria-label="fait" />
              <CircleHelp
                v-else-if="st.done === null"
                class="text-muted-foreground mt-0.5 size-4 shrink-0"
                aria-label="pas visible par un tracker"
              />
              <Circle v-else class="text-muted-foreground mt-0.5 size-4 shrink-0" aria-label="à faire" />
              <span :class="cn('break-words', st.done && 'text-muted-foreground line-through')" :title="st.done === null ? 'Événement du jeu : un tracker ne le voit pas' : undefined">{{ st.label }}</span>
            </li>
          </ul>
          <p v-if="s.objective.source" class="text-muted-foreground text-xs">{{ SOURCE_LABELS[s.objective.source] ?? s.objective.source }}</p>
        </template>
        <p v-else class="text-muted-foreground text-sm">
          {{ s.status === 'connected' ? 'Objectif pas encore décrit pour ce jeu.' : 'Objectif affiché une fois le slot connecté.' }}
        </p>
      </Card>
    </div>
  </section>
</template>
