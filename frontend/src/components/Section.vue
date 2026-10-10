<script setup lang="ts">
import { ref } from 'vue'
import { ChevronRight } from '@lucide/vue'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { cn } from '@/lib/utils'

const props = withDefaults(defineProps<{ title: string; startOpen?: boolean }>(), { startOpen: true })
const open = ref(props.startOpen)
</script>

<template>
  <Collapsible v-model:open="open" as="section" class="bg-background rounded-lg border">
    <h3 class="text-base">
      <CollapsibleTrigger
        class="hover:bg-accent/60 flex min-h-11 w-full cursor-pointer items-center gap-2 rounded-lg px-3 py-2.5 text-left font-semibold focus-visible:outline-offset-[-3px]"
      >
        <ChevronRight :class="cn('size-4 transition-transform motion-reduce:transition-none', open && 'rotate-90')" aria-hidden="true" />
        {{ title }}
      </CollapsibleTrigger>
    </h3>
    <CollapsibleContent force-mount class="px-3 pb-2.5 data-[state=closed]:hidden"><slot /></CollapsibleContent>
  </Collapsible>
</template>
