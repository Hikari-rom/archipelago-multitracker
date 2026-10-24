<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useMediaQuery } from '@vueuse/core'
import ConfigView from '../components/ConfigView.vue'
import LogsView from '../components/LogsView.vue'
import UpdateBanner from '../components/UpdateBanner.vue'
import { ALL_OWNERS, NO_OWNER, distinctOwners, filterByOwner, hasNoOwner, loadOwnerChoice, saveOwnerChoice } from '../lib/config'
import { totals } from '../lib/dashboard'
import { setView, tracker, type View } from '../stores/tracker'
import BottomNav from './components/BottomNav.vue'
import MoreMenu from './components/MoreMenu.vue'
import SkyBackground from './components/SkyBackground.vue'
import SleepBanner from './components/SleepBanner.vue'
import ThemeMenu from './components/ThemeMenu.vue'
import UndoToast from './components/UndoToast.vue'
import DashboardV2 from './views/DashboardV2.vue'
import GoalsV2 from './views/GoalsV2.vue'
import HistoryV2 from './views/HistoryV2.vue'
import RoomV2 from './views/RoomV2.vue'
import { loadSkyAnimated, loadThemeChoice, saveSkyAnimated, saveThemeChoice, type ThemeChoice } from './lib/prefs'
import { applyV2Theme, resolveTheme } from './lib/tokens'

const phone = useMediaQuery('(max-width: 699px)')
const prefersDark = useMediaQuery('(prefers-color-scheme: dark)')
const reducedMotion = useMediaQuery('(prefers-reduced-motion: reduce)')

const themeChoice = ref<ThemeChoice>(loadThemeChoice())
const resolved = computed(() => resolveTheme(themeChoice.value, prefersDark.value))
watch(resolved, (t) => applyV2Theme(t), { immediate: true })
watch(themeChoice, saveThemeChoice)
const sky = ref(loadSkyAnimated())
watch(sky, saveSkyAnimated)

const ownerChoice = ref(loadOwnerChoice())
const chips = computed(() => [
  { key: ALL_OWNERS, label: 'tous' },
  ...distinctOwners(tracker.slots).map((o) => ({ key: o, label: o })),
  ...(hasNoOwner(tracker.slots) ? [{ key: NO_OWNER, label: 'sans joueur' }] : []),
])
const owner = computed({
  get: () => (chips.value.some((c) => c.key === ownerChoice.value) ? ownerChoice.value : ALL_OWNERS),
  set: (k: string) => {
    ownerChoice.value = k
    saveOwnerChoice(k)
  },
})
const selected = computed(() => filterByOwner(tracker.slots, owner.value))
const inLogic = computed(() => totals(selected.value).inLogic)

const showConfig = computed(() => tracker.view === 'config' || (tracker.loaded && !tracker.slots.length && !tracker.loadError))
const view = computed<View>(() => (showConfig.value ? 'config' : tracker.view))
const roomHref = computed(() => (/^https?:\/\//.test(tracker.roomUrl) ? tracker.roomUrl : ''))
const sseLabel = computed(() => ({ open: 'En direct', connecting: 'Connexion…', reconnecting: 'Reconnexion…' })[tracker.sse])
const TABS: { key: View; label: string }[] = [
  { key: 'dashboard', label: 'Tableau' },
  { key: 'history', label: 'Historique' },
  { key: 'goals', label: 'Objectifs' },
]
</script>

<template>
  <SkyBackground v-if="resolved === 'nuit'" :animated="sky && !reducedMotion" />
  <header class="sticky top-0 z-20 border-b bg-header backdrop-blur-md">
    <div class="mx-auto flex h-14 max-w-[1440px] items-center gap-3 px-4 min-[700px]:px-8 min-[1000px]:gap-5">
      <a href="#" aria-label="Retour au tableau de bord" class="flex min-h-11 min-w-0 items-center gap-2.5" @click.prevent="setView('dashboard')">
        <span class="grid size-7 shrink-0 place-items-center rounded-md border border-logic/60 font-mono text-[11px] font-bold text-logic">AP</span>
        <span class="flex min-w-0 flex-col">
          <span class="text-[15px] font-semibold">Multitracker</span>
          <span v-if="!phone && (tracker.server || tracker.roomUrl)" class="truncate font-mono text-[10.5px] text-muted-foreground max-[999px]:hidden">
            {{ tracker.server }}<template v-if="roomHref"> · <a :href="roomHref" target="_blank" rel="noopener" class="underline-offset-2 hover:underline">room ↗</a></template>
          </span>
        </span>
      </a>
      <nav v-if="!phone" aria-label="Navigation" class="ml-2 flex self-stretch min-[1000px]:ml-5">
        <button
          v-for="t in TABS" :key="t.key" type="button" :aria-label="t.label"
          :aria-current="view === t.key ? 'page' : undefined"
          class="border-b-2 px-4 text-sm"
          :class="view === t.key ? 'border-logic font-semibold' : 'border-transparent text-muted-foreground hover:text-foreground'"
          @click="setView(t.key)"
        >{{ t.label }}</button>
      </nav>
      <span v-if="phone" class="ml-auto font-mono text-sm"><strong class="text-logic">{{ inLogic }}</strong> en logique</span>
      <span v-if="!phone" class="ml-auto flex shrink-0 items-center gap-2 whitespace-nowrap text-xs text-muted-foreground">
        <span class="size-2 rounded-full" :class="tracker.sse === 'open' ? 'bg-done' : 'bg-new'" aria-hidden="true" /><span class="max-[999px]:sr-only">{{ sseLabel }}</span>
      </span>
      <MoreMenu v-if="!phone" />
      <ThemeMenu v-model:choice="themeChoice" v-model:sky="sky" :resolved="resolved" :compact="phone" />
    </div>
  </header>
  <SleepBanner class="mx-4 min-[700px]:mx-8" />
  <UpdateBanner class="mx-4 min-[700px]:mx-8" />
  <main class="mx-auto max-w-[1440px] px-4 pt-4 pb-24 min-[700px]:px-8 min-[700px]:pb-10">
    <p v-if="tracker.loadError && !tracker.slots.length" role="alert" class="rounded-xl border bg-card p-4"><span class="text-error">! </span>Impossible de joindre le serveur : {{ tracker.loadError }}</p>
    <ConfigView v-else-if="view === 'config'" />
    <LogsView v-else-if="view === 'logs'" />
    <HistoryV2 v-else-if="view === 'history'" :slots="selected" :owner="owner" :chips="chips" @update:owner="(k: string) => (owner = k)" />
    <RoomV2 v-else-if="view === 'room'" />
    <GoalsV2 v-else-if="view === 'goals'" :slots="selected" :owner="owner" :chips="chips" @update:owner="(k: string) => (owner = k)" />
    <DashboardV2 v-else :slots="selected" :owner="owner" :chips="chips" @update:owner="(k: string) => (owner = k)" />
  </main>
  <UndoToast />
  <BottomNav v-if="phone" />
</template>
