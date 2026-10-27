<script setup lang="ts">
import { mdiPinOutline } from '@mdi/js'
import { computed } from 'vue'
import { COLUMN_LABEL, STATUS_LABEL, hintPin, sortHints, type HintColumn } from '../../lib/hints'
import type { HintRow } from '../../lib/types'
import type { HintsSort } from '../lib/prefs'
import { isPinned } from '../../stores/tracker'
import HintAccessCell from './HintAccessCell.vue'
import MdiIcon from './MdiIcon.vue'
import PinButton from './PinButton.vue'

const props = defineProps<{
  rows: HintRow[]
  columns: HintColumn[]
  /** slot of the group (layout « par slot »): columns `dir` and `other` are relative to it */
  context?: string
  label: string
}>()
const sort = defineModel<HintsSort>('sort', { required: true })

const pinned = (h: HintRow) => {
  const p = hintPin(h)
  return !!p && isPinned(p.slot, p.location)
}
// pinned rows stay on top, whatever the sort
const sorted = computed(() => {
  const all = sortHints(props.rows, sort.value.key, sort.value.dir, props.context)
  return [...all.filter(pinned), ...all.filter((h) => !pinned(h))]
})

function toggle(key: HintColumn) {
  sort.value = sort.value.key === key ? { key, dir: sort.value.dir === 1 ? -1 : 1 } : { key, dir: 1 }
}
function ariaSort(key: HintColumn) {
  if (sort.value.key !== key) return 'none'
  return sort.value.dir === 1 ? 'ascending' : 'descending'
}
function rowKey(h: HintRow) {
  return `${h.finder}\u0000${h.location_id ?? h.location}`
}
function itemClass(h: HintRow) {
  if (h.trap) return 'text-error'
  if (h.progression) return 'font-semibold text-new'
  if (h.useful) return 'text-logic'
  return ''
}
function here(h: HintRow) {
  return !!props.context && h.finder_slot === props.context
}
</script>

<template>
  <div class="overflow-x-auto rounded-[14px] border bg-card">
    <table class="w-full min-w-[760px] border-collapse text-sm" :aria-label="label">
      <thead>
        <tr class="border-b text-left text-xs text-muted-foreground">
          <th scope="col" class="w-8 px-1"><span class="sr-only">Épinglé</span><MdiIcon :path="mdiPinOutline" class="mx-auto" /></th>
          <th v-for="c in columns" :key="c" scope="col" :aria-sort="ariaSort(c)" class="px-3 py-2 font-medium">
            <button type="button" class="flex min-h-8 items-center gap-1 hover:text-foreground" :class="sort.key === c ? 'text-foreground' : ''" @click="toggle(c)">
              {{ COLUMN_LABEL[c] }}
              <span aria-hidden="true" class="w-3 font-mono">{{ sort.key === c ? (sort.dir === 1 ? '↑' : '↓') : '' }}</span>
            </button>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="h in sorted" :key="rowKey(h)" class="border-b align-top last:border-b-0" :class="[h.access.state === 'found' ? 'opacity-60' : '', pinned(h) ? 'bg-new/5' : '']" :data-hint="h.item" :data-pinned="pinned(h) || undefined">
          <td class="px-1 py-1">
            <PinButton v-if="hintPin(h)" :slot="hintPin(h)!.slot" :location="hintPin(h)!.location" :name="h.location" :game="h.finder_game" />
          </td>
          <td v-for="c in columns" :key="c" class="px-3 py-2">
            <template v-if="c === 'item'">
              <span :class="itemClass(h)"><template v-if="h.progression">★ </template>{{ h.item }}</span>
            </template>
            <template v-else-if="c === 'receiver'">
              <span :class="h.receiver_tracked ? 'text-logic' : ''">{{ h.receiver }}</span>
              <span v-if="h.receiver_game" class="block text-xs text-muted-foreground">{{ h.receiver_game }}</span>
            </template>
            <template v-else-if="c === 'finder'">
              <span :class="h.finder_tracked && h.slots.includes(h.finder_slot ?? '') ? 'text-logic' : ''">{{ h.finder }}</span>
              <span v-if="h.finder_game" class="block text-xs text-muted-foreground">{{ h.finder_game }}</span>
            </template>
            <template v-else-if="c === 'location'">
              {{ h.location }}
              <span v-if="h.entrance" class="block text-xs text-muted-foreground">via {{ h.entrance }}</span>
            </template>
            <template v-else-if="c === 'status'">
              <span :class="h.status === 'priority' ? 'text-hint' : h.status === 'avoid' ? 'text-muted-foreground line-through' : 'text-muted-foreground'">
                {{ STATUS_LABEL[h.status ?? 'unspecified'] ?? '—' }}
              </span>
            </template>
            <template v-else-if="c === 'access'"><HintAccessCell :access="h.access" /></template>
            <template v-else-if="c === 'found'">{{ h.found ? '✓' : '' }}</template>
            <template v-else-if="c === 'dir'">
              <span class="whitespace-nowrap text-xs" :class="here(h) ? 'text-hint' : 'text-logic'">{{ here(h) ? 'Dans ce monde' : 'Item de ce slot' }}</span>
            </template>
            <template v-else-if="c === 'other'">
              {{ here(h) ? h.receiver : h.finder }}
              <span class="block text-xs text-muted-foreground">{{ here(h) ? h.receiver_game : h.finder_game }}</span>
            </template>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
