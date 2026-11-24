<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { TabsContent, TabsList, TabsRoot, TabsTrigger } from 'reka-ui'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { cn } from '@/lib/utils'
import { getUpdate } from '../lib/api'
import { CONFIG_TABS, configTabFromHash, initialConfigTab, type ConfigTab } from '../lib/config'
import { setConfigTab, setView, tracker } from '../stores/tracker'
import AppTab from './config/AppTab.vue'
import DisplayTab from './config/DisplayTab.vue'
import FeaturesTab from './config/FeaturesTab.vue'
import RoomTab from './config/RoomTab.vue'
import SaveBar from './config/SaveBar.vue'
import SlotsTab from './config/SlotsTab.vue'
import { useConfigForm } from './config/form'

/** bottomNav: the v2 shows a navigation bar at the bottom of phones, the save bar goes above it. */
defineProps<{ bottomNav?: boolean }>()
const emit = defineEmits<{ saved: [] }>()

const form = useConfigForm()
const { loading, loadError, summary, room, discoverError } = form

const LABELS: Record<ConfigTab, string> = { slots: 'Slots', room: 'Room', fonctions: 'Fonctions', affichage: 'Affichage', app: 'App' }
const tab = ref<ConfigTab>('slots')
const updateReady = ref(false)
const toFix = computed(() => summary.value.warnings + summary.value.errors)
const dots = computed<Record<ConfigTab, boolean>>(() => ({
  slots: toFix.value > 0,
  room: !!room.value?.sleeping || !!discoverError.value,
  fonctions: false,
  affichage: false,
  app: updateReady.value,
}))

const prefilled = !!tracker.prefillRoom
watch(loading, (l) => {
  if (!l) {
    tab.value = initialConfigTab({ hashTab: configTabFromHash(location.hash), hasSlots: !form.firstSetup.value, prefillRoom: prefilled })
  }
})
watch(tab, (t) => setConfigTab(t))
// "#config?room=..." opened while the page is shown: the link is filled in on the Room tab. Sync: the form clears
// prefillRoom in its own watcher, before a pre-flush watcher here would see it.
watch(
  () => tracker.prefillRoom,
  (v) => {
    if (v && !loading.value) tab.value = 'room'
  },
  { flush: 'sync' },
)
function onHash(): void {
  const t = configTabFromHash(location.hash)
  if (t) tab.value = t
}

onMounted(() => {
  void form.load()
  window.addEventListener('hashchange', onHash)
  getUpdate()
    .then((u) => (updateReady.value = !!u.available && !u.running))
    .catch(() => {})
})
onUnmounted(() => window.removeEventListener('hashchange', onHash))

/** Enter never saves the whole configuration by accident; in the room field it runs the discovery. */
function onEnter(ev: KeyboardEvent): void {
  const target = ev.target as HTMLElement
  if (target.tagName !== 'INPUT') return
  ev.preventDefault()
  if (target.id === 'cfg-room') void form.onDiscover()
}

async function onSave(): Promise<void> {
  if (!(await form.save())) return
  emit('saved')
  setView('dashboard')
}
</script>

<template>
  <section class="mx-auto flex max-w-[1100px] flex-col gap-4 pb-28" aria-labelledby="cfg-title">
    <div class="flex flex-wrap items-baseline gap-x-4 gap-y-1">
      <h2 id="cfg-title" class="text-xl font-semibold">Configuration</h2>
      <p v-if="!loading && !loadError" data-config-summary class="text-muted-foreground text-sm">
        {{ summary.count }} suivis · <span class="text-primary">{{ summary.withLogic }} avec logique</span>
        <template v-if="toFix"> · <span class="text-warn-foreground">{{ toFix }} à corriger</span></template>
        <template v-if="room">
          · room <span :class="room.sleeping ? 'text-warn-foreground' : 'text-good-foreground'">{{ room.sleeping ? 'endormie' : 'éveillée' }}</span>
        </template>
      </p>
    </div>
    <p v-if="loading" class="text-muted-foreground">Chargement…</p>
    <Alert v-else-if="loadError" variant="destructive" role="alert">
      <AlertDescription>Impossible de lire la configuration : {{ loadError }}</AlertDescription>
    </Alert>
    <form v-else novalidate @submit.prevent @keydown.enter="onEnter">
      <TabsRoot v-model="tab" class="flex flex-col gap-4">
        <TabsList aria-label="Sections de la configuration" class="-mx-1 flex gap-1 overflow-x-auto border-b px-1">
          <TabsTrigger
            v-for="t in CONFIG_TABS"
            :key="t"
            :value="t"
            :data-config-tab="t"
            :class="cn(
              'text-muted-foreground hover:text-foreground -mb-px flex shrink-0 items-center gap-1.5 border-b-2 border-transparent px-3 py-2.5 text-sm whitespace-nowrap max-[699px]:min-h-11',
              'data-[state=active]:border-primary data-[state=active]:text-foreground data-[state=active]:font-semibold',
            )"
          >
            {{ LABELS[t] }}
            <span v-if="t === 'slots'" class="font-mono text-xs font-normal">{{ summary.count }}</span>
            <span v-if="t === 'affichage'" class="text-xs font-normal max-[699px]:hidden">(cet appareil)</span>
            <span v-if="dots[t]" data-tab-dot :class="cn('size-2 rounded-full', t === 'app' ? 'bg-primary' : 'bg-warn-foreground')" aria-label="à voir" />
          </TabsTrigger>
        </TabsList>
        <div class="bg-card rounded-xl border p-4 min-[700px]:p-5">
          <TabsContent value="slots"><SlotsTab :form="form" /></TabsContent>
          <TabsContent value="room"><RoomTab :form="form" /></TabsContent>
          <TabsContent value="fonctions"><FeaturesTab :form="form" /></TabsContent>
          <TabsContent value="affichage"><DisplayTab /></TabsContent>
          <TabsContent value="app"><AppTab :form="form" /></TabsContent>
        </div>
      </TabsRoot>
    </form>
    <SaveBar :form="form" :bottom-nav="bottomNav" @save="onSave" />
  </section>
</template>
