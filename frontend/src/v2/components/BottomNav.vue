<script setup lang="ts">
import { computed } from 'vue'
import { setView, tracker, type View } from '../../stores/tracker'
import MoreMenu from './MoreMenu.vue'

const ITEMS: { key: View; icon: string; label: string }[] = [
  { key: 'dashboard', icon: '⌂', label: 'Tableau' },
  { key: 'history', icon: '↺', label: 'Historique' },
  { key: 'goals', icon: '⚑', label: 'Objectifs' },
]
const current = computed(() => tracker.view)
</script>

<template>
  <nav aria-label="Navigation mobile" class="fixed inset-x-0 bottom-0 z-20 flex border-t bg-header pb-[env(safe-area-inset-bottom)] backdrop-blur-md">
    <button
      v-for="i in ITEMS" :key="i.key" type="button"
      :aria-current="current === i.key ? 'page' : undefined"
      class="flex min-h-14 flex-1 flex-col items-center justify-center gap-0.5 text-[11px]"
      :class="current === i.key ? 'font-semibold text-logic' : 'text-muted-foreground'"
      @click="setView(i.key)"
    >
      <span class="text-lg" aria-hidden="true">{{ i.icon }}</span>{{ i.label }}
    </button>
    <MoreMenu compact />
  </nav>
</template>
