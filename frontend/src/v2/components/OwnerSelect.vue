<script setup lang="ts">
import { showOwnerFilter } from '../../lib/config'
import { tracker } from '../../stores/tracker'

const owner = defineModel<string>({ required: true })
defineProps<{ chips: { key: string; label: string }[] }>()
</script>

<template>
  <label v-if="showOwnerFilter(tracker.slots)" class="flex items-center gap-2 text-sm text-muted-foreground">
    Joueur
    <select v-model="owner" class="h-9 max-[699px]:h-11 rounded-lg border bg-card px-2 text-sm text-foreground">
      <option v-for="c in chips" :key="c.key" :value="c.key">{{ c.label }}</option>
    </select>
  </label>
</template>
