<script setup lang="ts">
import { computed } from 'vue'
import { DialogClose, DialogContent, DialogDescription, DialogOverlay, DialogPortal, DialogRoot, DialogTitle } from 'reka-ui'
import { Checkbox } from '@/components/ui/checkbox'
import type { ConfigForm } from './form'
import SlotDiags from './SlotDiags.vue'
import SlotRowFields from './SlotRowFields.vue'

const props = defineProps<{ form: ConfigForm; name: string | null }>()
const emit = defineEmits<{ close: [] }>()
const row = computed(() => props.form.rows.value.find((r) => r.name === props.name) ?? null)
</script>

<template>
  <DialogRoot :open="!!row" @update:open="(o: boolean) => !o && emit('close')">
    <DialogPortal>
      <DialogOverlay class="fixed inset-0 z-40 bg-black/50" />
      <DialogContent
        v-if="row"
        data-slot-sheet
        class="bg-popover text-popover-foreground fixed inset-x-0 bottom-0 z-50 flex max-h-[88vh] flex-col gap-4 overflow-y-auto rounded-t-2xl border-t p-4 pb-6"
      >
        <span aria-hidden="true" class="bg-muted-foreground/40 mx-auto h-1 w-10 rounded-full" />
        <div class="flex items-start gap-3">
          <div class="min-w-0 flex-1">
            <DialogTitle class="text-primary truncate text-lg font-semibold">{{ row.name }}</DialogTitle>
            <DialogDescription class="text-muted-foreground text-sm">{{ row.game || 'jeu inconnu' }}</DialogDescription>
          </div>
          <label class="flex min-h-11 items-center gap-2 text-sm">
            <Checkbox v-model="row.checked" :aria-label="`suivre ${row.name}`" /> Suivi
          </label>
        </div>
        <SlotDiags :diags="form.diags.value[row.name] ?? []" />
        <SlotRowFields v-if="row.checked" :form="form" :row="row" stacked />
        <DialogClose class="bg-primary text-primary-foreground min-h-11 rounded-lg font-semibold">OK</DialogClose>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>
