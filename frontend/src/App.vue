<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import ConfigView from './components/ConfigView.vue'
import SlotCard from './components/SlotCard.vue'
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
function pick(k: string) {
  ownerChoice.value = k
  saveOwnerChoice(k)
}
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
  <header class="top">
    <div class="top-inner">
      <div class="brand">
        <h1>Archipelago Multitracker</h1>
        <p v-if="tracker.server || tracker.roomUrl" class="muted server">
          <template v-if="tracker.server">Serveur : {{ tracker.server }}</template>
          <template v-if="tracker.roomUrl">
            {{ tracker.server ? ' · ' : '' }}Room : <a v-if="roomHref" :href="roomHref" target="_blank" rel="noopener">{{ tracker.roomUrl }}</a><template v-else>{{ tracker.roomUrl }}</template>
          </template>
        </p>
      </div>
      <span class="live" :class="'live-' + tracker.sse" role="status">
        <span class="dot" aria-hidden="true"></span>{{ sseLabel }}
      </span>
      <button type="button" class="btn" aria-label="Configuration" :aria-pressed="showConfig" @click="setView(showConfig && tracker.slots.length ? 'dashboard' : 'config')">
        <span aria-hidden="true">⚙</span> Configuration
      </button>
      <button
        type="button"
        class="btn theme"
        :aria-label="`Thème : ${themeLabel[theme]}. Changer de thème`"
        @click="theme = nextTheme(theme)"
      >
        Thème : {{ themeLabel[theme] }}
      </button>
    </div>
    <div v-if="!showConfig && filterOn" class="top-inner chips" role="group" aria-label="Filtrer par joueur">
      <button v-for="c in chips" :key="c.key" type="button" class="chipbtn" :class="{ on: activeChip === c.key }" :aria-pressed="activeChip === c.key" @click="pick(c.key)">{{ c.label }}</button>
    </div>
    <div v-if="!showConfig" class="top-inner sub">
      <p class="summary">{{ summary }}</p>
      <label class="check"><input v-model="hideDone" type="checkbox" /> Masquer les jeux terminés</label>
    </div>
  </header>

  <main class="main-grid-wrap">
    <ConfigView v-if="showConfig" />
    <template v-else>
    <p v-if="tracker.roomError" class="warn-banner" role="alert">Room : {{ tracker.roomError }}</p>
    <p v-if="tracker.loadError && !tracker.slots.length" class="banner" role="alert">
      Impossible de joindre le serveur : {{ tracker.loadError }}
    </p>
    <p v-else-if="!tracker.loaded" class="muted">Chargement…</p>
    <p v-else-if="!visible.length" class="muted">Tous les jeux sont terminés 🎉</p>
    <div v-else class="grid">
      <SlotCard v-for="s in visible" :key="s.name" :summary="s" />
    </div>
    </template>
  </main>
</template>
