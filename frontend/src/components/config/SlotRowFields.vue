<script setup lang="ts">
// The settings of one tracked slot: yaml, player, goal (when chosen by hand), « fin ». As table cells on PC, stacked
// with labels in the phone sheet.
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'
import type { SlotRow } from '../../lib/config'
import { shortYaml, type ConfigForm } from './form'

const props = defineProps<{ form: ConfigForm; row: SlotRow; stacked?: boolean }>()
const f = props.form
const selectClass =
  'border-input bg-background h-9 w-full min-w-0 rounded-md border px-2 text-sm shadow-xs focus-visible:ring-ring/50 focus-visible:ring-3'
</script>

<template>
  <template v-if="!stacked">
    <td class="px-2 py-2 align-top">
      <select v-model="row.yaml" :class="cn(selectClass, 'h-8 font-mono text-xs')" :aria-label="`yaml de ${row.name}`">
        <option value="">aucun yaml</option>
        <option v-for="y in f.yamlPaths.value" :key="y" :value="y">{{ shortYaml(y) }}</option>
        <option v-if="row.yaml && !f.yamlPaths.value.includes(row.yaml)" :value="row.yaml">{{ row.yaml }}</option>
      </select>
    </td>
    <td class="px-2 py-2 align-top">
      <Input v-model="row.owner" type="text" list="cfg-owners" placeholder="joueur" class="h-8 w-28" :aria-label="`joueur de ${row.name}`" />
    </td>
    <td v-if="f.goalOverride.value" class="px-2 py-2 align-top">
      <p v-if="f.goalLoading.value.has(row.game)" class="text-muted-foreground pt-1.5 text-xs" data-goal-loading>Lecture des conditions de victoire…</p>
      <div v-else-if="f.goalOptions(row.game).length" data-goal-choice class="flex flex-col gap-1">
        <label v-for="o in f.goalOptions(row.game)" :key="o.option" class="flex min-w-0 items-center gap-2 text-xs">
          <span class="text-muted-foreground shrink-0">{{ o.display }}</span>
          <select :value="row.goal?.[o.option] ?? ''" :class="cn(selectClass, 'h-8 w-auto max-w-[14rem]')" :aria-label="`${o.display} de ${row.name}`" @change="f.onGoal(row, o.option, $event)">
            <option value="">automatique</option>
            <option v-for="c in o.choices" :key="c" :value="c">{{ c }}</option>
          </select>
        </label>
      </div>
      <span v-else class="text-muted-foreground block pt-1.5 text-xs">—</span>
    </td>
    <td class="px-3 py-2 text-center align-top">
      <label v-if="f.games.value[row.game]?.logic" data-goal-needs class="inline-flex cursor-pointer pt-1.5" title="Afficher ce qui manque pour la victoire">
        <Checkbox v-model="row.goalNeeds" :aria-label="`ce qui manque pour la victoire de ${row.name}`" />
      </label>
    </td>
  </template>
  <div v-else class="flex flex-col gap-4">
    <label class="flex flex-col gap-1.5 text-sm">
      <span class="text-muted-foreground">Yaml</span>
      <select v-model="row.yaml" :class="cn(selectClass, 'h-11 font-mono text-xs')" :aria-label="`yaml de ${row.name}`">
        <option value="">aucun yaml</option>
        <option v-for="y in f.yamlPaths.value" :key="y" :value="y">{{ shortYaml(y) }}</option>
        <option v-if="row.yaml && !f.yamlPaths.value.includes(row.yaml)" :value="row.yaml">{{ row.yaml }}</option>
      </select>
    </label>
    <label class="flex flex-col gap-1.5 text-sm">
      <span class="text-muted-foreground">Joueur</span>
      <Input v-model="row.owner" type="text" list="cfg-owners" placeholder="joueur" class="h-11" :aria-label="`joueur de ${row.name}`" />
    </label>
    <template v-if="f.goalOverride.value">
      <p v-if="f.goalLoading.value.has(row.game)" class="text-muted-foreground text-xs" data-goal-loading>Lecture des conditions de victoire de {{ row.game }}…</p>
      <div v-else-if="f.goalOptions(row.game).length" data-goal-choice class="flex flex-col gap-3">
        <label v-for="o in f.goalOptions(row.game)" :key="o.option" class="flex flex-col gap-1.5 text-sm">
          <span class="text-muted-foreground">But · {{ o.display }}</span>
          <select :value="row.goal?.[o.option] ?? ''" :class="cn(selectClass, 'h-11')" :aria-label="`${o.display} de ${row.name}`" @change="f.onGoal(row, o.option, $event)">
            <option value="">automatique</option>
            <option v-for="c in o.choices" :key="c" :value="c">{{ c }}</option>
          </select>
        </label>
      </div>
    </template>
    <label v-if="f.games.value[row.game]?.logic" data-goal-needs class="flex cursor-pointer items-start gap-3 text-sm">
      <Checkbox v-model="row.goalNeeds" class="mt-0.5" :aria-label="`ce qui manque pour la victoire de ${row.name}`" />
      <span>Fin : ce qui manque pour la victoire<span class="text-muted-foreground block text-xs">Affiché sous le but.</span></span>
    </label>
  </div>
</template>
