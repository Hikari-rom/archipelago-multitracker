<script setup lang="ts">
import { computed } from 'vue'
import { counterText, mainCounter, NEED_ACCESS, needLabel, needsCount } from '../../lib/goals'
import type { Objective } from '../../lib/types'

// goMode: rainbow bars (D34); choosable: the game offers victory conditions to pick in the Configuration
const props = defineProps<{ objective: Objective | null | undefined; goal: boolean; compact?: boolean; goMode?: boolean; choosable?: boolean }>()
const CHOOSE = 'à choisir dans la Configuration (« Choisir le but à la main »)'
const main = computed(() => mainCounter(props.objective))
const needs = computed(() => (props.goal ? undefined : props.objective?.needs))
const missing = computed(() => (props.goal ? 0 : needsCount(props.objective)))
const pct = (c: { current: number; target: number }) => (c.target > 0 ? Math.min(100, Math.round((c.current / c.target) * 100)) : 0)
</script>

<template>
  <p v-if="compact" class="text-sm text-muted-foreground">
    <template v-if="main">But · {{ main.label }} <span class="font-mono tabular-nums">{{ counterText(main) }}</span></template>
    <template v-else-if="goal"><span class="text-done">✓</span> But atteint</template>
    <template v-else-if="objective">But · {{ objective.summary }}</template>
    <template v-else>But non décrit pour ce jeu<template v-if="choosable"> · {{ CHOOSE }}</template></template>
    <span v-if="missing" data-goal-missing :title="needs?.kind === 'set' ? needs.items.map(needLabel).join(', ') : undefined"> · fin : {{ missing }} item{{ missing > 1 ? 's' : '' }} manquant{{ missing > 1 ? 's' : '' }}</span>
  </p>
  <div v-else-if="objective" class="space-y-3">
    <p class="text-sm">{{ objective.summary }}</p>
    <p v-if="objective.note" class="text-xs text-muted-foreground">{{ objective.note }}</p>
    <ul v-if="objective.counters.length" class="space-y-2">
      <li v-for="c in objective.counters" :key="c.label">
        <div class="flex justify-between text-sm"><span>{{ c.label }}</span><span class="font-mono tabular-nums">{{ counterText(c) }}</span></div>
        <div class="mt-1 h-1.5 overflow-hidden rounded-full bg-muted" aria-hidden="true"><div class="h-full" :class="goMode && !goal ? 'v2-go-bar' : 'bg-done'" :style="{ width: pct(c) + '%' }" /></div>
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
    <div v-if="needs" data-goal-needs class="space-y-1.5 border-t pt-3 text-sm">
      <template v-if="needs.kind === 'set'">
        <p class="font-medium">Pour la fin, il manque {{ missing > 1 ? `ces ${missing} items` : 'cet item' }} :</p>
        <ul class="space-y-1">
          <li v-for="n in needs.items" :key="n.name">
            <span class="font-mono">{{ needLabel(n) }}</span><span v-if="n.or.length" class="text-muted-foreground"> ou {{ n.or.map(needLabel).join(' ou ') }}</span>
            <ul v-if="n.hints.length" class="ml-4 text-xs text-muted-foreground">
              <li v-for="h in n.hints" :key="h.item + h.finder + h.location">
                <template v-if="h.item !== n.name">{{ h.item }} : </template>chez {{ h.finder }}<template v-if="h.finder_game"> ({{ h.finder_game }})</template> · {{ h.location }} · <span :class="h.access === 'ok' ? 'text-done' : ''">{{ NEED_ACCESS[h.access] }}</span>
              </li>
            </ul>
          </li>
        </ul>
        <p v-if="!needs.complete" class="text-xs text-muted-foreground">D'autres items pourraient en remplacer certains (calcul arrêté avant la fin).</p>
      </template>
      <p v-else-if="needs.kind === 'many'" class="text-muted-foreground">Pour la fin, il manque de nombreux items (trop long à détailler).</p>
      <p v-else class="text-muted-foreground">La fin est hors logique même avec tous les items qui restent à recevoir.</p>
    </div>
  </div>
  <p v-else class="text-sm text-muted-foreground">But non décrit pour ce jeu.<template v-if="choosable"> Tu peux le choisir : coche
    « Choisir le but à la main » dans la Configuration, puis règle-le ici ou sous ce slot.</template></p>
</template>
