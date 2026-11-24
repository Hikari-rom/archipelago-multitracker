<script setup lang="ts">
import { RotateCcw } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { setView } from '../../stores/tracker'
import UpdatePanel from '../UpdatePanel.vue'
import UserApworldsPanel from '../UserApworldsPanel.vue'
import type { ConfigForm } from './form'

const props = defineProps<{ form: ConfigForm }>()
const f = props.form

async function onRestore(): Promise<void> {
  if (await f.onRestore()) setView('dashboard')
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <UserApworldsPanel @imported="f.loadConfig().catch(() => {})" />
    <UpdatePanel />
    <div v-if="f.cfg.value?.has_backup" class="flex flex-col gap-1">
      <Button type="button" variant="outline" class="self-start" :disabled="f.restoring.value" @click="onRestore">
        <RotateCcw aria-hidden="true" /> Restaurer la configuration précédente
      </Button>
      <p class="text-muted-foreground text-xs">Revient à la configuration enregistrée avant la dernière (elle-même reste récupérable).</p>
    </div>
  </div>
</template>
