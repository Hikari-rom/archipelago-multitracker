<script setup lang="ts">
import { computed } from 'vue'
import { cn } from '@/lib/utils'
import { barParts } from '../lib/dashboard'

/** Progress bar in two colours: green = checks done, blue = checks in logic (not done yet). */
const props = defineProps<{ done: number; logic: number; total: number; label: string; class?: string }>()
const parts = computed(() => barParts(props.done, props.logic, props.total))
</script>

<template>
  <div
    role="img"
    :aria-label="label"
    :title="label"
    :class="cn('bg-muted ring-border/60 flex h-2 w-full overflow-hidden rounded-full ring-1 ring-inset', props.class)"
  >
    <div class="bg-bar-done h-full transition-[width] motion-reduce:transition-none" :style="{ width: `${parts.done}%` }" />
    <div class="bg-bar-logic h-full transition-[width] motion-reduce:transition-none" :style="{ width: `${parts.logic}%` }" />
  </div>
</template>
