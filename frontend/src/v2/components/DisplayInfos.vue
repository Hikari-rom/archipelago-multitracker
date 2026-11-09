<script setup lang="ts">
import { setDisplay, tracker } from '../../stores/tracker'
import { applyPreset, DENSITIES, DENSITY_LABELS, INFO_KEYS, INFO_LABELS, toggleInfo, type Density, type InfoKey } from '../lib/display'

const seg = 'inline-flex rounded-lg border p-0.5'
const segBtn = (on: boolean) => ['min-h-8 rounded-md px-3 text-sm max-[699px]:min-h-11', on ? 'bg-accent font-semibold text-foreground' : 'text-muted-foreground hover:text-foreground']
const pick = (d: Density) => setDisplay(applyPreset(d))
const toggle = (key: InfoKey, e: Event) => setDisplay(toggleInfo(tracker.display, key, (e.target as HTMLInputElement).checked))
</script>

<template>
  <fieldset data-display-infos class="flex flex-col gap-2">
    <legend class="mb-2 text-sm font-medium">Infos du tableau de bord</legend>
    <div class="flex flex-wrap items-center gap-2 text-sm">
      Densité
      <div :class="seg" role="group" aria-label="Densité">
        <button
          v-for="d in DENSITIES" :key="d" type="button" :data-density="d"
          :aria-pressed="tracker.display.preset === d" :class="segBtn(tracker.display.preset === d)" @click="pick(d)"
        >{{ DENSITY_LABELS[d] }}</button>
      </div>
      <span v-if="tracker.display.preset === 'custom'" data-custom class="text-muted-foreground text-xs">· Personnalisé</span>
    </div>
    <div class="grid grid-cols-1 gap-x-6 min-[700px]:grid-flow-col min-[700px]:grid-cols-3 min-[700px]:grid-rows-4">
      <label v-for="k in INFO_KEYS" :key="k" class="flex min-h-8 items-center gap-2 text-sm max-[699px]:min-h-11">
        <input type="checkbox" class="size-4" :data-info="k" :checked="tracker.display.shown.includes(k)" @change="toggle(k, $event)" />
        {{ INFO_LABELS[k] }}
      </label>
    </div>
    <p class="text-muted-foreground text-xs">
      Le gros chiffre, le nom du jeu et les alertes (erreur, BK, logique approximative) restent toujours affichés.
      Interface v2 seulement.
    </p>
  </fieldset>
</template>
