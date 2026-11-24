<script setup lang="ts">
import { computed } from 'vue'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { ConfigForm } from './form'

const props = defineProps<{ form: ConfigForm; bottomNav?: boolean }>()
const emit = defineEmits<{ save: [] }>()
const f = props.form
// A first setup has nothing to go back to: the bar stays as soon as the configuration can be saved.
const shown = computed(() => f.dirty.value || (f.firstSetup.value && f.canSave.value) || !!f.saveError.value)
</script>

<template>
  <div
    v-if="shown"
    data-save-bar
    :class="cn(
      'bg-popover text-popover-foreground fixed inset-x-3 bottom-3 z-30 mx-auto flex max-w-xl flex-col gap-1 rounded-xl border px-4 py-2.5 shadow-lg',
      bottomNav && 'max-[699px]:bottom-[76px]',
    )"
  >
    <div class="flex flex-wrap items-center gap-2">
      <span class="min-w-0 flex-1 text-sm">{{ f.firstSetup.value ? 'Nouvelle configuration' : 'Changements non enregistrés' }}</span>
      <Button v-if="!f.firstSetup.value" type="button" variant="outline" class="max-[699px]:min-h-11" @click="f.reset()">Annuler</Button>
      <Button type="button" class="max-[699px]:min-h-11" :disabled="!f.canSave.value" @click="emit('save')">
        {{ f.saving.value ? 'Enregistrement…' : 'Enregistrer' }}
      </Button>
    </div>
    <p v-if="f.saveError.value" class="text-destructive text-sm" role="alert">{{ f.saveError.value }}</p>
  </div>
</template>
