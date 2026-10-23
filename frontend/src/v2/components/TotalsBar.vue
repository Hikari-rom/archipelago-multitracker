<script setup lang="ts">
import { computed } from 'vue'
import { useMediaQuery } from '@vueuse/core'
import { showOwnerFilter } from '../../lib/config'
import { SORT_LABELS, totals, type SortMode } from '../../lib/dashboard'
import type { SlotSummary } from '../../lib/types'
import { tracker } from '../../stores/tracker'
import type { V2Layout } from '../lib/prefs'
import { isBK } from '../lib/card'
import OwnerSelect from './OwnerSelect.vue'

const props = defineProps<{
  slots: SlotSummary[]
  sort: SortMode
  layout: V2Layout
  hideDone: boolean
  owner: string
  chips: { key: string; label: string }[]
  restCount?: number
}>()
const emit = defineEmits<{
  'update:sort': [SortMode]
  'update:layout': [V2Layout]
  'update:hideDone': [boolean]
  'update:owner': [string]
}>()

const phone = useMediaQuery('(max-width: 699px)')
const t = computed(() => totals(props.slots))
const bk = computed(() => props.slots.filter(isBK).length)
const sorts = Object.keys(SORT_LABELS) as SortMode[]
const layouts: { key: V2Layout; label: string }[] = [
  { key: 'cards', label: 'Cartes' },
  { key: 'focus', label: 'Focus' },
]
const seg = 'inline-flex rounded-lg border p-0.5'
const segBtn = (on: boolean) => ['min-h-8 rounded-md px-3 text-sm max-[699px]:min-h-11', on ? 'bg-accent font-semibold text-foreground' : 'text-muted-foreground hover:text-foreground']
function onSort(e: Event) {
  emit('update:sort', (e.target as HTMLSelectElement).value as SortMode)
}
</script>

<template>
  <div class="flex flex-wrap items-center gap-x-6 gap-y-3 rounded-[14px] border bg-card px-5 py-3">
    <template v-if="phone">
      <span class="font-mono text-sm">Où avancer · {{ restCount ?? slots.length }}</span>
      <label class="flex items-center gap-2 text-sm text-muted-foreground">
        <span class="sr-only">Tri</span>
        <select :value="sort" class="h-11 rounded-lg border bg-card px-2 text-sm text-foreground" @change="onSort">
          <option v-for="s in sorts" :key="s" :value="s">{{ SORT_LABELS[s] }} ▾</option>
        </select>
      </label>
    </template>
    <template v-else>
      <div class="flex flex-wrap items-baseline gap-x-5 gap-y-1 font-mono text-sm">
        <span><strong class="text-logic">{{ t.inLogic }}</strong> en logique</span>
        <span>{{ t.done }} / {{ t.total }} faits</span>
        <span v-if="t.newItems" class="text-new">★ {{ t.newItems }} nouveaux</span>
        <span v-if="bk" data-bk-total><span class="rounded bg-bk px-1 text-bk-foreground">BK</span> {{ bk }} jeu{{ bk > 1 ? 'x' : '' }} sans check en logique</span>
        <span class="text-muted-foreground">{{ slots.length }} jeux</span>
      </div>
      <div class="ml-auto flex flex-wrap items-center gap-x-5 gap-y-2">
        <div class="flex items-center gap-2 text-sm text-muted-foreground">
          Tri
          <div :class="seg" role="group" aria-label="Tri">
            <button v-for="s in sorts" :key="s" type="button" :aria-pressed="sort === s" :class="segBtn(sort === s)" @click="emit('update:sort', s)">{{ SORT_LABELS[s] }}</button>
          </div>
        </div>
      </div>
    </template>
    <div class="flex flex-wrap items-center gap-x-5 gap-y-2" :class="phone ? 'ml-auto' : ''">
      <div class="flex items-center gap-2 text-sm text-muted-foreground">
        <template v-if="!phone">Affichage</template>
        <div :class="seg" role="group" aria-label="Affichage">
          <button v-for="l in layouts" :key="l.key" type="button" :data-layout="l.key" :aria-pressed="layout === l.key" :class="segBtn(layout === l.key)" @click="emit('update:layout', l.key)">{{ l.label }}</button>
        </div>
      </div>
      <template v-if="!phone">
        <span class="flex items-center gap-2 text-sm">
          <input id="v2-hide-done" type="checkbox" class="size-4" :checked="hideDone" @change="emit('update:hideDone', ($event.target as HTMLInputElement).checked)" />
          <label for="v2-hide-done">Masquer terminés</label>
        </span>
        <OwnerSelect v-if="showOwnerFilter(tracker.slots)" :model-value="owner" :chips="chips" @update:model-value="emit('update:owner', $event)" />
      </template>
    </div>
  </div>
</template>
