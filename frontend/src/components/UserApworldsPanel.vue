<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { FolderInput, RefreshCw } from '@lucide/vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import * as api from '../lib/api'
import { IMPORT_LABELS, importSummary, VERSION_LABELS, type ApworldsInfo, type ImportRow } from '../lib/apworlds'

const emit = defineEmits<{ imported: [] }>()

const info = ref<ApworldsInfo | null>(null)
const loadError = ref('')
const path = ref('')
const busy = ref<'' | 'import' | 'check'>('')
const actionError = ref('')
const report = ref<ImportRow[] | null>(null)
const checked = ref(false)

const skipped = computed(() => (report.value ?? []).filter((r) => r.status !== 'imported'))
const BADGES = { ok: 'good', warn: 'warn', muted: 'muted' } as const

function errText(e: unknown): string {
  return e instanceof Error ? e.message : String(e)
}

async function load(): Promise<void> {
  try {
    info.value = await api.getApworlds()
    if (!path.value) path.value = info.value.default_source ?? ''
    loadError.value = ''
  } catch (e) {
    loadError.value = errText(e)
  }
}

async function onImport(): Promise<void> {
  busy.value = 'import'
  actionError.value = ''
  try {
    const res = await api.importApworlds(path.value.trim())
    info.value = res
    report.value = res.report ?? []
    checked.value = false
    emit('imported')
  } catch (e) {
    actionError.value = errText(e)
  } finally {
    busy.value = ''
  }
}

async function onCheck(): Promise<void> {
  busy.value = 'check'
  actionError.value = ''
  try {
    info.value = await api.checkApworlds()
    checked.value = true
  } catch (e) {
    actionError.value = errText(e)
  } finally {
    busy.value = ''
  }
}

onMounted(load)
</script>

<template>
  <Card class="gap-3 py-4" data-apworlds-panel>
    <CardHeader class="px-5">
      <CardTitle class="flex items-center gap-2"><FolderInput class="size-4" aria-hidden="true" /> Apworlds de ton Archipelago</CardTitle>
      <CardDescription>
        Certains jeux ne sont pas fournis avec l'app. Importe-les depuis le dossier <code>custom_worlds</code> de ton
        installation d'Archipelago : seuls les jeux de la room que l'app ne fournit pas sont copiés. La logique n'est
        calculée que si c'est la même version que celle de la room.
      </CardDescription>
    </CardHeader>
    <CardContent class="flex flex-col gap-3 px-5 text-sm">
      <p v-if="loadError" class="text-destructive" role="alert">Impossible de lire les apworlds importés : {{ loadError }}</p>
      <template v-else-if="info">
        <form class="flex flex-wrap items-center gap-2" @submit.prevent="onImport">
          <label for="apworlds-source" class="sr-only">Dossier custom_worlds</label>
          <Input
            id="apworlds-source"
            v-model="path"
            class="min-w-0 flex-1 basis-64 font-mono text-xs"
            placeholder="C:\ProgramData\Archipelago\custom_worlds"
            autocomplete="off"
            spellcheck="false"
            data-source
          />
          <Button type="submit" size="sm" :disabled="!!busy || !path.trim()" data-import>
            <FolderInput aria-hidden="true" /> {{ busy === 'import' ? 'Import…' : 'Importer' }}
          </Button>
        </form>
        <p v-if="!info.default_source" class="text-muted-foreground text-xs" data-no-default>
          Pas d'installation d'Archipelago trouvée à l'emplacement habituel : colle le chemin de son dossier
          <code>custom_worlds</code>.
        </p>

        <p v-if="report" class="rounded-lg border px-3 py-2" role="status" data-report>
          Import terminé : {{ importSummary(report) }}.
        </p>
        <details v-if="skipped.length" class="text-muted-foreground" data-skipped>
          <summary class="cursor-pointer">Fichiers pas importés ({{ skipped.length }})</summary>
          <ul class="mt-1 flex flex-col gap-0.5">
            <li v-for="r in skipped" :key="r.file"><code>{{ r.file }}</code><template v-if="r.game"> ({{ r.game }})</template> : {{ IMPORT_LABELS[r.status] }}</li>
          </ul>
        </details>

        <p v-if="!info.files.length" class="text-muted-foreground" data-empty>Aucun apworld importé.</p>
        <template v-else>
          <ul class="flex flex-col divide-y rounded-lg border" data-files>
            <li v-for="f in info.files" :key="f.file" class="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5 px-3 py-1.5">
              <span class="min-w-0">
                <span class="font-medium">{{ f.game ?? 'jeu inconnu' }}</span>
                <code class="text-muted-foreground ml-2 text-xs">{{ f.file }}</code>
              </span>
              <Badge v-if="f.version" :variant="BADGES[VERSION_LABELS[f.version].tone]" data-version>{{ VERSION_LABELS[f.version].text }}</Badge>
              <Badge v-else-if="f.in_room === false" variant="muted">pas dans la room</Badge>
            </li>
          </ul>
          <div class="flex flex-wrap items-center gap-2">
            <Button type="button" variant="outline" size="sm" :disabled="!!busy" data-check @click="onCheck">
              <RefreshCw :class="busy === 'check' ? 'animate-spin motion-reduce:animate-none' : ''" aria-hidden="true" />
              {{ busy === 'check' ? 'Vérification…' : 'Vérifier les versions' }}
            </Button>
            <span v-if="!checked" class="text-muted-foreground text-xs">Compare chaque apworld à celui avec lequel la room a été générée.</span>
          </div>
        </template>
        <p v-if="actionError" class="text-destructive" role="alert">{{ actionError }}</p>
      </template>
      <p v-else class="text-muted-foreground">Chargement…</p>
    </CardContent>
  </Card>
</template>
