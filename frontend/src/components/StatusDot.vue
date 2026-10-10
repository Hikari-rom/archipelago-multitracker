<script setup lang="ts">
import { computed } from 'vue'
import { cn } from '@/lib/utils'

const props = defineProps<{ status: string; label: string; title?: string; live?: boolean }>()
const dot = computed(
  () =>
    ({
      connected: 'bg-live',
      open: 'bg-live',
      connecting: 'bg-pending',
      reconnecting: 'bg-pending',
      error: 'bg-destructive',
    })[props.status] ?? 'bg-idle',
)
</script>

<template>
  <span
    :class="cn('text-muted-foreground inline-flex shrink-0 items-center gap-1.5 text-xs whitespace-nowrap', status === 'error' && 'text-destructive')"
    :title="title"
    :role="live ? 'status' : undefined"
  >
    <span :class="cn('inline-block size-2 rounded-full', dot)" aria-hidden="true"></span>{{ label }}
  </span>
</template>
