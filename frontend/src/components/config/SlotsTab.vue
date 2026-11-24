<script setup lang="ts">
import { computed, ref } from 'vue'
import { useMediaQuery } from '@vueuse/core'
import { ChevronRight, FileUp, Wand2 } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'
import { setChecked, slotView, type SlotMode, type SlotRow } from '../../lib/config'
import { shortYaml, type ConfigForm } from './form'
import SlotDiags from './SlotDiags.vue'
import SlotRowFields from './SlotRowFields.vue'
import SlotSheet from './SlotSheet.vue'

const props = defineProps<{ form: ConfigForm }>()
const f = props.form
const { rows, yamls, games, diags, uploading, uploadLog, assocInfo, owners, goalOverride } = f

const wide = useMediaQuery('(min-width: 700px)')
const mode = ref<SlotMode>('tracked')
const text = ref('')
const sheet = ref<string | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)

const visible = computed(() => slotView(rows.value, diags.value, { text: text.value, mode: mode.value }))
const toFix = computed(() => slotView(rows.value, diags.value, { text: '', mode: 'fix' }).length)
const modes = computed<{ key: SlotMode; label: string; count: number }[]>(() => [
  { key: 'tracked', label: 'Suivis', count: f.checkedRows.value.length },
  { key: 'all', label: 'Toute la room', count: rows.value.length },
  { key: 'fix', label: 'À corriger', count: toFix.value },
])
const allShownChecked = computed<boolean | 'indeterminate'>(() => {
  const n = visible.value.filter((r) => r.checked).length
  return n === 0 ? false : n === visible.value.length ? true : 'indeterminate'
})
function toggleShown(): void {
  rows.value = setChecked(rows.value, new Set(visible.value.map((r) => r.name)), allShownChecked.value !== true)
}

async function onFiles(ev: Event): Promise<void> {
  const input = ev.target as HTMLInputElement
  const files = [...(input.files ?? [])]
  input.value = ''
  await f.uploadFiles(files)
}

/** Second line of a slot on a phone: its main problem, or its yaml and « fin ». */
function line(r: SlotRow): { text: string; tone: string } {
  const bad = (diags.value[r.name] ?? []).find((d) => d.level !== 'info')
  if (r.checked && bad) return { text: `⚠ ${bad.text}`, tone: bad.level === 'error' ? 'text-destructive' : 'text-warn-foreground' }
  if (!r.checked) return { text: 'non suivi', tone: 'text-muted-foreground' }
  const fin = games.value[r.game]?.logic && r.goalNeeds !== false ? ' · fin ✓' : ''
  return { text: `${r.yaml ? shortYaml(r.yaml) : 'aucun yaml'}${fin}`, tone: 'text-muted-foreground' }
}
const pill = (on: boolean) =>
  cn('min-h-9 shrink-0 rounded-full border px-3.5 text-sm max-[699px]:min-h-11', on ? 'border-primary bg-accent text-foreground' : 'text-muted-foreground hover:text-foreground')
</script>

