<script setup lang="ts">
import { computed } from 'vue'
import { ACCESS_LABEL, accessDetail } from '../../lib/hints'
import type { HintAccess } from '../../lib/types'

const props = defineProps<{ access: HintAccess }>()
const detail = computed(() => accessDetail(props.access))
const tone = computed(
  () =>
    ({
      ok: 'border-done/50 text-done',
      blocked: 'border-error/50 text-error',
      pending: 'border-border text-muted-foreground',
      unknown: 'border-border text-muted-foreground',
      found: 'border-logic/50 text-logic',
    })[props.access.state],
)
</script>

<template>
  <div class="flex min-w-0 flex-col items-start gap-0.5" :data-access="access.state">
    <span class="whitespace-nowrap rounded-full border px-2 py-px text-xs font-medium" :class="tone">
      {{ access.state === 'ok' ? '✓ ' : access.state === 'blocked' ? '✕ ' : '' }}{{ ACCESS_LABEL[access.state] }}
    </span>
    <span v-if="detail" class="text-xs" :class="access.state === 'blocked' ? 'text-foreground/85' : 'text-muted-foreground'">{{ detail }}</span>
  </div>
</template>
