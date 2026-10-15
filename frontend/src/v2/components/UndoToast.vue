<script setup lang="ts">
import { undo, undoLast } from '../lib/undo'
</script>

<template>
  <div
    v-if="undo.message" role="status" aria-live="polite"
    class="fixed bottom-24 left-1/2 z-40 flex w-[calc(100%-2rem)] max-w-md -translate-x-1/2 items-center gap-4 rounded-xl border bg-popover px-4 py-3 text-popover-foreground shadow-xl min-[700px]:bottom-6"
  >
    <span class="flex-1 text-sm">{{ undo.message }}</span>
    <button type="button" class="min-h-11 rounded-md px-3 text-sm font-semibold text-logic hover:bg-accent min-[700px]:min-h-8" @click="undoLast()">Annuler</button>
  </div>
</template>
