<script setup lang="ts">
import { computed, ref } from 'vue'
import { CircleAlert, FileUp, Info, TriangleAlert, Wand2 } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { cn } from '@/lib/utils'
import { distinctGames, filterRows, setChecked } from '../../lib/config'
import { shortYaml, type ConfigForm } from './form'

const props = defineProps<{ form: ConfigForm }>()
const { rows, yamls, yamlPaths, games, goalOverride, goalLoading, diags, uploading, uploadLog, assocInfo, checkedRows } = props.form
const { goalOptions, onGoal, onAssociate, checkWithYaml } = props.form

const fileInput = ref<HTMLInputElement | null>(null)
const filterText = ref('')
const filterGame = ref('')
const checkedOnly = ref(false)
const visible = computed(() =>
  filterRows(rows.value, { text: filterText.value, game: filterGame.value, checkedOnly: checkedOnly.value }),
)
const gameOptions = computed(() => distinctGames(rows.value))
const owners = props.form.owners

async function onFiles(ev: Event): Promise<void> {
  const input = ev.target as HTMLInputElement
  const files = [...(input.files ?? [])]
  input.value = ''
  await props.form.uploadFiles(files)
}
function setVisible(value: boolean): void {
  rows.value = setChecked(rows.value, new Set(visible.value.map((r) => r.name)), value)
}

const diagIcon = { info: Info, warn: TriangleAlert, error: CircleAlert } as const
const diagClass = { info: 'text-muted-foreground', warn: 'text-warn-foreground bg-warn', error: 'text-destructive' } as const
const selectClass =
  'border-input bg-background h-9 w-full min-w-0 rounded-md border px-2 text-sm shadow-xs focus-visible:ring-ring/50 focus-visible:ring-3'
</script>

