<script setup lang="ts">
import { DropdownMenuCheckboxItem, DropdownMenuContent, DropdownMenuItemIndicator, DropdownMenuLabel, DropdownMenuPortal,
  DropdownMenuRadioGroup, DropdownMenuRadioItem, DropdownMenuRoot, DropdownMenuSeparator, DropdownMenuTrigger } from 'reka-ui'
import type { ThemeChoice } from '../lib/prefs'
import type { ResolvedTheme } from '../lib/tokens'

const props = defineProps<{ choice: ThemeChoice; resolved: ResolvedTheme; sky: boolean; compact?: boolean }>()
const emit = defineEmits<{ 'update:choice': [ThemeChoice]; 'update:sky': [boolean] }>()
const LABEL: Record<ThemeChoice, string> = { nuit: 'Nuit', plan: 'Plan', auto: 'Auto' }
const OPTIONS: { key: ThemeChoice; title: string; sub: string }[] = [
  { key: 'nuit', title: 'Nuit', sub: 'Ciel étoilé, sombre' },
  { key: 'plan', title: 'Plan', sub: 'Clair, grille de dessin' },
  { key: 'auto', title: 'Auto', sub: 'Suit le système : Plan ou Nuit' },
]
const item = 'flex min-h-11 cursor-default items-center gap-3 rounded-lg px-3 py-1.5 text-sm outline-none data-[highlighted]:bg-accent'
</script>

<template>
  <DropdownMenuRoot>
    <DropdownMenuTrigger
      :aria-label="`Thème : ${LABEL[props.choice]}`"
      class="flex min-h-9 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-lg border px-3 text-sm hover:bg-accent max-[699px]:min-h-11 max-[699px]:min-w-11 max-[699px]:justify-center"
    >
      <span aria-hidden="true">◐</span><span v-if="!props.compact">{{ LABEL[props.choice] }} ▾</span>
    </DropdownMenuTrigger>
    <DropdownMenuPortal>
      <DropdownMenuContent align="end" :side-offset="6" class="z-50 w-72 max-w-[calc(100vw-32px)] rounded-xl border bg-popover p-1.5 text-popover-foreground shadow-xl">
        <DropdownMenuLabel class="px-3 py-1.5 font-mono text-[11px] tracking-widest uppercase text-muted-foreground">Thème</DropdownMenuLabel>
        <DropdownMenuRadioGroup :model-value="props.choice" @update:model-value="(v) => emit('update:choice', v as ThemeChoice)">
          <DropdownMenuRadioItem v-for="o in OPTIONS" :key="o.key" :value="o.key" :class="item">
            <span class="flex flex-1 flex-col"><span class="font-semibold">{{ o.title }}</span><span class="text-xs text-muted-foreground">{{ o.sub }}</span></span>
            <DropdownMenuItemIndicator aria-hidden="true">✓</DropdownMenuItemIndicator>
          </DropdownMenuRadioItem>
        </DropdownMenuRadioGroup>
        <DropdownMenuSeparator class="my-1 h-px bg-border" />
        <DropdownMenuCheckboxItem
          :model-value="props.sky"
          :disabled="props.resolved !== 'nuit'"
          :class="item"
          @update:model-value="(v) => emit('update:sky', !!v)"
        >
          <span class="flex flex-1 flex-col"><span class="font-semibold">Ciel animé</span><span class="text-xs text-muted-foreground">Coupé si le système réduit les animations</span></span>
          <DropdownMenuItemIndicator aria-hidden="true">✓</DropdownMenuItemIndicator>
        </DropdownMenuCheckboxItem>
      </DropdownMenuContent>
    </DropdownMenuPortal>
  </DropdownMenuRoot>
</template>
