<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useMediaQuery } from '@vueuse/core'
import { formatReceived } from '../../lib/history'
import { hintInMyWorld, hintMineElsewhere } from '../../lib/logic'
import { loadDetail, markSeen, tracker } from '../../stores/tracker'
import { CATEGORY_CLASS, category, itemOrigin } from '../lib/days'
import { regionsOf } from '../lib/regions'
import GoalBlock from './GoalBlock.vue'

export type DetailTab = 'logic' | 'new' | 'received' | 'hints' | 'goal'
const props = defineProps<{ name: string; initial?: DetailTab }>()

const phone = useMediaQuery('(max-width: 699px)')
const pid = computed(() => `dt-${encodeURIComponent(props.name).replace(/%/g, '_')}`)
const tab = ref<DetailTab>(props.initial ?? 'logic')
const picked = ref<string | null>(null)
const d = computed(() => tracker.details[props.name])
const error = computed(() => tracker.detailError[props.name])
onMounted(() => {
  if (!d.value && !error.value) void loadDetail(props.name)
})

const regions = computed(() => regionsOf(d.value?.in_logic_locations ?? []))
const region = computed(() => regions.value.find((r) => r.name === picked.value) ?? regions.value[0])
const news = computed(() => (d.value?.items_list ?? []).filter((i) => i.new).sort((a, b) => b.index - a.index))
const received = computed(() => [...(d.value?.items_list ?? [])].sort((a, b) => b.index - a.index))
const RECEIVED_MAX = 50
const hintsWorld = computed(() => {
  const hs = d.value?.hints_in_my_world ?? []
  return [...hs.filter((h) => h.in_logic), ...hs.filter((h) => !h.in_logic)]
})
const hintsElsewhere = computed(() => d.value?.hints_mine_elsewhere ?? [])
const tabs = computed<{ key: DetailTab; label: string }[]>(() => [
  { key: 'logic', label: `En logique ${d.value?.in_logic_locations.length ?? 0}` },
  { key: 'new', label: `★ Nouveaux ${news.value.length}` },
  { key: 'received', label: `Reçus ${d.value?.items_list.length ?? 0}` },
  { key: 'hints', label: `Hints ${hintsWorld.value.length + hintsElsewhere.value.length}` },
  { key: 'goal', label: 'But' },
])

const buttons = ref<HTMLElement[]>([])
function onKey(e: KeyboardEvent): void {
  const step = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0
  if (!step) return
  e.preventDefault()
  const i = (tabs.value.findIndex((t) => t.key === tab.value) + step + tabs.value.length) % tabs.value.length
  tab.value = tabs.value[i].key
  buttons.value[i]?.focus()
}
</script>

