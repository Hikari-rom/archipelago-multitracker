<script setup lang="ts">
import { computed } from 'vue'
import type { CardState } from '../lib/card'

const props = withDefaults(defineProps<{ state: CardState; size?: 'xl' | 'lg' | 'md' }>(), { size: 'lg' })
const lit = computed(() => props.state.logic.kind === 'ok' && props.state.logic.count > 0)
const approx = computed(() => props.state.logic.kind === 'ok' && props.state.logic.approx)
const px = computed(() => ({ xl: 'text-[56px]', lg: 'text-[34px]', md: 'text-[22px]' })[props.size])
</script>

<template>
  <span
    class="font-mono font-semibold leading-none tabular-nums"
    :class="[px, state.goalReached ? 'text-done' : lit ? 'text-logic' : 'text-muted-foreground']"
  ><template v-if="state.goalReached">✓</template><template v-else><span v-if="approx" aria-label="approximatif">≈</span>{{ state.big }}</template></span>
</template>
