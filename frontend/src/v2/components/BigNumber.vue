<script setup lang="ts">
import { computed } from 'vue'
import type { CardState } from '../lib/card'
import LogicNote from './LogicNote.vue'

// inButton: rendered inside a button (focus list), the note icon cannot be a button itself.
const props = withDefaults(defineProps<{ state: CardState; size?: 'xl' | 'lg' | 'md'; inButton?: boolean }>(), { size: 'lg' })
const lit = computed(() => props.state.logic.kind === 'ok' && props.state.logic.count > 0)
const approx = computed(() => props.state.logic.kind === 'ok' && props.state.logic.approx)
const note = computed(() => (props.state.logic.kind === 'ok' && !props.state.goalReached ? props.state.logic.note : null))
const px = computed(() => ({ xl: 'text-[56px]', lg: 'text-[34px]', md: 'text-[22px]' })[props.size])
</script>

<template>
  <span class="inline-flex flex-col items-center gap-1 align-middle">
    <span class="inline-flex items-start gap-0.5">
      <span
        class="font-mono font-semibold leading-none tabular-nums"
        :class="[px, state.goalReached ? 'text-gold' : state.bk ? 'text-bk' : lit ? 'text-logic' : 'text-muted-foreground']"
      ><template v-if="state.goalReached">✓</template><template v-else><span v-if="approx" aria-label="approximatif">≈</span>{{ state.big }}</template></span>
      <LogicNote v-if="note" :note="note" :inert="inButton" :class="size === 'md' ? 'text-[11px]' : 'text-sm'" />
    </span>
    <span
      v-if="state.bk" data-bk
      class="rounded bg-bk px-1 font-mono font-semibold leading-tight text-bk-foreground"
      :class="size === 'md' ? 'text-[10px]' : 'text-[11px]'"
      title="BK : aucun check en logique, en attente d'items des autres joueurs"
    >BK</span>
  </span>
</template>
