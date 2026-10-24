<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { getUpdate } from '../lib/api'
import { latestLabel, loadDismissed, saveDismissed, UPDATE_ANCHOR, type UpdateInfo } from '../lib/update'
import { setView, tracker } from '../stores/tracker'

// The server checks once a day; the page asks it again every few hours (a tab left open for days).
const REFRESH_MS = 3 * 3600 * 1000

const info = ref<UpdateInfo | null>(null)
const dismissed = ref(loadDismissed())
let timer: ReturnType<typeof setInterval> | undefined

const version = computed(() => info.value?.latest?.version ?? '')
const show = computed(
  () => !!info.value?.available && !info.value.running && version.value !== dismissed.value && tracker.view !== 'config',
)

async function load(): Promise<void> {
  try {
    info.value = await getUpdate()
  } catch {
    /* no banner */
  }
}

async function onOpen(): Promise<void> {
  setView('config')
  await nextTick()
  // ConfigView loads first: wait for the panel to exist
  for (let i = 0; i < 20; i++) {
    const el = document.getElementById(UPDATE_ANCHOR)
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' })
      return
    }
    await new Promise((r) => setTimeout(r, 100))
  }
}

function onDismiss(): void {
  dismissed.value = version.value
  saveDismissed(version.value)
}

onMounted(() => {
  void load()
  timer = setInterval(load, REFRESH_MS)
})
onUnmounted(() => clearInterval(timer))
</script>

<template>
  <div v-if="show && info" role="status" data-update-banner class="bg-card mx-auto mt-3 flex max-w-[1440px] flex-wrap items-center gap-x-3 gap-y-2 rounded-xl border px-4 py-2 text-sm">
    <span aria-hidden="true" class="text-primary">↑</span>
    <p class="min-w-0 flex-1">Mise à jour disponible : <strong>{{ latestLabel(info) }}</strong></p>
    <button type="button" class="bg-primary text-primary-foreground min-h-9 rounded-lg px-3 font-semibold" @click="onOpen">Voir</button>
    <button type="button" class="text-muted-foreground hover:text-foreground min-h-9 px-2" aria-label="Masquer jusqu'à la prochaine version" title="Masquer jusqu'à la prochaine version" @click="onDismiss">✕</button>
  </div>
</template>
