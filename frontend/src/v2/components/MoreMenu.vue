<script setup lang="ts">
import { DropdownMenuContent, DropdownMenuItem, DropdownMenuPortal, DropdownMenuRoot, DropdownMenuSeparator, DropdownMenuTrigger } from 'reka-ui'
import { v1Href } from '../../lib/v2path'
import { setView } from '../../stores/tracker'

const props = defineProps<{ compact?: boolean }>()
const hash = () => globalThis.location.hash
const item = 'flex min-h-11 cursor-default items-center gap-3 rounded-lg px-3 py-1.5 text-sm outline-none data-[highlighted]:bg-accent'
</script>

<template>
  <DropdownMenuRoot>
    <DropdownMenuTrigger
      aria-label="Plus"
      :class="props.compact
        ? 'flex min-h-14 flex-1 flex-col items-center justify-center gap-0.5 text-[11px] text-muted-foreground'
        : 'flex min-h-9 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-lg border px-3 text-sm hover:bg-accent'"
    >
      <template v-if="props.compact"><span class="text-lg" aria-hidden="true">⋯</span><span>Plus</span></template>
      <template v-else>Plus ▾</template>
    </DropdownMenuTrigger>
    <DropdownMenuPortal>
      <DropdownMenuContent align="end" :side="props.compact ? 'top' : 'bottom'" :side-offset="6" class="z-50 min-w-64 max-w-[calc(100vw-32px)] rounded-xl border bg-popover p-1.5 text-popover-foreground shadow-xl">
        <DropdownMenuItem :class="item" @select="setView('logs')">Journal</DropdownMenuItem>
        <DropdownMenuItem :class="item" @select="setView('config')">Configuration</DropdownMenuItem>
        <DropdownMenuSeparator class="my-1 h-px bg-border" />
        <DropdownMenuItem as-child :class="item">
          <a :href="v1Href(hash())">Revenir à la v1</a>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenuPortal>
  </DropdownMenuRoot>
</template>
