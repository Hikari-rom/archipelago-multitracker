<script setup lang="ts">
import { cn } from '@/lib/utils'
import { ACTIVE_CHOICES, saveActiveMinutes } from '../../lib/history'
import { setActiveMode, shows, tracker } from '../../stores/tracker'
import DisplayInfos from '../../v2/components/DisplayInfos.vue'
import { HINTS_LAYOUT_LABELS, saveHintsLayout, saveTicker, TICKER_LABELS, type HintsLayout, type TickerStyle } from '../../v2/lib/prefs'

function onActiveMinutes(e: Event): void {
  tracker.activeMinutes = Number((e.target as HTMLSelectElement).value)
  saveActiveMinutes(tracker.activeMinutes)
}
const tickerStyles = Object.keys(TICKER_LABELS) as TickerStyle[]
function onTicker(e: Event): void {
  tracker.ticker = (e.target as HTMLSelectElement).value as TickerStyle
  saveTicker(tracker.ticker)
}
const hintsLayouts = Object.keys(HINTS_LAYOUT_LABELS) as HintsLayout[]
function onHintsLayout(e: Event): void {
  tracker.hintsLayout = (e.target as HTMLSelectElement).value as HintsLayout
  saveHintsLayout(tracker.hintsLayout)
}
const selectClass =
  'border-input bg-background h-9 w-auto min-w-0 rounded-md border px-2 text-sm shadow-xs focus-visible:ring-ring/50 focus-visible:ring-3'
</script>

<template>
  <div class="flex flex-col gap-3">
    <p class="text-muted-foreground text-sm">Appliqué tout de suite sur cet appareil, rien à enregistrer.</p>
    <DisplayInfos />
    <label class="flex flex-wrap items-center gap-2 text-sm">
      Jeux actifs (affichés en premier)
      <select
        :value="tracker.activity.mode ?? 'auto'"
        data-active-mode
        :class="selectClass"
        @change="setActiveMode(($event.target as HTMLSelectElement).value as 'auto' | 'manual')"
      >
        <option value="auto">Automatique : check récent</option>
        <option value="manual">Manuel : choisis à la main</option>
      </select>
    </label>
    <p v-if="tracker.activity.mode === 'manual'" class="text-muted-foreground text-xs">
      Seuls les jeux activés à la main (« Activer », « Définir comme actif ») sont actifs, et le restent jusqu'à
      « Plus actif », quels que soient les checks. Plusieurs jeux peuvent l'être en même temps.
    </p>
    <label v-else class="flex flex-wrap items-center gap-2 text-sm">
      Un jeu est « actif » (affiché en premier) s'il a fait un check depuis
      <select :value="tracker.activeMinutes" :class="selectClass" @change="onActiveMinutes">
        <option v-for="m in ACTIVE_CHOICES" :key="m" :value="m">{{ m >= 60 ? `${m / 60} h` : `${m} min` }}</option>
      </select>
    </label>
    <label class="flex flex-wrap items-center gap-2 text-sm">
      Bandeau « Derniers reçus » du tableau de bord
      <select :value="tracker.ticker" data-ticker-style :disabled="!shows('recent')" :class="cn(selectClass, 'disabled:opacity-50')" @change="onTicker">
        <option v-for="t in tickerStyles" :key="t" :value="t">{{ TICKER_LABELS[t] }}</option>
      </select>
    </label>
    <p class="text-muted-foreground text-xs">
      Défilant : les derniers items reçus passent en continu comme un fil d'actualité (pause au survol). Interface v2
      seulement.
    </p>
    <label class="flex flex-wrap items-center gap-2 text-sm">
      Page Indices
      <select :value="tracker.hintsLayout" data-hints-layout :class="selectClass" @change="onHintsLayout">
        <option v-for="l in hintsLayouts" :key="l" :value="l">{{ HINTS_LAYOUT_LABELS[l] }}</option>
      </select>
    </label>
  </div>
</template>
