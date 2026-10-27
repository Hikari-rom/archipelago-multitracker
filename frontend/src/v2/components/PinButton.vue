<script setup lang="ts">
import { computed } from 'vue'
import { isPinned, togglePin } from '../../stores/tracker'

// Pins a check (D31): `slot` is the world that holds the location.
const props = defineProps<{ slot: string; location: number; name: string; game?: string | null }>()
const pinned = computed(() => isPinned(props.slot, props.location))
const label = computed(() => (pinned.value ? `Désépingler ${props.name}` : `Épingler ${props.name}`))
</script>

<template>
  <button
    type="button" data-pin :aria-pressed="pinned" :aria-label="label" :title="pinned ? 'Désépingler' : 'Épingler'"
    class="inline-grid size-8 shrink-0 place-items-center rounded-md text-sm transition-opacity hover:bg-accent max-[699px]:size-11"
    :class="pinned ? 'text-new' : 'opacity-40 grayscale hover:opacity-100 focus-visible:opacity-100'"
    @click.stop="togglePin(slot, location, name, game ?? null)"
  >
    <span aria-hidden="true">📌</span>
  </button>
</template>