<template>
  <div class="flex flex-col gap-3">
    <div class="flex flex-wrap items-center gap-2">
      <div class="-mx-1 flex min-w-0 gap-2 overflow-x-auto px-1 max-[699px]:basis-full" role="group" aria-label="Slots affichés">
        <button v-for="m in modes" :key="m.key" type="button" :data-slot-mode="m.key" :aria-pressed="mode === m.key" :class="pill(mode === m.key)" @click="mode = m.key">
          {{ m.label }} <span :class="m.key === 'fix' && m.count ? 'text-warn-foreground' : 'text-muted-foreground'">{{ m.count }}</span>
        </button>
      </div>
      <Input v-model="text" type="search" placeholder="Chercher un slot, un jeu, un joueur…" aria-label="Chercher un slot, un jeu, un joueur" class="min-w-0 flex-[1_1_16rem] max-[699px]:h-11" />
    </div>
    <div class="flex flex-wrap gap-2">
      <input ref="fileInput" type="file" accept=".yaml,.yml" multiple class="sr-only" aria-label="Importer des yamls" @change="onFiles" />
      <Button type="button" size="sm" variant="secondary" class="max-[699px]:min-h-11" :disabled="uploading" @click="fileInput?.click()">
        <FileUp aria-hidden="true" /> {{ uploading ? 'Import…' : 'Importer des yamls' }}
      </Button>
      <Button type="button" size="sm" variant="outline" class="max-[699px]:min-h-11" :disabled="!yamls.length" @click="f.onAssociate">
        <Wand2 aria-hidden="true" /> Associer automatiquement
      </Button>
      <Button type="button" size="sm" variant="outline" class="max-[699px]:min-h-11" @click="f.checkWithYaml">Cocher ceux qui ont un yaml</Button>
      <span class="text-muted-foreground self-center text-xs">{{ yamls.length }} yaml(s) dans config/players/</span>
    </div>
    <p v-if="assocInfo" class="text-muted-foreground text-sm" role="status">{{ assocInfo }}</p>
    <ul v-if="uploadLog.length" class="flex flex-col gap-1 text-sm" role="status">
      <li v-for="(l, k) in uploadLog" :key="k" :class="l.ok ? 'text-good-foreground' : 'text-destructive'">{{ l.text }}</li>
    </ul>

    <p v-if="!rows.length" class="text-muted-foreground text-sm">Aucun slot. Utilise « Découvrir les slots » dans l'onglet Room.</p>
    <p v-else-if="!visible.length" class="text-muted-foreground text-sm">Aucun slot ne correspond au filtre.</p>

    <!-- Bounded height: a room has 150+ slots, the page must not grow with them. -->
    <div v-else-if="wide" data-slot-list class="max-h-[min(60vh,36rem)] overflow-auto overscroll-contain rounded-lg border">
      <table class="w-full border-collapse text-sm">
        <thead class="bg-card text-muted-foreground sticky top-0 z-10 text-left text-xs">
          <tr>
            <th class="w-8 px-3 py-2 font-medium">
              <Checkbox :model-value="allShownChecked" aria-label="cocher les slots affichés" @update:model-value="toggleShown" />
            </th>
            <th class="px-2 py-2 font-medium">Slot</th>
            <th class="px-2 py-2 font-medium">Yaml</th>
            <th class="px-2 py-2 font-medium">Joueur</th>
            <th v-if="goalOverride" class="px-2 py-2 font-medium">But</th>
            <th class="px-3 py-2 text-center font-medium" title="Afficher ce qui manque pour la victoire">Fin</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in visible" :key="r.name" :data-slot-row="r.name" :class="cn('border-t', !r.checked && 'opacity-75')">
            <td class="px-3 py-2 align-top"><Checkbox v-model="r.checked" class="mt-1.5" :aria-label="`suivre ${r.name}`" /></td>
            <td class="min-w-0 px-2 py-2 align-top">
              <div class="text-primary pt-1">{{ r.name }}</div>
              <div class="text-muted-foreground text-xs">{{ r.game || 'jeu inconnu' }}</div>
              <SlotDiags v-if="r.checked" :diags="diags[r.name] ?? []" class="mt-1" />
            </td>
            <SlotRowFields v-if="r.checked" :form="form" :row="r" />
            <td v-else :colspan="goalOverride ? 4 : 3" class="text-muted-foreground px-2 py-2 pt-3.5 align-top text-xs">non suivi</td>
          </tr>
        </tbody>
      </table>
    </div>

    <ul v-else data-slot-list class="max-h-[min(65vh,40rem)] divide-y overflow-y-auto overscroll-contain rounded-lg border">
      <li v-for="r in visible" :key="r.name" :data-slot-row="r.name" class="flex items-center gap-3 pl-3">
        <Checkbox v-model="r.checked" :aria-label="`suivre ${r.name}`" />
        <button type="button" data-slot-open class="flex min-h-14 min-w-0 flex-1 items-center gap-2 py-2 pr-3 text-left" @click="sheet = r.name">
          <span class="min-w-0 flex-1">
            <span class="text-primary block truncate">{{ r.name }}</span>
            <span class="text-muted-foreground block truncate text-xs">{{ r.game || 'jeu inconnu' }}</span>
            <span :class="cn('block truncate font-mono text-[11px]', line(r).tone)">{{ line(r).text }}</span>
          </span>
          <ChevronRight class="text-muted-foreground size-4 shrink-0" aria-hidden="true" />
        </button>
      </li>
    </ul>
    <SlotSheet :form="form" :name="sheet" @close="sheet = null" />
    <datalist id="cfg-owners"><option v-for="o in owners" :key="o" :value="o" /></datalist>
  </div>
</template>