<template>
  <div class="flex flex-col gap-3">
    <p class="text-muted-foreground text-sm">
      {{ yamls.length }} yaml(s) dans <code class="bg-muted rounded px-1">config/players/</code>. Certains jeux en ont besoin
      pour calculer la logique. « Fin » : afficher sous le but ce qui manque pour la victoire (jeux avec logique).
    </p>
    <div class="flex flex-wrap gap-2">
      <input ref="fileInput" type="file" accept=".yaml,.yml" multiple class="sr-only" aria-label="Importer des yamls" @change="onFiles" />
      <Button type="button" variant="secondary" :disabled="uploading" @click="fileInput?.click()">
        <FileUp aria-hidden="true" /> {{ uploading ? 'Import…' : 'Importer des yamls' }}
      </Button>
      <Button type="button" variant="outline" :disabled="!yamls.length" @click="onAssociate">
        <Wand2 aria-hidden="true" /> Associer automatiquement
      </Button>
    </div>
    <p v-if="assocInfo" class="text-muted-foreground text-sm" role="status">{{ assocInfo }}</p>
    <ul v-if="uploadLog.length" class="flex flex-col gap-1 text-sm" role="status">
      <li v-for="(l, k) in uploadLog" :key="k" :class="l.ok ? 'text-good-foreground' : 'text-destructive'">{{ l.text }}</li>
    </ul>

    <div class="grid grid-cols-1 gap-2 sm:grid-cols-[1fr_minmax(0,14rem)]">
      <Input v-model="filterText" type="search" placeholder="Rechercher un slot ou un jeu…" aria-label="Rechercher un slot ou un jeu" />
      <select v-model="filterGame" :class="selectClass" aria-label="Filtrer par jeu">
        <option value="">Tous les jeux</option>
        <option v-for="g in gameOptions" :key="g" :value="g">{{ g }}</option>
      </select>
    </div>
    <div class="flex flex-wrap items-center gap-2">
      <div class="flex min-h-8 items-center gap-2 pr-2">
        <Checkbox id="cfg-checked-only" v-model="checkedOnly" />
        <Label for="cfg-checked-only" class="font-normal">Cochés seulement ({{ checkedRows.length }})</Label>
      </div>
      <Button type="button" size="sm" variant="outline" :disabled="!visible.length" @click="setVisible(true)">Cocher les {{ visible.length }} affichés</Button>
      <Button type="button" size="sm" variant="outline" :disabled="!visible.length" @click="setVisible(false)">Décocher les affichés</Button>
      <Button type="button" size="sm" variant="outline" @click="checkWithYaml">Cocher ceux qui ont un yaml</Button>
    </div>

    <p v-if="!rows.length" class="text-muted-foreground text-sm">Aucun slot. Utilise « Découvrir les slots ».</p>
    <p v-else-if="!visible.length" class="text-muted-foreground text-sm">Aucun slot ne correspond au filtre.</p>
    <ul v-else data-slot-list class="max-h-[min(60vh,36rem)] divide-y overflow-y-auto overscroll-contain rounded-lg border text-sm">
      <li
        class="text-muted-foreground bg-card sticky top-0 z-10 hidden px-3 py-1.5 text-xs font-medium sm:grid sm:grid-cols-[minmax(0,1fr)_minmax(0,17rem)_minmax(0,7rem)_2.5rem] sm:gap-2"
        aria-hidden="true"
      >
        <span class="pl-6.5">slot · jeu</span><span>yaml</span><span>joueur</span><span>fin</span>
      </li>
      <li v-for="(r, i) in visible" :key="r.name" :class="cn('flex flex-col gap-1 px-3 py-1.5', !r.checked && 'opacity-75')">
        <div class="grid grid-cols-1 items-center gap-x-2 gap-y-1 sm:grid-cols-[minmax(0,1fr)_minmax(0,17rem)_minmax(0,7rem)_2.5rem]">
          <div class="flex min-w-0 items-center gap-2.5">
            <Checkbox :id="`cfg-row-${i}`" v-model="r.checked" :aria-label="`suivre ${r.name}`" />
            <label :for="`cfg-row-${i}`" class="min-w-0 flex-1 cursor-pointer truncate" :title="`${r.name} · ${r.game || 'jeu inconnu'}`">
              <span class="font-medium">{{ r.name }}</span>
              <span class="text-muted-foreground text-xs"> · {{ r.game || 'jeu inconnu' }}</span>
            </label>
          </div>
          <div v-if="r.checked" class="flex gap-2 pl-6.5 sm:contents">
            <select v-model="r.yaml" :class="cn(selectClass, 'h-8 flex-1')" :aria-label="`yaml de ${r.name}`">
              <option value="">aucun yaml</option>
              <option v-for="y in yamlPaths" :key="y" :value="y">{{ shortYaml(y) }}</option>
              <option v-if="r.yaml && !yamlPaths.includes(r.yaml)" :value="r.yaml">{{ r.yaml }}</option>
            </select>
            <Input v-model="r.owner" type="text" list="cfg-owners" placeholder="joueur" class="h-8 w-20 shrink-0 sm:w-full" :aria-label="`joueur de ${r.name}`" />
            <label v-if="games[r.game]?.logic" data-goal-needs class="flex shrink-0 cursor-pointer items-center gap-1.5 text-xs" title="Afficher ce qui manque pour la victoire">
              <Checkbox v-model="r.goalNeeds" :aria-label="`ce qui manque pour la victoire de ${r.name}`" />
              <span class="text-muted-foreground sm:sr-only">fin</span>
            </label>
          </div>
        </div>
        <p v-if="r.checked && goalOverride && goalLoading.has(r.game)" class="text-muted-foreground pl-6.5 text-xs" data-goal-loading>
          Lecture des conditions de victoire de {{ r.game }}…
        </p>
        <div v-if="r.checked && goalOverride && goalOptions(r.game).length" data-goal-choice class="flex flex-wrap items-center gap-2 pl-6.5">
          <label v-for="o in goalOptions(r.game)" :key="o.option" class="flex min-w-0 items-center gap-2 text-xs">
            <span class="text-muted-foreground shrink-0">But · {{ o.display }}</span>
            <select :value="r.goal?.[o.option] ?? ''" :class="cn(selectClass, 'h-8 w-auto max-w-[16rem]')" :aria-label="`${o.display} de ${r.name}`" @change="onGoal(r, o.option, $event)">
              <option value="">automatique</option>
              <option v-for="c in o.choices" :key="c" :value="c">{{ c }}</option>
            </select>
          </label>
        </div>
        <ul v-if="r.checked && diags[r.name].length" class="flex flex-col gap-0.5 pl-6.5">
          <li v-for="(d, k) in diags[r.name]" :key="k" :class="cn('flex items-start gap-1.5 rounded px-1.5 py-0.5 text-xs', diagClass[d.level])">
            <component :is="diagIcon[d.level]" class="mt-px size-3.5 shrink-0" aria-hidden="true" />{{ d.text }}
          </li>
        </ul>
      </li>
    </ul>
    <datalist id="cfg-owners"><option v-for="o in owners" :key="o" :value="o" /></datalist>
  </div>
</template>
