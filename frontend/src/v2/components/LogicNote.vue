<script setup lang="ts">
import { ref } from 'vue'
import { Hourglass } from '@lucide/vue'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'

// The slot's logic is knowingly late (never early): an icon whose tooltip says why. Hover or focus opens it, a
// tap toggles it (touch screens). `inert`: inside a button (the focus list) a nested button is invalid, the native
// title stands in.
defineProps<{ note: string; inert?: boolean }>()
const open = ref(false)
const icon = 'size-[0.9em] shrink-0 text-muted-foreground'
</script>

<template>
  <span class="inline-flex">
    <span v-if="inert" data-logic-note :title="note" role="img" aria-label="Logique minorée" class="inline-flex">
      <Hourglass :class="icon" aria-hidden="true" />
    </span>
    <TooltipProvider v-else>
      <Tooltip v-model:open="open" disable-closing-trigger>
        <TooltipTrigger
          data-logic-note
          type="button"
          aria-label="Logique minorée"
          class="inline-flex items-center rounded-full p-0.5 hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-logic"
          @click.stop="open = !open"
        >
          <Hourglass :class="icon" aria-hidden="true" />
        </TooltipTrigger>
        <TooltipContent class="max-w-72 text-left">{{ note }}</TooltipContent>
      </Tooltip>
    </TooltipProvider>
  </span>
</template>
