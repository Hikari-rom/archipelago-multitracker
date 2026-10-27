<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { getUpdate } from '../lib/api'
import { installedNotes, loadSeenVersion, noteLines, runningId, saveSeenVersion, type UpdateInfo } from '../lib/update'

// Said once per browser after the app changed version; the first visit only remembers the version.
const info = ref<UpdateInfo | null>(null)
const seen = ref(loadSeenVersion())
const id = computed(() => (info.value ? runningId(info.value) : null))
const show = computed(() => !!id.value && !!seen.value && id.value !== seen.value)
const label = computed(() => info.value?.current.version ?? id.value ?? '')
const notes = computed(() => (info.value ? installedNotes(info.value) : null))
const lines = computed(() => noteLines(notes.value?.notes ?? ''))

onMounted(async () => {
  try {
    info.value = await getUpdate()
  } catch {
    return
  }
  if (id.value && !seen.value) {
    seen.value = id.value
    saveSeenVersion(id.value)
  }
})

function onClose(): void {
  if (!id.value) return
  seen.value = id.value
  saveSeenVersion(id.value)
}
</script>

<template>
  <div v-if="show" role="status" data-updated-notice class="bg-card mx-auto mt-3 flex max-w-[1440px] flex-col gap-2 rounded-xl border border-done/40 px-4 py-2 text-sm">
    <div class="flex flex-wrap items-center gap-x-3 gap-y-2">
      <span aria-hidden="true" class="text-done">✓</span>
      <p class="min-w-0 flex-1">Mise à jour installée : <strong>{{ label }}</strong></p>
      <a v-if="notes?.url" :href="notes.url" target="_blank" rel="noopener" class="text-logic underline-offset-2 hover:underline">Notes de version ↗</a>
      <button type="button" class="text-muted-foreground hover:text-foreground min-h-9 px-2" aria-label="Fermer" title="Fermer" @click="onClose">✕</button>
    </div>
    <details v-if="lines.length" class="pb-1">
      <summary class="cursor-pointer text-muted-foreground hover:text-foreground">Nouveautés</summary>
      <div class="mt-2 flex max-h-72 flex-col gap-1 overflow-y-auto">
        <p v-for="(l, i) in lines" :key="i" :class="l.heading ? 'mt-1 font-semibold' : 'text-foreground/85'">{{ l.text }}</p>
      </div>
    </details>
  </div>
</template>