<template>
  <p v-if="error" role="alert" class="text-sm"><span class="text-error">! </span>{{ error }}</p>
  <p v-else-if="!d" class="text-sm text-muted-foreground">Chargement…</p>
  <div v-else>
    <div role="tablist" aria-label="Détails du jeu" class="flex gap-1 overflow-x-auto border-b [scrollbar-width:none] [&::-webkit-scrollbar]:hidden min-[700px]:flex-wrap min-[700px]:overflow-visible" @keydown="onKey">
      <button
        v-for="t in tabs" :key="t.key" ref="buttons" type="button" role="tab" :data-tab="t.key" :id="`${pid}-${t.key}`" :aria-controls="`${pid}-panel`"
        :aria-selected="tab === t.key" :tabindex="tab === t.key ? 0 : -1"
        class="min-h-11 shrink-0 whitespace-nowrap border-b-2 px-3 text-sm min-[700px]:min-h-9"
        :class="tab === t.key ? 'border-logic font-semibold' : 'border-transparent text-muted-foreground hover:text-foreground'"
        @click="tab = t.key"
      >{{ t.label }}</button>
    </div>

    <div :id="`${pid}-panel`" role="tabpanel" :aria-labelledby="`${pid}-${tab}`" class="pt-3">
      <template v-if="tab === 'logic'">
        <p v-if="!regions.length" class="text-sm text-muted-foreground">Aucun check en logique.</p>
        <div v-else-if="phone" data-regions-list class="space-y-1">
          <details v-for="r in regions" :key="r.name" class="rounded-md border">
            <summary class="flex min-h-11 cursor-pointer items-center gap-2 px-3 text-sm">
              <span class="min-w-0 flex-1 truncate">▸ {{ r.name }}</span>
              <span v-if="r.hinted > 0" class="text-hint">◆{{ r.hinted }}</span>
              <span class="font-mono tabular-nums">{{ r.count }}</span>
            </summary>
            <ul class="space-y-1.5 px-3 pb-3">
              <li v-for="l in r.locations" :key="l.id" data-location class="text-sm">
                <span v-if="l.hint" class="text-hint" aria-label="hintée">◆ </span>{{ l.name }}
                <div v-if="l.hint" class="text-xs text-muted-foreground">hint · {{ l.hint.item }} pour {{ l.hint.receiver }}</div>
              </li>
            </ul>
          </details>
        </div>
        <div v-else class="grid gap-3 min-[900px]:grid-cols-[minmax(0,240px)_1fr]">
          <ul class="space-y-1">
            <li v-for="r in regions" :key="r.name">
              <button
                type="button" class="flex min-h-11 w-full items-center gap-2 rounded-md px-2 text-left text-sm hover:bg-accent min-[700px]:min-h-8"
                :class="r.name === region?.name ? 'bg-logic/15' : ''" @click="picked = r.name"
              >
                <span class="min-w-0 flex-1 truncate">{{ r.name }}</span>
                <span v-if="r.hinted > 0" class="text-hint">◆{{ r.hinted }}</span>
                <span class="font-mono tabular-nums">{{ r.count }}</span>
              </button>
            </li>
          </ul>
          <div v-if="region">
            <h4 class="mb-2 text-sm font-semibold">{{ region.name }} · {{ region.count }} en logique · hintées en premier</h4>
            <ul class="space-y-1.5">
              <li v-for="l in region.locations" :key="l.id" data-location class="text-sm">
                <span v-if="l.hint" class="text-hint" aria-label="hintée">◆ </span>{{ l.name }}
                <div v-if="l.hint" class="text-xs text-muted-foreground">hint · {{ l.hint.item }} pour {{ l.hint.receiver }}</div>
              </li>
            </ul>
          </div>
        </div>
      </template>

      <template v-else-if="tab === 'new' || tab === 'received'">
        <div v-if="tab === 'new' && news.length" class="mb-2">
          <button type="button" class="min-h-11 rounded-md border px-3 text-sm hover:bg-accent min-[700px]:min-h-8" @click="markSeen(name)">Marquer comme vu</button>
        </div>
        <p v-if="tab === 'new' && !news.length" class="text-sm text-muted-foreground">Aucun nouvel item.</p>
        <ul class="space-y-1.5">
          <li v-for="i in (tab === 'new' ? news : received.slice(0, RECEIVED_MAX))" :key="i.index" class="flex items-baseline gap-2 text-sm">
            <span v-if="category(i)" class="rounded px-1.5 py-0.5 font-mono text-[10px] font-semibold" :class="CATEGORY_CLASS[category(i)!]">{{ category(i) }}</span>
            <span class="min-w-0 flex-1"><span>{{ i.name }}</span><span class="block text-xs text-muted-foreground">{{ itemOrigin(i) }}</span></span>
            <span class="shrink-0 text-xs text-muted-foreground">{{ formatReceived(i, tracker.nowMs) }}</span>
          </li>
        </ul>
        <p v-if="tab === 'received' && received.length > RECEIVED_MAX" class="mt-2 text-xs text-muted-foreground">+ {{ received.length - RECEIVED_MAX }} autres</p>
      </template>

      <template v-else-if="tab === 'hints'">
        <p v-if="!hintsWorld.length && !hintsElsewhere.length" class="text-sm text-muted-foreground">Aucun hint.</p>
        <ul class="space-y-1.5 text-sm">
          <li v-for="(h, n) in hintsWorld" :key="'w' + n"><span v-if="h.in_logic" class="text-hint" aria-label="en logique">◆ </span>{{ hintInMyWorld(h) }}</li>
          <li v-for="(h, n) in hintsElsewhere" :key="'e' + n">{{ hintMineElsewhere(h) }}</li>
        </ul>
      </template>

      <GoalBlock v-else :objective="d.objective" :goal="d.goal" />
    </div>
  </div>
</template>
