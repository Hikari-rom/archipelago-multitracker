<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { Monitor, Moon, Settings, Sun } from 'lucide-vue-next'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import ConfigView from './components/ConfigView.vue'
import SlotCard from './components/SlotCard.vue'
import StatusDot from './components/StatusDot.vue'
import { ALL_OWNERS, NO_OWNER, distinctOwners, filterByOwner, hasNoOwner, loadOwnerChoice, saveOwnerChoice, showOwnerFilter } from './lib/config'
import { stableOrder } from './lib/order'
import { sortSlots, summaryText } from './lib/logic'
import { applyTheme, loadTheme, nextTheme, saveTheme, themeLabel } from './lib/theme'
import { setView, tracker } from './stores/tracker'

const theme = ref(loadTheme())
const hideDone = ref(false)
onMounted(() => applyTheme(theme.value))
watch(theme, (t) => {
  applyTheme(t)
  saveTheme(t)
})

const sorted = computed(() => sortSlots(tracker.slots))
let lastOrder: string[] = []
const anyOpen = computed(() => Object.values(tracker.open).some(Boolean))
const ordered = computed(() => {
  const r = stableOrder(lastOrder, sorted.value, anyOpen.value || tracker.seenFreeze)
  lastOrder = r.map((s) => s.name)
  return r
})
const ownerChoice = ref(loadOwnerChoice())
const owners = computed(() => distinctOwners(tracker.slots))
const filterOn = computed(() => showOwnerFilter(tracker.slots))
const chips = computed(() => [
  { key: ALL_OWNERS, label: 'Tous' },
  ...owners.value.map((o) => ({ key: o, label: o })),
  ...(hasNoOwner(tracker.slots) ? [{ key: NO_OWNER, label: 'Sans joueur' }] : []),
])
const activeChip = computed(() => (chips.value.some((c) => c.key === ownerChoice.value) ? ownerChoice.value : ALL_OWNERS))
function pick(k: unknown) {
  if (typeof k !== 'string' || !k) return // clicking the active chip again keeps it selected
  ownerChoice.value = k
  saveOwnerChoice(k)
}
const themeIcon = computed(() => ({ auto: Monitor, light: Sun, dark: Moon })[theme.value])
const byOwner = computed(() => filterByOwner(ordered.value, activeChip.value))
const visible = computed(() => (hideDone.value ? byOwner.value.filter((s) => !s.goal) : byOwner.value))
const summary = computed(() => summaryText(filterByOwner(tracker.slots, activeChip.value)))
const showConfig = computed(() => tracker.view === 'config' || (tracker.loaded && !tracker.slots.length && !tracker.loadError))
const roomHref = computed(() => (/^https?:\/\//.test(tracker.roomUrl) ? tracker.roomUrl : ''))
const sseLabel = computed(
  () => ({ open: 'En direct', connecting: 'Connexion…', reconnecting: 'Reconnexion…' })[tracker.sse],
)
</script>

<template>
  <header class="bg-card/95 supports-[backdrop-filter]:bg-card/85 sticky top-0 z-10 border-b backdrop-blur">
    <div class="mx-auto flex max-w-[1400px] flex-wrap items-center gap-x-3 gap-y-2 px-4 py-2.5">
      <div class="min-w-0 flex-[1_1_220px]">
        <h1 class="text-lg font-semibold">Archipelago Multitracker</h1>
        <p v-if="tracker.server || tracker.roomUrl" class="text-muted-foreground text-xs break-all">
          <template v-if="tracker.server">Serveur : {{ tracker.server }}</template>
          <template v-if="tracker.roomUrl">
            {{ tracker.server ? ' · ' : '' }}Room :
            <a v-if="roomHref" :href="roomHref" target="_blank" rel="noopener" class="text-primary underline-offset-2 hover:underline">{{ tracker.roomUrl }}</a>
            <template v-else>{{ tracker.roomUrl }}</template>
          </template>
        </p>
      </div>
      <StatusDot :status="tracker.sse" :label="sseLabel" />
      <Button
        variant="outline"
        size="sm"
        aria-label="Configuration"
        :aria-pressed="showConfig"
        @click="setView(showConfig && tracker.slots.length ? 'dashboard' : 'config')"
      >
        <Settings aria-hidden="true" /> Configuration
      </Button>
      <Button variant="outline" size="sm" :aria-label="`Thème : ${themeLabel[theme]}. Changer de thème`" @click="theme = nextTheme(theme)">
        <component :is="themeIcon" aria-hidden="true" /> Thème : {{ themeLabel[theme] }}
      </Button>
    </div>
    <div v-if="!showConfig && filterOn" class="mx-auto max-w-[1400px] px-4 pb-2">
      <ToggleGroup
        type="single"
        variant="outline"
        size="sm"
        class="flex-wrap"
        :model-value="activeChip"
        aria-label="Filtrer par joueur"
        @update:model-value="pick"
      >
        <ToggleGroupItem v-for="c in chips" :key="c.key" :value="c.key" class="px-3">{{ c.label }}</ToggleGroupItem>
      </ToggleGroup>
    </div>
    <div v-if="!showConfig" class="mx-auto flex max-w-[1400px] flex-wrap items-center justify-between gap-2 px-4 pb-2.5">
      <Badge variant="good" class="px-2.5 py-0.5 text-sm font-semibold">{{ summary }}</Badge>
      <div class="flex min-h-8 items-center gap-2">
        <Checkbox id="hide-done" v-model="hideDone" />
        <Label for="hide-done" class="font-normal">Masquer les jeux terminés</Label>
      </div>
    </div>
  </header>

  <main class="mx-auto max-w-[1400px] px-4 pt-3.5 pb-10">
    <ConfigView v-if="showConfig" />
    <template v-else>
      <Alert v-if="tracker.roomError" class="bg-warn text-warn-foreground mb-3 border-transparent" role="alert">
        <AlertDescription class="text-warn-foreground">Room : {{ tracker.roomError }}</AlertDescription>
      </Alert>
      <Alert v-if="tracker.loadError && !tracker.slots.length" variant="destructive" role="alert">
        <AlertDescription>Impossible de joindre le serveur : {{ tracker.loadError }}</AlertDescription>
      </Alert>
      <p v-else-if="!tracker.loaded" class="text-muted-foreground">Chargement…</p>
      <p v-else-if="!visible.length" class="text-muted-foreground">Tous les jeux sont terminés 🎉</p>
      <div v-else class="grid grid-cols-1 items-start gap-3 min-[700px]:grid-cols-2 min-[1100px]:grid-cols-3">
        <SlotCard v-for="s in visible" :key="s.name" :summary="s" />
      </div>
    </template>
  </main>
</template>
