<script setup lang="ts">
import { CircleAlert, Info, TriangleAlert } from '@lucide/vue'
import { cn } from '@/lib/utils'
import type { Diag } from '../../lib/config'

defineProps<{ diags: Diag[] }>()
const icon = { info: Info, warn: TriangleAlert, error: CircleAlert } as const
const tone = { info: 'text-muted-foreground', warn: 'text-warn-foreground bg-warn', error: 'text-destructive' } as const
</script>

<template>
  <ul v-if="diags.length" class="flex flex-col gap-0.5">
    <li v-for="(d, k) in diags" :key="k" :class="cn('flex items-start gap-1.5 rounded px-1.5 py-0.5 text-xs', tone[d.level])">
      <component :is="icon[d.level]" class="mt-px size-3.5 shrink-0" aria-hidden="true" />{{ d.text }}
    </li>
  </ul>
</template>
