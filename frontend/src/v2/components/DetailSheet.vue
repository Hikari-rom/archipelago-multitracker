<script setup lang="ts">
import { computed } from 'vue'
import { DialogClose, DialogContent, DialogOverlay, DialogPortal, DialogRoot, DialogTitle } from 'reka-ui'
import { tracker } from '../../stores/tracker'
import { cardState, useCardCtx } from '../lib/card'
import BigNumber from './BigNumber.vue'
import DetailTabs from './DetailTabs.vue'
import StateChips from './StateChips.vue'

const props = defineProps<{ name: string | null }>()
const emit = defineEmits<{ close: [] }>()
const ctx = useCardCtx()
const summary = computed(() => tracker.slots.find((s) => s.name === props.name) ?? null)
const state = computed(() => (summary.value ? cardState(summary.value, ctx.value) : null))
</script>

<template>
  <DialogRoot :open="!!name" @update:open="(o: boolean) => !o && emit('close')">
    <DialogPortal>
      <DialogOverlay class="fixed inset-0 z-40 bg-black/50" />
      <DialogContent
        class="fixed inset-0 z-50 flex flex-col bg-popover text-popover-foreground" aria-describedby="undefined"
      >
        <template v-if="summary && state">
          <header class="flex items-start gap-3 border-b p-4">
            <div class="min-w-0 flex-1">
              <StateChips :state="state" />
              <DialogTitle class="mt-2 flex items-center gap-3">
                <BigNumber :state="state" size="md" />
                <span class="min-w-0">
                  <span class="line-clamp-2 block text-base font-semibold" :title="summary.game">{{ summary.game }}</span>
                  <span class="block font-mono text-xs font-normal text-muted-foreground">{{ summary.name }} · {{ summary.checks.done }} / {{ summary.checks.total }}</span>
                </span>
              </DialogTitle>
            </div>
            <DialogClose aria-label="Fermer" class="inline-flex size-11 shrink-0 items-center justify-center rounded-lg border text-lg hover:bg-accent">✕</DialogClose>
          </header>
          <div class="flex-1 overflow-y-auto p-4">
            <DetailTabs :key="summary.name" :name="summary.name" />
          </div>
        </template>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>
