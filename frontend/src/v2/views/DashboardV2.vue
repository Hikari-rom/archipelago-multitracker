<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useMediaQuery } from '@vueuse/core'
import { compactMain, SORT_LABELS, sortBy, splitFeatured, type SortMode } from '../../lib/dashboard'
import { stableOrder } from '../../lib/order'
import type { SlotSummary } from '../../lib/types'
import { setFeatured, tracker } from '../../stores/tracker'
import ActiveCarousel from '../components/ActiveCarousel.vue'
import ActiveCard from '../components/ActiveCard.vue'
import DetailSheet from '../components/DetailSheet.vue'
import FocusList from '../components/FocusList.vue'
import FocusPanel from '../components/FocusPanel.vue'
import GameTile from '../components/GameTile.vue'
import RecentStrip from '../components/RecentStrip.vue'
import TotalsBar from '../components/TotalsBar.vue'
import { loadHideDone, loadLayout, loadSort, saveHideDone, saveLayout, saveSort, type V2Layout } from '../lib/prefs'

const props = defineProps<{ slots: SlotSummary[]; owner: string; chips: { key: string; label: string }[] }>()
const emit = defineEmits<{ 'update:owner': [string] }>()
const sort = ref<SortMode>(loadSort())
watch(sort, saveSort)
const layout = ref<V2Layout>(loadLayout())
watch(layout, saveLayout)
const hideDone = ref(loadHideDone())
watch(hideDone, saveHideDone)
const sheet = ref<string | null>(null)
const phone = useMediaQuery('(max-width: 699px)')

const sorted = computed(() => sortBy(sort.value, props.slots, tracker.nowMs, tracker.activeMinutes, tracker.activity))
let lastOrder: string[] = []
const anyOpen = computed(() => Object.values(tracker.open).some(Boolean))
const ordered = computed(() => {
  const r = stableOrder(lastOrder, sorted.value, anyOpen.value || tracker.seenFreeze)
  lastOrder = r.map((s) => s.name)
  return r
})
const visible = computed(() => (hideDone.value ? ordered.value.filter((s) => !s.goal) : ordered.value))
const split = computed(() => splitFeatured(visible.value, tracker.nowMs, tracker.activeMinutes, tracker.activity))
const main = computed(() => compactMain(visible.value, tracker.nowMs, tracker.activeMinutes, tracker.activity))
const focus = computed(() => layout.value === 'focus')
// phone list: everything but the displayed game in Focus, the non-featured games otherwise
const phoneList = computed(() => (focus.value ? visible.value.filter((s) => s.name !== main.value?.name) : split.value.rest))
// featured slots get their details loaded (regions on the active cards, the Focus panel)
watch(
  () => (focus.value ? (main.value ? [main.value] : []) : split.value.featured).map((s) => s.name).join('\n'),
  (names) => setFeatured(names ? names.split('\n') : []),
  { immediate: true },
)
</script>

<template>
  <section :data-phone="phone || undefined">
    <TotalsBar
      v-model:sort="sort" v-model:layout="layout" v-model:hide-done="hideDone"
      :slots="props.slots" :owner="props.owner" :chips="props.chips" :rest-count="phone ? phoneList.length : split.rest.length"
      @update:owner="emit('update:owner', $event)"
    />
    <RecentStrip :slots="props.slots" />
    <p v-if="!tracker.loaded" class="mt-6 text-muted-foreground">Chargement…</p>
    <p v-else-if="!visible.length" class="mt-6 text-muted-foreground">Tous les jeux sont terminés.</p>
    <template v-else>
      <template v-if="phone && !focus">
        <ActiveCarousel v-if="split.featured.length" class="mt-4" :slots="split.featured" @details="sheet = $event" />
        <FocusList class="mt-4" :slots="phoneList" :current="null" />
      </template>
      <template v-else-if="phone">
        <ActiveCarousel v-if="main" class="mt-4" :slots="[main]" @details="sheet = $event" />
        <FocusList class="mt-4" :slots="phoneList" :current="null" />
      </template>
      <div v-else-if="focus" class="mt-6 grid grid-cols-[minmax(0,3fr)_minmax(0,2fr)] items-start gap-4">
        <FocusPanel v-if="main" :summary="main" />
        <FocusList :slots="visible" :current="main?.name ?? null" />
      </div>
      <template v-else>
      <template v-if="split.featured.length">
        <div class="mt-6 mb-3 flex flex-wrap items-baseline gap-x-4">
          <h2 class="text-lg font-semibold">◉ Actifs · {{ split.featured.length }}</h2>
          <span class="font-mono text-xs text-muted-foreground">{{ tracker.activity.mode === 'manual' ? 'manuel = choisis à la main' : `auto = check il y a moins de ${tracker.activeMinutes} min` }}</span>
        </div>
        <div class="space-y-3">
          <ActiveCard v-for="s in split.featured" :key="s.name" :summary="s" />
        </div>
      </template>
      <div class="mt-6 mb-3 flex flex-wrap items-baseline gap-x-4">
        <h2 class="text-lg font-semibold">▸ Où avancer · {{ split.rest.length }} jeux</h2>
        <span class="font-mono text-xs text-muted-foreground">tri {{ SORT_LABELS[sort].toLowerCase() }}</span>
      </div>
      <div class="grid grid-cols-1 gap-3 min-[700px]:grid-cols-2 min-[1100px]:grid-cols-3">
        <GameTile v-for="s in split.rest" :key="s.name" :summary="s" />
      </div>
      </template>
    </template>
    <DetailSheet :name="sheet" @close="sheet = null" />
  </section>
</template>
