<script setup lang="ts">
import { computed } from 'vue'
import { counterText, mainCounter } from '../../lib/goals'
import type { Objective } from '../../lib/types'

const props = defineProps<{ objective: Objective | null | undefined; goal: boolean; compact?: boolean }>()
const main = computed(() => mainCounter(props.objective))
const pct = (c: { current: number; target: number }) => (c.target > 0 ? Math.min(100, Math.round((c.current / c.target) * 100)) : 0)
</script>

<template>
  <p v-if="compact" class="text-sm text-muted-foreground">
    <template v-if="main">But · {{ main.label }} <span class="font-mono tabular-nums">{{ counterText(main) }}</span></template>
    <template v-else-if="goal"><span class="text-done">✓</span> But atteint</template>
    <template v-else-if="objective">But · {{ objective.summary }}</template>
    <template v-else>But non décrit pour ce jeu</template>
  </p>
  <div v-else-if="objective" class="space-y-3">
    <p class="text-sm">{{ objective.summary }}</p>
    <p v-if="objective.note" class="text-xs text-muted-foreground">{{ objective.note }}</p>
    <ul v-if="objective.counters.length" class="space-y-2">
      <li v-for="c in objective.counters" :key="c.label">
        <div class="flex justify-between text-sm"><span>{{ c.label }}</span><span class="font-mono tabular-nums">{{ counterText(c) }}</span></div>
        <div class="mt-1 h-1.5 overflow-hidden rounded-full bg-muted" aria-hidden="true"><div class="h-full bg-done" :style="{ width: pct(c) + '%' }" /></div>
      </li>
    </ul>
    <ul v-if="objective.steps.length" class="space-y-1 text-sm">
      <li v-for="s in objective.steps" :key="s.label" class="flex gap-2">
        <span v-if="s.done === true" class="text-done">✓</span>
        <span v-else-if="s.done === false" class="text-muted-foreground">○</span>
        <span v-else class="text-muted-foreground">⊘</span>
        <span>{{ s.label }}<span v-if="s.done === true" class="text-done"> · faite</span><span v-else-if="s.done === false" class="text-muted-foreground"> · à faire</span><span v-else class="text-muted-foreground"> · invisible pour un tracker</span></span>
      </li>
    </ul>
  </div>
  <p v-else class="text-sm text-muted-foreground">But non décrit pour ce jeu.</p>
</template>
