<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import SlotCard from './components/SlotCard.vue'
import { sortSlots, summaryText } from './lib/logic'
import { applyTheme, loadTheme, nextTheme, saveTheme, themeLabel } from './lib/theme'
import { tracker } from './stores/tracker'

const theme = ref(loadTheme())
const hideDone = ref(false)
onMounted(() => applyTheme(theme.value))
watch(theme, (t) => {
  applyTheme(t)
  saveTheme(t)
})

const sorted = computed(() => sortSlots(tracker.slots))
const visible = computed(() => (hideDone.value ? sorted.value.filter((s) => !s.goal) : sorted.value))
const summary = computed(() => summaryText(tracker.slots))
const sseLabel = computed(
  () => ({ open: 'En direct', connecting: 'Connexion…', reconnecting: 'Reconnexion…' })[tracker.sse],
)
</script>

<template>
  <header class="top">
    <div class="top-inner">
      <div class="brand">
        <h1>Archipelago Multitracker</h1>
        <p v-if="tracker.server" class="muted server">Serveur : {{ tracker.server }}</p>
      </div>
      <span class="live" :class="'live-' + tracker.sse" role="status">
        <span class="dot" aria-hidden="true"></span>{{ sseLabel }}
      </span>
      <button
        type="button"
        class="btn theme"
        :aria-label="`Thème : ${themeLabel[theme]}. Changer de thème`"
        @click="theme = nextTheme(theme)"
      >
        Thème : {{ themeLabel[theme] }}
      </button>
    </div>
    <div class="top-inner sub">
      <p class="summary">{{ summary }}</p>
      <label class="check"><input v-model="hideDone" type="checkbox" /> Masquer les jeux terminés</label>
    </div>
  </header>

  <main class="main-grid-wrap">
    <p v-if="tracker.loadError && !tracker.slots.length" class="banner" role="alert">
      Impossible de joindre le serveur : {{ tracker.loadError }}
    </p>
    <section v-else-if="tracker.loaded && !tracker.slots.length" class="empty">
      <h2>Aucun slot configuré</h2>
      <p>
        Copie <code>config/room.example.yaml</code> vers <code>config/room.yaml</code>, renseigne ta room
        et tes slots, puis redémarre le backend.
      </p>
    </section>
    <p v-else-if="!tracker.loaded" class="muted">Chargement…</p>
    <div v-else class="grid">
      <SlotCard v-for="s in visible" :key="s.name" :summary="s" />
    </div>
  </main>
</template>
